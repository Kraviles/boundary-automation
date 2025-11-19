import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

BASE_URL = "https://www.geoboundaries.org/api/current/gbOpen"
ADM_LEVELS = ["ADM0", "ADM1", "ADM2", "ADM3", "ADM4"]

def build_country_iso_from_csv(iso_path):
    """
    Reads a CSV of countries and their ISO codes.
    Returns a dictionary mapping the country to its iso code
    """
    iso = pd.read_csv(iso_path)
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

    if response.status_code == 200:
        return response.json()

    if response.status_code == 404:
        return None

    # other errors
    response.raise_for_status()

    return response.json()

# Full analysis across all countries + ADM levels

def run_full_analysis(
    iso_path="Valid country names and ISO codes - Sheet1.csv",
    completed_path="geoBoundaries_metadata.csv",
    missing_path="missing_layers.csv",
    refresh_days=None,  # <-- you can change this
):
    """
    Collects metadata for all countries + ADM levels.
    Skips fetching if an existing file is newer than `refresh_days`.
    
    refresh_days:
        0 = always refresh
        7 = refresh weekly
        30 = refresh monthly
        None = never refresh unless file missing
    """

    # --- 1. Check if output file exists ---
    if os.path.exists(completed_path):
        file_date = datetime.fromtimestamp(os.path.getmtime(completed_path))
        age_days = (datetime.today() - file_date).days

        # refresh_days=None means: do not refresh unless file missing
        if refresh_days is None:
            print(f"📁 File exists and refresh disabled. Using cached file: {completed_path}")
            return pd.read_csv(completed_path), pd.read_csv(missing_path)

        # If the file is fresh enough
        if age_days <= refresh_days:
            print(f"📁 Existing file is {age_days} days old (limit = {refresh_days}).")
            print("➡️  Using cached file. No API calls made.")
            return pd.read_csv(completed_path), pd.read_csv(missing_path)

        else:
            print(f"📁 Cached file is {age_days} days old — refreshing…")

    else:
        print("📁 No cached file found. Building new dataset…")

    # If file does not exist or if need a refresh:
    country_iso = build_country_iso_from_csv(iso_path)
    records = []
    missing = []
    print("Starting the analysis on every country's adm level...")
    for country, iso, in country_iso.items():

        for adm_level in ADM_LEVELS:
            data = fetch_single_boundary(iso, adm_level)
            if data is None:
                missing.append((country, iso, adm_level))
                continue
            records.append({
                "Country": country,
                "ISO": iso,
                "BoundaryType": adm_level,
                "BoundaryName": data.get("boundaryName"),
                "License": data.get("boundaryLicense"),
                "License Source": data.get("licenseSource"),
                "Source": data.get("boundarySourceURL"),
                "Year": data.get("boundaryYearRepresented"),
                "GeoJSON": data.get("gjDownloadURL"),
            })
            time.sleep(0.2)

   # --- 3. Save results ---
    df = pd.DataFrame(records)
    print(f"\n✅ Done! Saved metadata for {len(df)} boundaries.")
    print(f"❗ Missing layers: {len(missing_layers)}")

    return df, missing


def check_license(completed_path):
    """
    Reads the completed CSV with each available 
    """
