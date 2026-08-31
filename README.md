# RecoverIQ

**AI-Powered Revenue Recovery Agent for Razorpay**

RecoverIQ is an intelligent system designed to automate and optimize the process of recovering failed payments and managing outstanding invoices. Built for the Razorpay Buildathon 2026, it leverages advanced LLMs and Razorpay's API to ensure seamless payment recovery.

## Architecture

```
+----------------+      +----------------+      +------------------+
|                |      |                |      |                  |
|  Dashboard     |<---->|  RecoverIQ API |<---->|  Razorpay API    |
|  (Streamlit)   |      |  (FastAPI)     |      |                  |
|                |      |                |      |                  |
+----------------+      +-------+--------+      +------------------+
                                |
                                v
                        +-------+--------+
                        |                |
                        |  Database      |
                        |  (SQLite)      |
                        |                |
                        +----------------+
```

## Features

- **Automated Payment Recovery**: Detects failed payments and initiates recovery workflows.
- **Intelligent Retry Logic**: Uses configurable rules for retries (cooldowns, max retries, high-value thresholds).
- **Quiet Hours Enforcement**: Respects user-defined quiet hours to avoid sending notifications at inappropriate times.
- **LLM-Powered Communication**: Uses OpenRouter models to generate personalized and effective recovery messages.
- **Real-time Dashboard**: Streamlit-based dashboard for monitoring recovery metrics and system health.

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Razorpay Account (Test Mode)
- OpenRouter API Key

### 2. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/yourusername/recoveriq.git
cd recoveriq
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 3. Environment Setup

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your `OPENROUTER_API_KEY`, `RAZORPAY_KEY_ID`, and `RAZORPAY_KEY_SECRET`.

### 4. Running the Application

Run the FastAPI backend:

```bash
recoveriq
# or
uvicorn api.main:app --reload
```

Run the Streamlit dashboard (in a separate terminal):

```bash
streamlit run dashboard/app.py
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |
| POST | `/webhooks/razorpay` | Razorpay webhook endpoint |
| GET | `/api/v1/payments` | List payments |
| POST | `/api/v1/payments/{payment_id}/retry` | Manually trigger a retry |
| GET | `/api/v1/metrics` | Get system metrics for dashboard |

## Tech Stack

- **Backend Framework**: FastAPI
- **Data Validation**: Pydantic v2
- **Database**: SQLite with SQLAlchemy and aiosqlite (Async)
- **LLM Integration**: OpenRouter (Gemini, DeepSeek, Llama)
- **Frontend Dashboard**: Streamlit, Plotly, Pandas
- **Tooling**: Ruff, Pytest

## License

MIT License
