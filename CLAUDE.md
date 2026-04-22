# Claude Code Configuration

## Project Context
- **Project**: DWR EO Toolkit - ML inference on remote sensing data
- **Phase**: 4A complete, 4B (ML inference) planned
- **Key Files**: 
  - `/docs/ARCHITECTURE.md` — System design and modules
  - `/docs/PHASE_4B_ML_INFERENCE.md` — Next phase specifications
  - `/pyproject.toml` — Dependencies and config

## Development Preferences
- **Python**: 3.11+ (dropped 3.8-3.9)
- **Type Safety**: mypy clean, Pydantic v2, all functions typed
- **Testing**: Integration tests use real DB (SQLite in-memory), not mocks
- **CI/CD**: Local environment must match GitHub Actions (earthaccess>=0.17.0, httpx in dev deps)
- **Branches**: 
  - `main` — Production releases
  - `develop` — Integration branch
  - `feature/*` — Feature branches (e.g., `feature/phase-4b-inference`)

## Key Requirements
- 476 tests passing (100%), 0 type errors, 0 warnings
- Docker/docker-compose for local development
- REST API with WebSocket real-time updates
- Auto-trigger inference on download completion
- Output GeoTIFF/COG to PostGIS or filesystem

## GitHub Issues Status
- **Phase 4A** (ready to close): #33, #34, #35, #36, #40
- **Phase 4B** (update to in-progress): #37, #38, #39
- Comments ready in project documentation

## Next Phase (Phase 4B)
1. Model manager (GitHub releases, PyTorch, caching)
2. Geospatial raster handler (GeoTIFF/COG reader/writer)
3. Inference engine (PyTorch model executor)
4. Job system (auto-trigger on download)
5. REST API for models and inference
6. Storage backends (PostGIS + filesystem)

See `/docs/PHASE_4B_ML_INFERENCE.md` for detailed architecture.
