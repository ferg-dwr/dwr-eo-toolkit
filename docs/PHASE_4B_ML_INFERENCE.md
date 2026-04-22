# Phase 4B: ML Model Integration & Inference Pipeline

## Overview
Extend the DWR EO Toolkit to support automated ML inference on downloaded remote sensing data. Downloads trigger inference jobs that run PyTorch models (linear regression, random forest, etc.) and output results as GeoTIFF/COG to PostGIS or filesystem.

## Architecture

```
1. Download Completes (Phase 4A)
   ↓
2. WebSocket Notifies Completion
   ↓
3. Inference Job Auto-Triggered
   ↓
4. Model Downloaded from GitHub (if needed)
   ↓
5. Model Inference on Raster Data
   ↓
6. Output GeoTIFF/COG Generated
   ↓
7. Results Stored (PostGIS + Filesystem)
   ↓
8. WebSocket Broadcasts Completion
```

## Core Components

### 1. Model Manager
**Purpose**: Manage PyTorch models from GitHub releases

```
dwr_eo_toolkit/models/
├── manager.py          # Download, cache, version models
├── registry.py         # Track available models
└── cache/              # Local model storage
    └── {model_name}/{version}/
```

**Key Functions**:
- `download_model(repo, version)` - Fetch from GitHub releases
- `get_cached_model(name, version)` - Load from cache
- `list_available_models()` - Query registry
- Cache strategy: ~100GB limit with LRU eviction

### 2. Geospatial Data Handler
**Purpose**: Read/write rasters with geospatial metadata

```
dwr_eo_toolkit/geospatial/
├── reader.py           # Read GeoTIFF/COG, band selection, reprojection
├── writer.py           # Write GeoTIFF/COG with metadata
└── validator.py        # Validate raster compatibility
```

**Key Functions**:
- `read_raster(path, bands=[])` - Load with metadata (CRS, transform, etc.)
- `write_cog(array, metadata, output_path)` - Create COG with proper formatting
- `reproject_to_match(source_raster, target_raster)` - Align coordinate systems
- `extract_bands(path, band_indices)` - Get specific bands for model input

### 3. Inference Engine
**Purpose**: Execute PyTorch models on raster data

```
dwr_eo_toolkit/inference/
├── engine.py           # PyTorch model execution
├── processors/         # Input/output preprocessing
│   ├── linear_regression.py
│   └── random_forest.py
└── pipeline.py         # Orchestrate download→infer→output
```

**Key Functions**:
- `load_model(path)` - PyTorch model loader
- `infer(model, input_raster)` - Run inference
- `prepare_input(raster, expected_shape)` - Normalize input
- `postprocess_output(result, metadata)` - Format output raster

### 4. Inference Job System
**Purpose**: Manage inference as async jobs (similar to downloads)

**Database Schema**:
```sql
CREATE TABLE inference_jobs (
    id UUID PRIMARY KEY,
    download_id UUID REFERENCES download_sessions(id),
    model_name VARCHAR,
    model_version VARCHAR,
    status VARCHAR (pending, processing, completed, failed),
    input_raster_path VARCHAR,
    output_raster_path VARCHAR,
    inference_metadata JSONB,  -- timing, processing info
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 5. REST API Endpoints
**Purpose**: Expose inference capabilities via HTTP

```
Models API:
  GET    /api/v1/models                    # List available models
  POST   /api/v1/models/download           # Download model from GitHub
  GET    /api/v1/models/{name}/{version}   # Get model details

Inference API:
  GET    /api/v1/inference                 # List inference jobs
  POST   /api/v1/inference/{download_id}   # Trigger manual inference
  GET    /api/v1/inference/{job_id}        # Get inference results
  WebSocket /ws/inference/{job_id}         # Real-time inference updates
