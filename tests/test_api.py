"""
Test suite for the FastAPI REST API.

Uses a SQLite database via dependency override so no
running PostgreSQL is required.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from dwr_eo_toolkit.api.app import app
from dwr_eo_toolkit.api.routes import downloads_router  # noqa: F401 — import registers routes
from dwr_eo_toolkit.database.connection import get_db
from dwr_eo_toolkit.database.models import (
    Base,
)

SQLITE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session():
    """Create a clean in-memory SQLite DB for each test function."""
    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testingsession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = testingsession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(scope="function")
def client(db_session):
    """TestClient with DB dependency overridden to use the in-memory SQLite session."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestRootEndpoints:
    def test_root_returns_service_info(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "DWR EO Toolkit API"
        assert "docs" in data

    def test_health_check_returns_healthy(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "database" in data
        assert "timestamp" in data

    def test_status_returns_api_info(self, client):
        resp = client.get("/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["api"]["status"] == "running"
        assert "environment" in data


class TestDownloadsEndpoints:
    def test_list_downloads_empty(self, client):
        resp = client.get("/api/v1/downloads")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["downloads"] == []

    def test_create_download_returns_201(self, client):
        payload = {"product": "MODIS", "start_date": "2024-01-01", "end_date": "2024-01-31"}
        resp = client.post("/api/v1/downloads", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["product"] == "MODIS"
        assert data["status"] == "pending"
        assert "id" in data

    def test_create_download_missing_field_returns_422(self, client):
        resp = client.post("/api/v1/downloads", json={"product": "MODIS"})
        assert resp.status_code == 422

    def test_get_download_returns_200(self, client):
        payload = {"product": "ECOSTRESS", "start_date": "2024-01-01", "end_date": "2024-01-31"}
        created = client.post("/api/v1/downloads", json=payload).json()
        resp = client.get(f"/api/v1/downloads/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_download_not_found_returns_404(self, client):
        resp = client.get("/api/v1/downloads/nonexistent-id")
        assert resp.status_code == 404

    def test_update_download_returns_200(self, client):
        payload = {"product": "MODIS", "start_date": "2024-01-01", "end_date": "2024-01-31"}
        created = client.post("/api/v1/downloads", json=payload).json()
        resp = client.patch(f"/api/v1/downloads/{created['id']}")
        assert resp.status_code == 200

    def test_update_download_not_found_returns_404(self, client):
        resp = client.patch("/api/v1/downloads/nonexistent-id")
        assert resp.status_code == 404

    def test_cancel_download_returns_204(self, client):
        payload = {"product": "MODIS", "start_date": "2024-01-01", "end_date": "2024-01-31"}
        created = client.post("/api/v1/downloads", json=payload).json()
        resp = client.delete(f"/api/v1/downloads/{created['id']}")
        assert resp.status_code == 204

    def test_cancel_download_not_found_returns_404(self, client):
        resp = client.delete("/api/v1/downloads/nonexistent-id")
        assert resp.status_code == 404

    def test_list_downloads_after_create(self, client):
        payload = {"product": "MODIS", "start_date": "2024-01-01", "end_date": "2024-01-31"}
        client.post("/api/v1/downloads", json=payload)
        resp = client.get("/api/v1/downloads")
        assert resp.json()["count"] == 1


class TestBatchesEndpoints:
    def test_list_batches_empty(self, client):
        resp = client.get("/api/v1/batches")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_create_batch_returns_201(self, client):
        payload = {"name": "Jan 2024 Batch", "description": "Test batch"}
        resp = client.post("/api/v1/batches", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Jan 2024 Batch"
        assert "id" in data

    def test_create_batch_missing_name_returns_422(self, client):
        resp = client.post("/api/v1/batches", json={"description": "no name"})
        assert resp.status_code == 422

    def test_get_batch_returns_200(self, client):
        payload = {"name": "My Batch"}
        created = client.post("/api/v1/batches", json=payload).json()
        resp = client.get(f"/api/v1/batches/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_batch_not_found_returns_404(self, client):
        resp = client.get("/api/v1/batches/nonexistent-id")
        assert resp.status_code == 404

    def test_update_batch_returns_200(self, client):
        created = client.post("/api/v1/batches", json={"name": "B"}).json()
        resp = client.patch(f"/api/v1/batches/{created['id']}")
        assert resp.status_code == 200

    def test_update_batch_not_found_returns_404(self, client):
        resp = client.patch("/api/v1/batches/nonexistent-id")
        assert resp.status_code == 404

    def test_cancel_batch_returns_204(self, client):
        created = client.post("/api/v1/batches", json={"name": "B"}).json()
        resp = client.delete(f"/api/v1/batches/{created['id']}")
        assert resp.status_code == 204

    def test_cancel_batch_not_found_returns_404(self, client):
        resp = client.delete("/api/v1/batches/nonexistent-id")
        assert resp.status_code == 404


class TestJobsEndpoints:
    _job_payload = {
        "name": "Weekly MODIS",
        "product": "MODIS",
        "schedule_type": "weekly",
        "start_date": "2024-01-01",
    }

    def test_list_jobs_empty(self, client):
        resp = client.get("/api/v1/jobs")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_schedule_job_returns_201(self, client):
        resp = client.post("/api/v1/jobs/schedule", json=self._job_payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Weekly MODIS"
        assert "id" in data

    def test_schedule_job_missing_field_returns_422(self, client):
        resp = client.post("/api/v1/jobs/schedule", json={"name": "J"})
        assert resp.status_code == 422

    def test_get_job_returns_200(self, client):
        created = client.post("/api/v1/jobs/schedule", json=self._job_payload).json()
        resp = client.get(f"/api/v1/jobs/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_job_not_found_returns_404(self, client):
        resp = client.get("/api/v1/jobs/nonexistent-id")
        assert resp.status_code == 404

    def test_update_job_returns_200(self, client):
        created = client.post("/api/v1/jobs/schedule", json=self._job_payload).json()
        resp = client.patch(f"/api/v1/jobs/{created['id']}")
        assert resp.status_code == 200

    def test_update_job_not_found_returns_404(self, client):
        resp = client.patch("/api/v1/jobs/nonexistent-id")
        assert resp.status_code == 404

    def test_delete_job_returns_204(self, client):
        created = client.post("/api/v1/jobs/schedule", json=self._job_payload).json()
        resp = client.delete(f"/api/v1/jobs/{created['id']}")
        assert resp.status_code == 204

    def test_delete_job_not_found_returns_404(self, client):
        resp = client.delete("/api/v1/jobs/nonexistent-id")
        assert resp.status_code == 404

    def test_list_jobs_after_schedule(self, client):
        client.post("/api/v1/jobs/schedule", json=self._job_payload)
        resp = client.get("/api/v1/jobs")
        assert resp.json()["count"] == 1


class TestErrorHandling:
    def test_404_returns_json_error(self, client):
        """Custom exception handler returns JSON for HTTPException."""
        resp = client.get("/api/v1/downloads/does-not-exist")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert "timestamp" in data

    def test_openapi_schema_accessible(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        assert "paths" in resp.json()
