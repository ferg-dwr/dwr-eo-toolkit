import earthaccess

# Authenticate
auth = earthaccess.login(strategy="netrc")  # Uses .netrc or env vars

# Search for ECOSTRESS granules
granules = earthaccess.search_data(
    short_name="ECO_L2T_LSTE",
    bounding_box=(-122.82, 36.78, -120.94, 38.25),  # California
    temporal=("2020-01-01", "2026-04-13"),
    count=100
)

print(f"Found {len(granules)} granules")
for granule in granules[:5]:
    print(f"  {granule}")