```

### 6. Database Storage Options
**PostGIS**:
- Store raster metadata in PostGIS
- Reference paths to GeoTIFF/COG files in filesystem
- Enable spatial queries

**Filesystem**:
- Store rasters in organized directory structure:
  ```
  outputs/
  ├── {download_id}/
  │   ├── {model_name}_{version}_output.tif
  │   └── {model_name}_{version}_metadata.json
  ```

## Workflow: Download → Inference → Output

### 1. Download Completion Event
```python
# From Phase 4A
download_completes() 
  → websocket.broadcast("download_complete", download_id)
  → trigger_inference_pipeline(download_id)
```

### 2. Inference Pipeline
```python
async def trigger_inference_pipeline(download_id):
    # Get download metadata
    download = get_download(download_id)
    raster_paths = download.output_paths  # GeoTIFF files
    
    # For each configured model
    for model_config in get_inference_models():
        job = create_inference_job(download_id, model_config)
        
        # Download model if needed
        model = model_manager.get_model(
            model_config.name, 
            model_config.version
        )
        
        # Prepare input (band selection, reprojection)
        input_data = geospatial.prepare_input(
            raster_paths,
            model.expected_bands,
            model.expected_crs
        )
        
        # Run inference
        inference_result = model(input_data)
        
        # Write output raster
        output_path = geospatial.write_cog(
            inference_result,
            metadata=download.metadata,
            output_dir=f"outputs/{download_id}"
        )
        
        # Store in database
        save_inference_result(job, output_path)
        
        # Broadcast completion
        websocket.broadcast("inference_complete", job_id)
```

### 3. Example: ECOSTRESS Sharpening Model
```python
# Model from GitHub: username/ecostress-sharpener/releases/v1.0
model_config = {
    "name": "ecostress-sharpener",
    "version": "v1.0",
    "repo": "username/ecostress-sharpener",
    "input_bands": ["ECOSTRESS_thermal_3", "ECOSTRESS_thermal_2"],
    "expected_crs": "EPSG:4326",
    "output_type": "float32",
    "output_bands": ["thermal_sharpened"]
}

# Automatic inference on ECOSTRESS downloads
if download.product == "ECOSTRESS":
    trigger_inference_pipeline(download_id, [model_config])
```

## Dependencies
```toml
[project.optional-dependencies]
inference = [
    "torch>=2.0.0",
    "rasterio>=1.3.0",
    "rioxarray>=0.15.0",
    "numpy>=1.24.0",
    "gdal>=3.7.0",
]
```

## Phase 4B Milestones

### M1: Model Management
- [ ] GitHub release downloader
- [ ] Model cache system
- [ ] Model registry
- [ ] Tests for model loading

### M2: Geospatial Data Handling
- [ ] Raster reader (GeoTIFF/COG)
- [ ] Raster writer (COG creation)
- [ ] Band selection & reprojection
- [ ] Tests for geospatial operations

### M3: Inference Engine
- [ ] PyTorch model executor
- [ ] Input/output preprocessing
- [ ] Linear regression processor
- [ ] Random forest processor
- [ ] Tests for inference

### M4: Job System & API
- [ ] InferenceJob database model
- [ ] Auto-trigger on download completion
- [ ] REST API endpoints
- [ ] WebSocket updates
- [ ] Tests for job orchestration

### M5: Storage Integration
- [ ] PostGIS backend
- [ ] Filesystem backend
- [ ] Result metadata storage
- [ ] Tests for storage

### M6: Documentation & Examples
- [ ] API documentation
- [ ] Model format spec
- [ ] Deployment guide
- [ ] Example workflows

## Success Criteria
- [ ] Inference jobs auto-trigger on download completion
- [ ] Models downloaded from GitHub and cached locally
- [ ] Output rasters written as COG with correct metadata
- [ ] Results stored in PostGIS or filesystem
- [ ] WebSocket provides real-time inference updates
- [ ] >90% test coverage for inference modules
- [ ] End-to-end example: ECOSTRESS → Sharpening Model → COG output

## Future Enhancements (Phase 4C+)
- Multi-GPU inference with Kubernetes workers
- Model versioning & A/B testing
- Batch inference on multiple downloads
- Model serving with TorchServe
- GPU resource management
- Inference result caching
