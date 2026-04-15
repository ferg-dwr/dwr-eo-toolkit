from nasa_eo_data.providers import EarthAccessProvider
import earthaccess

# Authenticate
earthaccess.login(strategy="environment")

# Create provider
provider = EarthAccessProvider()

# Search
results, total = provider.search(
    product="ECOSTRESS",
    bounding_box=(-122.82, 36.78, -120.94, 38.25),
    start_date="2020-01-01",
    end_date="2026-04-13"
)

print(f"Found {total} granules")