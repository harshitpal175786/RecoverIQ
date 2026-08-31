import json
import httpx
from config import get_settings
from schemas.transaction import Transaction
from schemas.decision import AgentDecision
from agent.prompts import SYSTEM_PROMPT, build_user_prompt

class AIReasoner:
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(timeout=self.settings.LLM_TIMEOUT_SECONDS)
    
    async def reason(self, transaction: Transaction, context: dict) -> AgentDecision:
        """Call OpenRouter LLM and parse response into AgentDecision."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(transaction, context)}
        ]
        
        try:
            response_data = await self._call_openrouter(messages)
            content = response_data["choices"][0]["message"]["content"]
            
            # Clean possible markdown wrapping
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]
                
            decision_dict = json.loads(content)
            return AgentDecision(**decision_dict)
        except Exception as e:
            # Raise exception to be caught by the pipeline for fallback
            raise RuntimeError(f"AI reasoning failed: {str(e)}")
    
    async def _call_openrouter(self, messages: list[dict]) -> dict:
        """Call OpenRouter API with fallback models."""
        headers = {
            "Authorization": f"Bearer {self.settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        models_to_try = [self.settings.OPENROUTER_MODEL] + self.settings.fallback_models_list
        last_error = None
        
        for model in models_to_try:
            payload = {
                "model": model,
                "messages": messages,
                "response_format": {"type": "json_object"},
                "temperature": 0.2
            }
            try:
                response = await self.client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                last_error = e
                continue
                
        raise Exception(f"All models failed. Last error: {last_error}")
