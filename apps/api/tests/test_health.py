from fastapi.testclient import TestClient

from app.api.v1.routes import health
from app.core.config import Settings
from app.main import app


def test_liveness() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


class FailingConnection:
    async def __aenter__(self):
        raise ConnectionRefusedError("database unavailable")

    async def __aexit__(self, *_: object) -> None:
        return None


class UnavailableEngine:
    def connect(self) -> FailingConnection:
        return FailingConnection()


def test_readiness_returns_service_unavailable_when_database_is_down(monkeypatch) -> None:
    monkeypatch.setattr(health, "engine", UnavailableEngine())

    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is not ready"}


def test_cors_origins_accepts_comma_separated_environment_value() -> None:
    settings = Settings(cors_origins="http://localhost:3000,https://finance.example.com")

    assert settings.cors_origins == [
        "http://localhost:3000",
        "https://finance.example.com",
    ]
