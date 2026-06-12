import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.api import router

app = FastAPI(title="TW Stock Sentiment Portfolio", version="0.1.0")

_default_origins = "http://localhost:3000,http://127.0.0.1:3000"
_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", _default_origins).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
