"""AI Reasoner — Supports Local Ollama (Zero-Budget Primary Path) and OpenRouter API with fallbacks."""

import json
import logging
import httpx
from config import get_settings, AIProvider
from schemas.transaction import Transaction
from schemas.decision import AgentDecision, RecoveryAction
from agent.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


class AIReasoner:
    """AI reasoning engine supporting Local Ollama and OpenRouter."""

    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(timeout=self.settings.LLM_TIMEOUT_SECONDS)

    async def reason(self, transaction: Transaction, context: dict) -> AgentDecision:
        """Call AI provider (Ollama / OpenRouter) and parse response into AgentDecision."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(transaction, context)},
        ]

        provider = self.settings.AI_PROVIDER

        content = ""
        model_used = ""
        reasoning_details = None

        if provider == AIProvider.MOCK:
            raise RuntimeError("MOCK provider configured: Triggering deterministic fallback.")

        # --- AUTO MODE: Try Ollama first, fallback to OpenRouter ---
        if provider == AIProvider.AUTO:
            try:
                content, model_used = await self._call_ollama(messages)
                logger.info(f"✅ Recovery decision generated via Local Ollama ({model_used})")
            except Exception as e_ollama:
                logger.info(f"Local Ollama unavailable ({e_ollama}). Falling back to OpenRouter...")
                if self.settings.OPENROUTER_API_KEY and self.settings.OPENROUTER_API_KEY != "your_key_here":
                    resp_data = await self._call_openrouter(messages)
                    choice = resp_data["choices"][0]["message"]
                    content = choice.get("content", "")
                    reasoning_details = choice.get("reasoning_details")
                    model_used = resp_data.get("model", self.settings.OPENROUTER_MODEL)
                    logger.info(f"✅ Recovery decision generated via OpenRouter ({model_used})")
                else:
                    raise RuntimeError(f"Ollama failed and OpenRouter API key not configured: {e_ollama}")

        elif provider == AIProvider.OLLAMA:
            content, model_used = await self._call_ollama(messages)
            logger.info(f"✅ Recovery decision generated via Local Ollama ({model_used})")

        elif provider == AIProvider.OPENROUTER:
            resp_data = await self._call_openrouter(messages)
            choice = resp_data["choices"][0]["message"]
            content = choice.get("content", "")
            reasoning_details = choice.get("reasoning_details")
            model_used = resp_data.get("model", self.settings.OPENROUTER_MODEL)
            logger.info(f"✅ Recovery decision generated via OpenRouter ({model_used})")

        # Parse & Validate Output
        try:
            content = content.strip()
            # Strip think tags if present
            import re
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

            # Extract json block if surrounded by markdown or commentary
            json_match = re.search(r"(\{.*\})", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content

            # Fix common python/json mismatches
            json_str = re.sub(r":\s*None\b", ": null", json_str)
            json_str = re.sub(r":\s*True\b", ": true", json_str)
            json_str = re.sub(r":\s*False\b", ": false", json_str)
            # Remove trailing commas before closing braces/brackets
            json_str = re.sub(r",\s*(\}|\])", r"\1", json_str)

            decision_dict = json.loads(json_str)

            # Ensure transaction_id is set
            decision_dict["transaction_id"] = transaction.transaction_id
            decision_dict["ai_model_used"] = model_used
            decision_dict["is_fallback"] = False

            if reasoning_details and "reasoning" not in decision_dict:
                decision_dict["reasoning"] = str(reasoning_details)

            return AgentDecision(**decision_dict)

        except json.JSONDecodeError as e:
            raise RuntimeError(f"AI reasoning failed: Invalid JSON response — {str(e)} (Raw: {content[:150]}...)")
        except Exception as e:
            raise RuntimeError(f"AI reasoning schema validation failed: {str(e)}")

    async def _call_ollama(self, messages: list[dict]) -> tuple[str, str]:
        """Call Local Ollama chat API."""
        url = f"{self.settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
        payload = {
            "model": self.settings.OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.2,
            },
        }

        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        content = data.get("message", {}).get("content", "")
        model_name = f"ollama/{data.get('model', self.settings.OLLAMA_MODEL)}"
        return content, model_name

    async def _call_openrouter(self, messages: list[dict]) -> dict:
        """Call OpenRouter API with fallback models."""
        headers = {
            "Authorization": f"Bearer {self.settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/harshitpal175786/RecoverIQ",
            "X-Title": "RecoverIQ - AI Revenue Recovery Agent",
        }

        models_to_try = [self.settings.OPENROUTER_MODEL] + self.settings.fallback_models_list
        last_error = None

        for model in models_to_try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 2048,
            }

            if "minimax" in model and self.settings.OPENROUTER_REASONING:
                payload["reasoning"] = {"enabled": True}

            if "minimax" not in model:
                payload["response_format"] = {"type": "json_object"}

            try:
                logger.info(f"Calling OpenRouter with model: {model}")
                response = await self.client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    error_msg = data["error"].get("message", str(data["error"]))
                    logger.warning(f"OpenRouter error with {model}: {error_msg}")
                    last_error = Exception(error_msg)
                    continue

                return data

            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error with {model}: {e.response.status_code} — {e.response.text[:200]}")
                last_error = e
                continue
            except httpx.HTTPError as e:
                logger.warning(f"Network error with {model}: {str(e)}")
                last_error = e
                continue
            except Exception as e:
                logger.warning(f"Unexpected error with {model}: {str(e)}")
                last_error = e
                continue

        raise Exception(f"All OpenRouter models failed. Last error: {last_error}")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

