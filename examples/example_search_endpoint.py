"""
Example: /api/v1/downloads/search endpoint

Simple REST endpoint that takes a search request and returns results.
This is a self-contained example showing the pattern.
"""

from typing import List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from fastapi import FastAPI, HTTPException
from dwr_eo_toolkit.providers import EarthAccessProvider

# ==============================================================================
# Request/Response Models (Pydantic V2)
# ==============================================================================

class SearchRequest(BaseModel):
    """Request model for search endpoint"""
    product: str = Field(..., description="Product name (e.g., 'ECOSTRESS', 'MODIS')")
    min_lon: float = Field(..., description="Min longitude")
    min_lat: float = Field(..., description="Min latitude")
    max_lon: float = Field(..., description="Max longitude")
    max_lat: float = Field(..., description="Max latitude")
    start_date: str = Field(..., description="Start date YYYY-MM-DD")
    end_date: str = Field(..., description="End date YYYY-MM-DD")
    max_results: int = Field(100, description="Max granules to return", ge=1, le=2000)

    @field_validator('product')
    @classmethod
    def validate_product(cls, v):
        """Validate product is supported"""
        valid_products = ['ECOSTRESS', 'MODIS']
        if v.upper() not in valid_products:
            raise ValueError(f"Product must be one of {valid_products}")
        return v.upper()

    @field_validator('min_lon', 'min_lat', 'max_lon', 'max_lat')
    @classmethod
    def validate_coords(cls, v):
        """Validate coordinates are reasonable"""
        if not -180 <= v <= 180:
            raise ValueError(f"Coordinate must be between -180 and 180")
        return v

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v):
        """Validate date format"""
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Date must be in format YYYY-MM-DD")
        return v

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v, info):
        """Ensure end_date >= start_date"""
        if 'start_date' in info.data:
            start = datetime.strptime(info.data['start_date'], '%Y-%m-%d')
            end = datetime.strptime(v, '%Y-%m-%d')
            if end < start:
                raise ValueError("end_date must be >= start_date")
        return v

    def get_bbox(self) -> Tuple[float, float, float, float]:
        """Get bounding box as tuple"""
        return (self.min_lon, self.min_lat, self.max_lon, self.max_lat)


class Granule(BaseModel):
    """A single granule in search results"""
    id: str
    title: str
    temporal_start: Optional[str] = None
    temporal_end: Optional[str] = None
    spatial_bounds: Optional[dict] = None
    

class SearchResponse(BaseModel):
    """Response model for search endpoint"""
    success: bool
    message: str
    total: int = Field(0, description="Total granules found")
    returned: int = Field(0, description="Granules returned in this response")
    granules: List[dict] = Field(default_factory=list, description="Granule data")
    request_summary: dict = Field(default_factory=dict, description="Echo of request params")


class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    error: str
    details: Optional[str] = None


# ==============================================================================
# API Endpoint
# ==============================================================================

app = FastAPI(
    title="DWR EO Toolkit API",
    description="Search and download NASA Earth observation imagery",
    version="0.1.0",
)

# Initialize provider (once at startup)
provider = EarthAccessProvider()


@app.post(
    "/api/v1/downloads/search",
    response_model=SearchResponse,
    summary="Search for imagery granules",
    description="""
    Search for NASA Earth observation granules by product, location, and date range.
    
    Returns metadata about available granules that match the search criteria.
    Use the granule IDs from the response to download files.
    """,
)
async def search_imagery(request: SearchRequest) -> SearchResponse:
    """
    Search for imagery granules.
    
    Args:
        request: Search parameters (product, bbox, dates, etc.)
    
    Returns:
        SearchResponse with matching granules
    
    Raises:
        HTTPException: If search fails
    """
    try:
        # Log the request
        print(f"🔍 Search request: {request.product}")
        print(f"   Bbox: {request.get_bbox()}")
        print(f"   Dates: {request.start_date} to {request.end_date}")
        
        # Execute search
        granules, total = provider.search(
            product=request.product,
            bounding_box=request.get_bbox(),
            start_date=request.start_date,
            end_date=request.end_date,
            max_results=request.max_results,
        )
        
        print(f"   ✅ Found {total} granules (returning {len(granules)})")
        
        # Build response
        return SearchResponse(
            success=True,
            message=f"Found {total} granules matching criteria",
            total=total,
            returned=len(granules),
            granules=[
                {
                    "id": str(g),
                    "title": str(g),
                    "raw": str(g),  # For now, just store string representation
                }
                for g in granules
            ],
            request_summary={
                "product": request.product,
                "bbox": request.get_bbox(),
                "start_date": request.start_date,
                "end_date": request.end_date,
            }
        )
    
    except ValueError as e:
        # Validation error
        print(f"❌ Validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    
    except Exception as e:
        # Search failed
        print(f"❌ Search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}",
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "DWR EO Toolkit API",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "search": "/api/v1/downloads/search",
        }
    }


# ==============================================================================
# Example Usage / Testing
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("""
    Starting API server...
    
    Try it out:
    
    1. Visit: http://localhost:8000/docs
       (Interactive Swagger UI)
    
    2. Or curl from terminal:
       curl -X POST http://localhost:8000/api/v1/downloads/search \\
         -H "Content-Type: application/json" \\
         -d '{
           "product": "ECOSTRESS",
           "min_lon": -122.82,
           "min_lat": 36.78,
           "max_lon": -120.94,
           "max_lat": 38.25,
           "start_date": "2024-12-29",
           "end_date": "2024-12-31",
           "max_results": 10
         }'
    
    3. Check health:
       curl http://localhost:8000/health
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
