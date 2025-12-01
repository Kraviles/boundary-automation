# Boundary Automation

## Description

This project provides a tool to automate the process of fetching, analyzing, and managing geographical boundary data from the [geoBoundaries](https://www.geoboundaries.org/) API. It includes a Python backend for data processing and a desktop GUI for user interaction.

The primary goals of this project are to:
- Fetch administrative boundary data for all countries at various administrative levels (ADM0 to ADM4).
- Check the license of each boundary against a predefined list of acceptable licenses.
- Provide a user-friendly interface to run the analysis and view the results.
- Maintain a local cache of the boundary metadata to avoid unnecessary API calls.

## Quick-Start Guide

This project is managed using [UV](https://docs.astral.sh/uv/). If you do not yet have UV installed or need help troubleshooting issues with UV, refer to their [documentation](https://docs.astral.sh/uv/getting-started/features/).

### Prerequisites

This project depends on the following Python libraries:
- pandas
- requests
- PySide6

Once UV is installed, you can add these dependencies by running:
`uv add pandas requests PySide6`
`uv sync`

### Running the Application

To run the application, execute the following command:

`uv run python main.py`

This will launch the Boundary Automation Dashboard.

## Project Structure

`main.py`: The main entry point for the application. This script launches the GUI.

`src/interface.py`: Defines the PySide6 graphical user interface (GUI), including the data tables and control buttons.

`src/analysis.py`: Contains the core logic for fetching data from the geoBoundaries API, performing license checks, and fetching GitHub issues.

`src/config.py`: Stores configuration data, including the list of acceptable licenses.

`data/`: This directory contains all the data files used by the application.
  - `geoBoundaries_metadata.csv`: A CSV file where the fetched boundary metadata is stored.
  - `missing_layers.csv`: A CSV file that logs any boundaries that could not be fetched.
  - `Valid country names and ISO codes - Sheet1.csv`: A utility file that maps country names to their corresponding ISO codes.
