import os
import pandas as pd
import requests
from requests.exceptions import RequestException
import PySide6.QtWidgets as qtw
import zipfile
import shapefile
import geopandas as gpd
import matplotlib.pyplot as plt

GITHUB_RAW = "https://raw.githubusercontent.com"

def fetch_pull_requests():
    """
    Fetches pull requests
    """
    url = "https://api.github.com/repos/wmgeolab/geoBoundaries/pulls"
    all_prs = []
    page = 1
    per_page = 100  # max allowed

    while True:
        response = requests.get(url, params={"per_page": per_page, "page": page}, timeout=10)
        response.raise_for_status()
        prs = response.json()
        if not prs:
            break
        all_prs.extend(prs)
        page += 1

    print(f"✅ Fetched {len(all_prs)} pull requests in total")
    return all_prs

def fetch_github_issues():
    '''
    Fetches open issues from the geoBoundaries GitHub repository.
    '''
    url = "https://api.github.com/repos/wmgeolab/geoBoundaries/issues"
    all_issues = []
    page = 1 
    per_page = 100
    while True:
        response = requests.get(url, params={"per_page": per_page, "page": page}, timeout=10)
        response.raise_for_status()
        items = response.json()
        if not items:
            break
        issues_only = [item for item in items if "pull_request" not in item]

        all_issues.extend(issues_only)
        page +=1
        
    return pd.DataFrame(all_issues)

def find_keyword(pr):
    """
    Grabs the ISO_ADMcode that is present in all pull requests,
    """
    title = pr.get("title", "")
    return title.split()[0] if title else None

def find_matching_issue(issues, keyword):
    """
    Finds the issue that corresponds to the pull request
    """
    for idx, row in issues.iterrows():
        title = row['title']
        if keyword.lower() in str(title).lower():
            return row['title'], int(row['number'])  # return the matching row's number
    
    return None, None


def summarize_pr(prs):
    """
    Creates a summary dict of a PR, including:
    - metadata
    - boundary file links (if any)
    - downloadable URLs
    """

    summary = {
        "number": prs.get("number"),
        "title": prs.get("title"),
        "author": prs.get("user", {}).get("login"),
        "state": prs.get("state"),
        "created_at": prs.get("created_at"),
        "updated_at": prs.get("updated_at"),
        "labels": [label["name"] for label in prs.get("labels", [])],
        "full_text": prs.get("body", "(no description)"),
        "boundary_filenames": [],
        "boundary_download_urls": [],
        "issue_title": None,
        "associated_issue_number": None
    }
    keyword = (find_keyword(prs))
    issue_title, issue_num = find_matching_issue(issues, keyword)
    summary["issue_title"] = issue_title
    summary["associated_issue_number"] = issue_num
    
    # Method of grabbing the link!
    files_url = prs.get("url") + "/files"

    try:
        resp = requests.get(files_url)
        resp.raise_for_status()
        pr_files = resp.json()

        for f in pr_files:
            filename = f.get("filename")
            raw_url = f.get("raw_url")

            if filename:
                summary["boundary_filenames"].append(filename)

            if raw_url:
                summary["boundary_download_urls"].append(raw_url)

    except Exception as e:
        summary["boundary_filenames"].append(None)
        summary["boundary_download_urls"].append(f"ERROR: {e}")

    return summary

def fetch_issue_by_number(issue_number):
    """
    Fetches a single issue by its number from repo.
    Returns a dict with title and body (description), or None if not found.
    """
    url = f"https://api.github.com/repos/wmgeolab/geoBoundaries/issues/{issue_number}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        issue = response.json()
        return {
            "number": issue.get("number"),
            "title": issue.get("title"),
            "body": issue.get("body")
        }
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None

# Visualization of Boundaries

def process_boundary_file(filename, url, title=None):
    """
    Downloads a single zipped boundary file from GitHub,
    extracts it, detects whether it contains a .shp or .geojson,
    loads it into GeoPandas, and plots it.
    """
    
    if title is None:
        title = filename  # fallback

    print(f"⬇️ Downloading {filename} ...")
    zip_path = filename + ".zip"

    # Download (stream=True prevents loading entire file into memory)
    response = requests.get(url, stream=True)
    response.raise_for_status()

    # Save zip file locally
    with open(zip_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"📦 Saved ZIP as {zip_path}")

    # Unzip destination folder
    extract_to = f"unzipped_{filename}"
    os.makedirs(extract_to, exist_ok=True)

    # Extract ZIP
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

    print(f"✅ Extracted to: {os.path.abspath(extract_to)}")

    # Detect .shp or .geojson
    shp_file = None
    geojson_file = None

    for root, dirs, files in os.walk(extract_to):
        for f in files:
            if f.lower().endswith(".shp"):
                shp_file = os.path.join(root, f)
            elif f.lower().endswith(".geojson") or f.lower().endswith(".json"):
                geojson_file = os.path.join(root, f)

    # Decide which file to load
    if shp_file:
        print(f"🗂 Found shapefile: {shp_file}")
        gdf = gpd.read_file(shp_file)
    elif geojson_file:
        print(f"🗂 Found GeoJSON: {geojson_file}")
        gdf = gpd.read_file(geojson_file)
    else:
        raise FileNotFoundError("❌ No .shp or .geojson found in extracted files.")

    # Show preview of dataset
    print("\n📍 GeoDataFrame preview:")
    print(gdf.head())

    # Plot with title
    gdf.plot()
    plt.title(f"Boundary Preview: {title}")
    plt.show()

    return gdf

def preview_boundary_from_url(download_url, title=None, save_as=None):
    """
    Downloads a ZIP file from a PR summary and previews it using preview_boundary_zip().
    Only downloads ONE file, avoiding rate limit issues.
    """

    if save_as is None:
        save_as = download_url.split('/')[-1]  # default to filename from URL

    print(f"⬇️ Downloading boundary file:\n   {download_url}")

    response = requests.get(download_url, stream=True)

    if response.status_code != 200:
        print(f"❌ Failed to download. Status code: {response.status_code}")
        return None

    # Write ZIP to disk
    with open(save_as, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    print(f"   ✅ Saved as: {save_as}")

    # Now preview it
    return process_boundary_file(save_as.replace(".zip", ""), download_url, title=title)