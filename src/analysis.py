import os
import time
from datetime import datetime
import requests
import pandas as pd

from .config import BASE_URL, ADM_LEVELS, GITHUB_ISSUES_API_URL, GITHUB_PULL_REQUESTS_API_URL


class GeoBoundariesAPI:
    """A class to interact with the geoBoundaries API."""
    def __init__(self):
        self.base_url = BASE_URL

    def _fetch_single_boundary(self, iso, adm_level):
        """
        Fetches a single ISO + ADM layer from the geoBoundaries API.
        Raises an exception for network errors or if the boundary is not found.
        """
        url = f"{self.base_url}/{iso}/{adm_level}/"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Boundary not found is a common case, so we handle it specifically.
                return None
            # Re-raise other HTTP errors
            raise e
        except requests.exceptions.RequestException as e:
            # Handle other network-related errors (e.g., connection timeout)
            raise RuntimeError(f"Error fetching boundary for {iso}/{adm_level}: {e}") from e

    def get_all_boundaries_metadata(self, iso_path):
        """
        Collects metadata for all countries and ADM levels from the API.
        """
        country_iso_map = build_country_iso_from_csv(iso_path)
        records = []
        missing = []

        print("Starting analysis on all country administrative levels...")
        for country, iso in country_iso_map.items():
            for adm_level in ADM_LEVELS:
                data = self._fetch_single_boundary(iso, adm_level)
                if data is None:
                    missing.append((country, iso, adm_level))
                    continue
                records.append({
                    'Country': country,
                    'ISO': iso,
                    'BoundaryType': adm_level,
                    'BoundaryName': data.get('boundaryName'),
                    'License': data.get('boundaryLicense'),
                    'License Source': data.get('licenseSource'),
                    'Source': data.get('boundarySourceURL'),
                    'Year': data.get('boundaryYearRepresented'),
                    'GeoJSON': data.get('gjDownloadURL'),
                })
                # Add a delay to be respectful to the API
                time.sleep(0.2)
        
        df = pd.DataFrame(records)
        missing_df = pd.DataFrame(missing, columns=['Country', 'ISO', 'ADM_Level'])
        
        print(f"\nDone! Saved metadata for {len(df)} boundaries.")
        print(f"Missing layers: {len(missing_df)}")
        
        return df, missing_df


def build_country_iso_from_csv(iso_path):
    """
    Reads a CSV of countries and their ISO codes.
    Returns a dictionary mapping the country to its ISO code.
    """
    try:
        iso_df = pd.read_csv(iso_path)
        iso_df.columns = iso_df.columns.str.strip()  # Clean the column names
        return dict(zip(iso_df['Country or Area'], iso_df['ISO-alpha3 code']))
    except FileNotFoundError:
        raise RuntimeError(f"ISO country codes file not found at: {iso_path}")


def run_full_analysis(iso_path, completed_path, missing_path, refresh_days=None):
    """
    Collects metadata for all countries + ADM levels.
    Skips fetching if an existing file is newer than `refresh_days`.
    
    refresh_days:
        0 = always refresh
        7 = refresh weekly
        30 = refresh monthly
        None = never refresh unless file missing
    """
    if os.path.exists(completed_path):
        file_date = datetime.fromtimestamp(os.path.getmtime(completed_path))
        age_days = (datetime.now() - file_date).days

        if refresh_days is None:
            print(f'File exists and refresh disabled. Using cached file: {completed_path}')
            return pd.read_csv(completed_path), pd.read_csv(missing_path)

        if age_days <= refresh_days:
            print(f'Existing file is {age_days} days old (limit = {refresh_days}).')
            print('➡️  Using cached file. No API calls made.')
            return pd.read_csv(completed_path), pd.read_csv(missing_path)
        else:
            print(f'Cached file is {age_days} days old — refreshing…')
    else:
        print('No cached file found. Building new dataset…')

    api = GeoBoundariesAPI()
    df, missing_df = api.get_all_boundaries_metadata(iso_path)

    # Save results
    df.to_csv(completed_path, index=False)
    missing_df.to_csv(missing_path, index=False)
    
    return df, missing_df


def check_license(completed_path, acceptable_licenses):
    """
    Reads the completed CSV and checks for unacceptable licenses.
    """
    if not os.path.exists(completed_path):
        print(f'File not found: {completed_path}')
        return pd.DataFrame(), pd.DataFrame()

    df = pd.read_csv(completed_path)
    
    # Filter for rows where the license is in the acceptable list
    acceptable_df = df[df['License'].isin(acceptable_licenses)]
    
    # Filter for rows where the license is not in the acceptable list
    unacceptable_df = df[~df['License'].isin(acceptable_licenses)]
    
    return acceptable_df, unacceptable_df


def fetch_github_issues():
    """
    Fetches open issues from the geoBoundaries GitHub repository.
    """
    try:
        response = requests.get(GITHUB_ISSUES_API_URL)
        response.raise_for_status()
        issues = response.json()
        return pd.DataFrame(issues)
    except requests.RequestException as e:
        print(f"Error fetching GitHub issues: {e}")
        return pd.DataFrame()

def fetch_github_pull_requests():
    """
    Fetches open pull requests from the geoBoundaries GitHub repository.
    """
    all_prs = []
    page = 1
    per_page = 100
    headers = {}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    try:
        while True:
            response = requests.get(
                GITHUB_PULL_REQUESTS_API_URL,
                params={"page": page, "per_page": per_page},
                timeout=10,
                headers=headers
            )
            response.raise_for_status()
            batch = response.json()
            if not batch:
                break
            all_prs.extend(batch)
            page += 1
        return pd.DataFrame(all_prs)
    except requests.RequestException as e:
        print(f"Error fetching GitHub pull requests: {e}")
        return pd.DataFrame()

def fetch_raw_github_content(url):
    """
    Fetches raw content from a GitHub URL.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching raw content from {url}: {e}")
        return None

def fetch_single_pull_request(url):
    """
    Fetches details for a single pull request from its API URL.
    """
    headers = {}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    try:
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching pull request from {url}: {e}")
        return None

def fetch_pull_request_files(pr_number):
    """
    Fetches the list of files for a given pull request number.
    """
    url = f"https://api.github.com/repos/wmgeolab/geoBoundaries/pulls/{pr_number}/files"
    headers = {}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    try:
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching files for PR #{pr_number}: {e}")
        return []
