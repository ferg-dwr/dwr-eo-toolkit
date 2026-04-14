#!/usr/bin/env python3
"""
Complete example script demonstrating nasa-eo-data package.

This script shows:
1. Authentication (Phase 1)
2. Provider layer (Phase 2A)
3. Filter layer (Phase 2B)
4. Querying real NASA CMR data

Requirements:
- NASA Earthdata Login credentials (env var or .netrc file)
- Internet connection (to query CMR API)

Usage:
    python3 example_full_workflow.py
"""

import logging
from datetime import datetime

from nasa_eo_data.core.auth import EarthDataLoginAuth
from nasa_eo_data.providers import CMRProvider
from nasa_eo_data.filters import Query

# Setup logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run the complete example workflow."""
    
    print("\n" + "="*70)
    print("NASA EARTH OBSERVATION DATA - EXAMPLE WORKFLOW")
    print("="*70 + "\n")
    
    # ==================== Phase 1: Authentication ====================
    print("PHASE 1: AUTHENTICATION")
    print("-" * 70)
    
    try:
        # Initialize authentication (tries token -> .netrc -> env vars)
        auth = EarthDataLoginAuth()
        print("Authentication initialized")
        
        # Get a bearer token
        token = auth.get_bearer_token()
        print(f"Bearer token obtained: {token[:20]}...{token[-10:]}")
        
    except Exception as e:
        print(f"Authentication failed: {e}")
        print("\nMake sure you have NASA Earthdata credentials set up:")
        print("  1. Environment variable: export EARTHDATA_TOKEN=your_token")
        print("  2. Or .netrc file with: machine urs.earthdata.nasa.gov login USERNAME password PASSWORD")
        print("  3. Or get a token from: https://urs.earthdata.nasa.gov/user_settings/generate_token")
        return
    
    # ==================== Phase 2A: Provider Layer ====================
    print("\nPHASE 2A: PROVIDER LAYER")
    print("-" * 70)
    
    # Create CMR provider
    provider = CMRProvider(auth)
    print("CMR Provider initialized")
    
    # Validate that ECOSTRESS exists
    print("\nSearching for ECOSTRESS products in CMR...")
    ecostress_product = "ECOSTRESS"
    if provider.validate_product(ecostress_product):
        print(f"ECOSTRESS products found in CMR")
    else:
        print(f"ECOSTRESS products not found in CMR")
        return
    
    # Get product metadata
    print("\nFetching ECOSTRESS metadata...")
    try:
        metadata = provider.get_metadata(ecostress_product)
        print(f"Product: {metadata['short_name']}")
        print(f"Provider: {metadata['provider']}")
        print(f"Resolution: {metadata['spatial_resolution']}")
        print(f"Processing Level: {metadata['processing_level']}")
    except Exception as e:
        print(f"Could not fetch metadata: {e}")
    
    # ==================== Phase 2B: Filter Layer ====================
    print("\nPHASE 2B: FILTER LAYER")
    print("-" * 70)
    
    # Define search parameters based on real ECOSTRESS availability
    # California Central Valley region with known ECOSTRESS data
    print("\nBuilding query with filters...")
    
    bbox = (-122.82, 36.78, -120.94, 38.25)
    print(f"Spatial: Bounding box {bbox}")
    
    # Search for data from 2020 onwards (ECOSTRESS started in 2018)
    start_date = "2020-01-01"
    end_date = "2026-04-13"
    print(f"Temporal: {start_date} to {end_date}")
    
    print(f"Cloud cover: max 20%")
    print(f"Processing level: L2")
    
    # ==================== Fluent Query Builder ====================
    print("\nFLUENT QUERY API")
    print("-" * 70)
    
    # Build query using fluent API (method chaining)
    query = (Query()
        .with_product("ECOSTRESS")
        .with_spatial_bounds(*bbox)
        .with_date_range(start_date, end_date)
        .with_cloud_cover(20)
        .with_processing_level("L2")
    )
    
    print("Query built successfully")
    print(f"\nQuery Summary:")
    print(f"{query.filters_summary()}")
    
    # Convert to parameters (useful for debugging)
    params = query.to_params()
    print(f"\nQuery Parameters:")
    for key, value in params.items():
        if key == "bounding_box":
            print(f"  {key}: min_lon={value[0]}, min_lat={value[1]}, max_lon={value[2]}, max_lat={value[3]}")
        else:
            print(f"  {key}: {value}")
    
    # ==================== Execute Query ====================
    print("\nEXECUTING QUERY AGAINST CMR")
    print("-" * 70)
    
    print(f"\nSearching CMR for ECOSTRESS granules...")
    print(f"This may take a moment...\n")
    
    try:
        # Execute the query
        results, total = query.execute(provider)
        
        print(f"Query succeeded!")
        print(f"\nResults:")
        print(f"  Total granules found: {total}")
        print(f"  Granules returned: {len(results)}")
        
        # ==================== Display Results ====================
        if results:
            print(f"\nFirst granule details:")
            first_granule = results[0]
            
            # Extract useful info
            if "umm" in first_granule:
                umm = first_granule["umm"]
                granule_id = umm.get("GranuleUR", "N/A")
                collection = umm.get("CollectionReference", {})
                collection_id = collection.get("ShortName", "N/A")
                
                print(f"  Granule ID: {granule_id}")
                print(f"  Collection: {collection_id}")
                
                # Get download URLs if available
                related_urls = umm.get("RelatedUrls", [])
                if related_urls:
                    print(f"  Related URLs: {len(related_urls)}")
                    for url_info in related_urls[:2]:
                        url = url_info.get("URL", "")
                        rel_type = url_info.get("Type", "")
                        if url:
                            print(f"    - {rel_type}: {url[:60]}...")
        else:
            print("\nNo results returned for this query.")
            print("This may indicate:")
            print("  - No ECOSTRESS data available in this region")
            print("  - Data only available for different dates")
            print("  - Collection is not fully indexed yet")
        
    except Exception as e:
        print(f"Query execution failed: {e}")
        print(f"\nPossible reasons:")
        print(f"  - Network connectivity issue")
        print(f"  - Invalid product name")
        print(f"  - Authentication expired")
        return
    
    # ==================== Summary ====================
    print("\n" + "="*70)
    print("WORKFLOW COMPLETE")
    print("="*70)
    
    print(f"""
            What you just did:
            1. Authenticated to NASA Earthdata
            2. Initialized CMR Provider (Phase 2A)
            3. Built a query using Filter Layer (Phase 2B)
            4. Executed the query against NASA CMR API
            5. Retrieved ECOSTRESS thermal imagery metadata

            Next Steps:
            - Phase 2C: Add ECOSTRESS-specific metadata
            - Phase 3: Implement download manager
            - Phase 4: Build high-level query API for DWR

            For more examples, see:
            - example_filters_only.py: Test filters without credentials
            - example_providers_only.py: Test providers without filters
            """)


if __name__ == "__main__":
    main()