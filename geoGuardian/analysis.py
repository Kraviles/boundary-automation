import requests
import pandas as pd
import time

BASE_URL = "https://www.geoboundaries.org/api/current/gbOpen"
ADM_LEVELS = ["ADM0", "ADM1", "ADM2", "ADM3", "ADM4"]

def build_country_iso_from_csv(csv_path):
    """
    Reads a CSV of countries and their ISO codes.
    Returns a dictionary mapping the country to its iso code
    """
    iso = pd.read_csv(csv_path)
    iso.columns = iso.columns.str.strip() # clean the column names

    return dict(zip(iso['Country or Area'], iso['ISO-alpha3 code']))

def fetch_single_boundary(iso_code, adm):
    """
    Fetch a single ISO + ADM layer from the geoBoundaries API
    returns:
        - dictionary of data if exists
        - None if the data is missing
    """
    url = f"{BASE_URL}/{iso_code}/{adm}/"

    response = requests.get(url, timeout=10)

    if response.stsatus_code == 200:
        return response.json()

    if response.status_code == 404:
        return None

    # other errors
    response.raise_for_status()

    return response.json()

# Full analysis across all countries + ADM levels

def run_full_analysis(csv_path: str):
    """
    Loops through every country and ADM level
    Returns:
        - records 
        - missing 
    """
    country_iso = build_country_iso_from_csv(csv_path)
    records = []
    missing = []

    for country, iso, in country_iso_dict.items():

        for adm_level in ADM_LEVELS:
            data = fetch_single_boundary(iso, adm_level)
            if data is None:
                missing.append((country, iso, adm))
                continue
            records.append({
                "Country": country,
                "ISO": iso,
                "BoundaryType": adm,
                "BoundaryName": data.get("boundaryName"),
                "License": data.get("boundaryLicense"),
                "License Source": data.get("licenseSource"),
                "Source": data.get("boundarySourceURL"),
                "Year": data.get("boundaryYearRepresented"),
                "GeoJSON": data.get("gjDownloadURL"),
            })
            time.sleep(0.2)

    return records, missing



acceptable_licenses = ["CC0 1.0 Universal (CC0 1.0) Public Domain Dedication",
                       "Creative Commons Attribution 2.5 India (CC BY 2.5 IN)",
                       "Creative Commons Attribution 3.0 License",
                       "Public Domain",
                       "Other - Direct Permission",
                       "Creative Commons Attribution 4.0 International (CC BY 4.0)",
                       "Creative Commons Attribution 4.0 (CC BY 4.0)",
                       "Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)",
                       "Data license Germany - Attribution - Version 2.0",
                       "MIMU Data License (MIMU)",
                       "Open Data Commons Attribution License 1.0",
                       "Open Government Licence v3.0",
                       "Open Government Licence v1.0",
                       "Other - Humanitarian",
                       "Singapore Open Data License Version 1.0",
                       "National Institute of Statistics (INE) Data License)",
                       "Korea Open Government License Type 1 (Source Indication)",
                       "Open Data Commons Public Domain Dedication and License (PDDL) v1.0",
                       "UN SALB Data License",
                       "Attribution 2.5 Denmark (CC BY 2.5 DK)",
                       "Creative Commons Attribution 2.5 Generic",
                       "Pixabay License for Content",
                       "Etalab Open License 2.0",
                       "Attribuzione 3.0 Italia (CC BY 3.0 IT)",
                       "Federal Office of Topography swisstopo License",
                       "Open Government Canada 2.0",
                       "Sierra Leone Open License Agreement"
]

# The boundary levels to check
ADM_LEVELS = ["ADM0", "ADM1", "ADM2", "ADM3", "ADM4"]

# Empty list to store results
records = []
# Empty list to store layers with missing data
missing = []

for country, iso_code in country_iso.items():
    for adm in ADM_LEVELS:
        url = f"{BASE_URL}/{iso_code}/{adm}/"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Extract key info from the API response
                records.append({
                    "Country": country,
                    "ISO": iso_code,
                    "BoundaryType": adm,
                    "BoundaryName": data.get("boundaryName", None),
                    "License": data.get("boundaryLicense", None),
                    "License Source": data.get("licenseSource", None),
                    "Source": data.get("boundarySourceURL", None),
                    "Year": data.get("boundaryYearRepresented", None),
                    "GeoJSON": data.get("gjDownloadURL", None),
                })
            elif response.status_code == 404:
                missing.append((country, iso_code, adm))
            else:
                print(f"❌ No data for {country} ({iso_code}) at {adm} — Status {response.status_code}")
        
        except Exception as e:
            print(f"⚠️ Error fetching {country} ({adm}): {e}")
        
        # Small delay to be nice to the API
        time.sleep(0.2)

# Convert all records into a DataFrame
df = pd.DataFrame(records)
df.to_csv("geoBoundaries_metadata.csv", index=False)

print(f"\n✅ Done! Collected {len(df)} valid boundaries across {len(country_iso)} countries.")
