import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from data.db import init_db
from api.routes import seed, recovery, metrics, transactions, audit, health, webhooks

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title='RecoverIQ API',
    description='AI Revenue Recovery Agent — Razorpay Buildathon 2026',
    version='0.1.0',
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(seed.router)
app.include_router(transactions.router)
app.include_router(recovery.router)
app.include_router(metrics.router)
app.include_router(audit.router)
app.include_router(webhooks.router)

# Mount Static Frontend
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": "Welcome to RecoverIQ API - AI Revenue Recovery Agent"}
