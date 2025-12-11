# GeoGuardian

## Description

This project provides a tool to automate the process of fetching, analyzing, and managing geographical boundary data from the geoBoundaries API which directly accesses the [GeoBoundaries Github](https://github.com/wmgeolab/geoBoundaries/tree/main). It includes a Python backend for data processing and a desktop GUI for user interaction.

The primary goals of this project are to:
- Fetch administrative boundary data for all countries at various administrative levels (ADM0 to ADM4).
- Check the license of each boundary against a predefined list of acceptable licenses.
- Provide a user-friendly interface to run the analysis and view the results.
- Maintain a local cache of the boundary metadata to avoid unnecessary API calls.
- Ensure a robust and clear selection of boundary data sources within the Data Collection interface, separating display labels from unique source identifiers.

## Features

The application is structured into three main tabs, each serving a distinct purpose:

### Data Collection

This tab allows users to:
- Run a full analysis to fetch and cache administrative boundary data from the geoBoundaries API.
- Filter available and acceptable boundary data by country and administrative level (ADM0 to ADM4).
- Select and compare two different boundary sources for a given country and ADM level on an interactive map.

### License Detection

This tab allows users to:
- Perform a scan of all cached boundary data to identify entries with licenses that are not explicitly defined as acceptable.
- Display a table of all boundaries with unacceptable licenses, helping in compliance checks.

### Pull Request Verification

This tab is designed to assist with the verification process of new boundary data submitted via GitHub Pull Requests:
- Fetch and list open Pull Requests from the geoBoundaries GitHub repository.
- For a selected Pull Request, display critical information such as the contents of `meta.txt`, a preview of the `license.png` file, a visual preview of the boundary shapefile/GeoJSON, and details of any associated GitHub issues.


## Quick-Start Guide

This project is managed using [UV](https://docs.astral.sh/uv/). If you do not yet have UV installed or need help troubleshooting issues with UV, refer to their [documentation](https://docs.astral.sh/uv/getting-started/features/).

### Prerequisites

This project depends on the following Python libraries:
- pandas
- requests
- PySide6
- matplotlib
- pyshp

Once UV is installed, you can add these dependencies by running:
`uv sync`

### Running the Application

To run the application, execute the following command:

`uv run python main.py`

This will launch the Boundary Automation Dashboard.

*Note*: The first time running this application and running the full analysis of the geoBoundaries Github through clicking "Run Full Analysis" can take several minutes depending on network speed and API rate limits. This is normal as large number of API calls are being made and the metadata and CSVs are being written.

## Project Structure

`main.py`: The main entry point for the application. This script launches the GUI.

`src/interface.py`: Defines the PySide6 graphical user interface (GUI), including the data tables, control buttons, and tabbed layout.

`src/analysis.py`: Contains the core logic for fetching data from the geoBoundaries API, performing license checks, and fetching GitHub issues and pull requests.

`src/config.py`: Stores configuration data, including the list of acceptable licenses, API endpoints, and UI strings.

`src/map.html`, `src/leaflet.js`, `src/leaflet.css`: These files create the interactive map view used in the Data Collection tab, powered by the Leaflet.js library.

`data/`: This directory contains all the data files used by the application.
  - `geoBoundaries_metadata.csv`: A CSV file where the fetched boundary metadata is stored.
  - `missing_layers.csv`: A CSV file that logs any boundaries that could not be fetched.
  - `iso_codes.csv`: A utility file that maps country names to their corresponding ISO codes.
