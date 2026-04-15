"""Simple search and download example using earthaccess."""

from nasa_eo_data.providers import EarthAccessProvider

# Create provider
provider = EarthAccessProvider()

# Search for ECOSTRESS data
print("Searching for ECOSTRESS granules...")
granules, total = provider.search(
    product="ECOSTRESS",
    bounding_box=(-122.82, 36.78, -120.94, 38.25),  # California
    start_date="2020-01-01",
    end_date="2026-04-13",
    max_results=5
)

print(f"✅ Found {total} granules")
for granule in granules[:3]:
    print(f"  - {granule.get('umm', {}).get('GranuleUR', 'Unknown')}")

# Download
print("\nDownloading granules...")
files = provider.download(granules[:2], "./data/ecostress")

print(f"✅ Downloaded {len(files)} files")
for file in files[:3]:
    print(f"  - {file}")