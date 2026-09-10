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
from dwr_eo_toolkit.api.routes import (  # noqa: F401 — import registers routes
    downloads_router,
    get_provider,
)
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


# ---------------------------------------------------------------------------
# POST /downloads vs POST /downloads/start
#
# These two used to share the collection path. `create_download` registers a
# pending row and touches nothing external; `start_download` runs a real CMR
# query and writes files. Collapsing them meant the cheap seeding path the
# CRUD tests relied on no longer existed, and a POST to the collection had a
# long blocking side effect. The split is what these tests pin.
# ---------------------------------------------------------------------------


class FakeGranule:
    def __init__(self, name):
        self.name = name


class FakeProvider:
    """Stands in for EarthAccessProvider. Records calls, touches no network."""

    def __init__(self, granules=2, files=None):
        self._granules = [FakeGranule(f"g{i}") for i in range(granules)]
        self._files = files
        self.search_calls = []
        self.download_calls = []

    def search(self, product, bounding_box, start_date, end_date, max_results):
        self.search_calls.append(
            {
                "product": product,
                "bounding_box": bounding_box,
                "start_date": start_date,
                "end_date": end_date,
                "max_results": max_results,
            }
        )
        return self._granules, len(self._granules)

    def download(self, granules, output_dir, max_workers=3, show_progress=False):
        self.download_calls.append({"n": len(granules), "output_dir": output_dir})
        if self._files is not None:
            return self._files
        return [f"{output_dir}/{g.name}.h5" for g in granules]


@pytest.fixture
def provider():
    return FakeProvider()


@pytest.fixture
def dl_client(db_session, provider):
    """TestClient with both the DB and the granule provider overridden."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_provider] = lambda: provider
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


BBOX = {"min_lon": -121.85, "min_lat": 38.35, "max_lon": -121.55, "max_lat": 38.80}


def _start_payload(tmp_path, **overrides):
    payload = {
        "product": "ECOSTRESS",
        **BBOX,
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "max_results": 2,
        "output_dir": str(tmp_path),
    }
    payload.update(overrides)
    return payload


class TestDownloadCreateIsSideEffectFree:
    def test_create_does_not_require_a_bbox(self, dl_client, provider):
        """Registering a download must stay cheap.

        If this starts failing with 422s about min_lon, the synchronous
        download has been wired back onto the collection path.
        """
        resp = dl_client.post(
            "/api/v1/downloads",
            json={
                "product": "MODIS",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "pending"
        assert provider.search_calls == []
        assert provider.download_calls == []

    def test_create_rejects_missing_product(self, dl_client):
        resp = dl_client.post(
            "/api/v1/downloads",
            json={"start_date": "2024-01-01", "end_date": "2024-01-31"},
        )
        assert resp.status_code == 422
        assert {"body", "product"} <= {
            tuple(e["loc"])[i] for e in resp.json()["detail"] for i in range(len(e["loc"]))
        }


class TestDownloadStartEndpoint:
    def test_start_downloads_and_records_the_session(self, dl_client, provider, tmp_path):
        resp = dl_client.post("/api/v1/downloads/start", json=_start_payload(tmp_path))
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["status"] == "completed"
        assert body["granules_found"] == 2
        assert body["files_downloaded"] == 2
        assert body["download_session_id"]

        # bbox reached the provider in CMR order
        assert provider.search_calls[0]["bounding_box"] == (
            BBOX["min_lon"],
            BBOX["min_lat"],
            BBOX["max_lon"],
            BBOX["max_lat"],
        )

        # and the session is retrievable through the CRUD routes
        listed = dl_client.get("/api/v1/downloads").json()
        assert listed["count"] == 1
        assert listed["downloads"][0]["id"] == body["download_session_id"]

    def test_partial_download_is_reported(self, db_session, tmp_path):
        """Fewer files back than granules found is 'partial', not 'completed'."""
        half = FakeProvider(granules=2, files=["only-one.h5"])

        def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_provider] = lambda: half
        try:
            with TestClient(app) as c:
                resp = c.post("/api/v1/downloads/start", json=_start_payload(tmp_path))
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "partial"
        assert body["files_downloaded"] == 1
        assert body["files_failed"] == 1

    def test_start_requires_a_bbox(self, dl_client, provider):
        resp = dl_client.post(
            "/api/v1/downloads/start",
            json={
                "product": "MODIS",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
        )
        assert resp.status_code == 422
        missing = {e["loc"][-1] for e in resp.json()["detail"]}
        assert {"min_lon", "min_lat", "max_lon", "max_lat"} <= missing
        assert provider.search_calls == []

    def test_start_rejects_inverted_bbox(self, dl_client, provider, tmp_path):
        """A transposed box returns zero granules from CMR rather than an error.

        Catching it here turns a silent empty result into a 422.
        """
        payload = _start_payload(tmp_path, min_lon=-121.55, max_lon=-121.85)
        resp = dl_client.post("/api/v1/downloads/start", json=payload)
        assert resp.status_code == 422
        assert "min_lon" in str(resp.json()["detail"])
        assert provider.search_calls == []

    def test_start_rejects_latitude_beyond_90(self, dl_client, tmp_path):
        """Latitude used to be checked against +/-180, so 100 passed."""
        payload = _start_payload(tmp_path, max_lat=100.0)
        resp = dl_client.post("/api/v1/downloads/start", json=payload)
        assert resp.status_code == 422
        assert "atitude" in str(resp.json()["detail"])

    def test_start_rejects_unknown_product(self, dl_client, tmp_path):
        """DownloadStartRequest had no product validator before the split."""
        payload = _start_payload(tmp_path, product="LANDSAT")
        resp = dl_client.post("/api/v1/downloads/start", json=payload)
        assert resp.status_code == 422

    def test_start_rejects_reversed_date_range(self, dl_client, tmp_path):
        payload = _start_payload(tmp_path, start_date="2024-01-31", end_date="2024-01-01")
        resp = dl_client.post("/api/v1/downloads/start", json=payload)
        assert resp.status_code == 422

    def test_search_shares_the_same_validation(self, dl_client, provider):
        """Search and start validate identically -- they share a base model."""
        resp = dl_client.post(
            "/api/v1/downloads/search",
            json={
                "product": "ECOSTRESS",
                "min_lon": -121.55,
                "min_lat": 38.35,
                "max_lon": -121.85,  # inverted
                "max_lat": 38.80,
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
        )
        assert resp.status_code == 422
        assert provider.search_calls == []
