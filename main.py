from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

from routers import analysis, payments, admin, auth

app = FastAPI(
    title="SMC Lens API",
    description="SMC/ICT Forex Trading Assistant — Backend API",
    version="1.0.0"
)

# CORS
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "https://smclens.com", "https://www.smclens.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Routers
app.include_router(auth.router)
app.include_router(analysis.router)
app.include_router(payments.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    return {
        "app": "SMC Lens API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
