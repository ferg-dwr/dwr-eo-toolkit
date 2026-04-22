"""
Working example: Query and download imagery
Fixed version - handles earthaccess DataGranule objects correctly
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from dwr_eo_toolkit.providers import EarthAccessProvider

# Load environment variables
load_dotenv()

# Configuration
EARTHDATA_TOKEN = os.getenv("EARTHDATA_TOKEN")
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "./downloads"))
DEFAULT_PRODUCT = os.getenv("DEFAULT_PRODUCT", "ECOSTRESS")
DEFAULT_START_DATE = os.getenv("DEFAULT_START_DATE", "2024-01-01")
DEFAULT_END_DATE = os.getenv("DEFAULT_END_DATE", "2024-12-31")

# Parse bounding box
BBOX_STR = os.getenv("DEFAULT_BBOX", "-122.82,36.78,-120.94,38.25")
BBOX = tuple(map(float, BBOX_STR.split(",")))

# Setup
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

print("Configuration loaded from .env:")
print(f"  Product: {DEFAULT_PRODUCT}")
print(f"  Date range: {DEFAULT_START_DATE} to {DEFAULT_END_DATE}")
print(f"  Bounding box: {BBOX}")
print(f"  Download dir: {DOWNLOAD_DIR}")

# Verify token
if not EARTHDATA_TOKEN:
    raise ValueError(
        "EARTHDATA_TOKEN not set in .env!\n"
        "Get your token at: https://urs.earthdata.nasa.gov/user_settings/generate_token"
    )

# Step 1: Search for imagery
print(f"\n🔍 Searching for {DEFAULT_PRODUCT} data...")
provider = EarthAccessProvider()

try:
    results, total = provider.search(
        product=DEFAULT_PRODUCT,
        bounding_box=BBOX,
        start_date=DEFAULT_START_DATE,
        end_date=DEFAULT_END_DATE,
    )
    print(f"Found {total} granules")
except Exception as e:
    print(f"Search failed: {e}")
    exit(1)

if not results:
    print("No results found. Try adjusting search parameters.")
    exit(0)

print("First 3 granules:")
for i, granule in enumerate(results[:3]):
    print(f"  {i + 1}. {granule}")

# Step 2: Download using the provider's download method
print(f"\nDownloading {min(len(results), 3)} granules...")

try:
    # Use the provider's download method which handles earthaccess DataGranule objects
    downloaded_files = provider.download(
        results[:3],  # Download first 3
        str(DOWNLOAD_DIR),
        max_workers=3,
    )

    print("\nDownload Complete!")
    print(f"  Downloaded: {len(downloaded_files)} files")

    for file_path in downloaded_files:
        file_size = Path(file_path).stat().st_size / 1024 / 1024
        print(f"    - {Path(file_path).name} ({file_size:.2f} MB)")

except Exception as e:
    print(f"Download failed: {e}")
    import traceback

    traceback.print_exc()
    exit(1)

print(f"\nFiles saved to: {DOWNLOAD_DIR}")
print("Done!")
