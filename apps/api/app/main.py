from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.middleware import RequestLoggingMiddleware
from app.db.session import dispose_engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    yield
    await dispose_engine()


app = FastAPI(
    title="FinanceAI API",
    description="Financial operations and responsible AI platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {"name": "FinanceAI API", "docs": "/docs", "version": "0.1.0"}
