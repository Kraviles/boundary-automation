import os

# API Configuration
BASE_URL = 'https://www.geoboundaries.org/api/current/gbOpen'
ADM_LEVELS = ['ADM0', 'ADM1', 'ADM2', 'ADM3', 'ADM4']
GITHUB_ISSUES_API_URL = "https://api.github.com/repos/wmgeolab/geoBoundaries/issues"
GITHUB_PULL_REQUESTS_API_URL = "https://api.github.com/repos/wmgeolab/geoBoundaries/pulls"

# File Paths
# Data directory is relative to the project root
# BASE_DIR is relative to the config.py file itself, so it's '../..' from here
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')

ISO_CODES_PATH = os.path.join(DATA_DIR, 'iso_codes.csv')
METADATA_PATH = os.path.join(DATA_DIR, "geoBoundaries_metadata.csv")
MISSING_LAYERS_PATH = os.path.join(DATA_DIR, "missing_layers.csv")
MAP_HTML_PATH = os.path.join(os.path.dirname(__file__), 'map.html') # Relative to src/config.py for now, will adjust in interface.py if needed

# UI Strings
MAIN_WINDOW_TITLE = "Boundary Automation Dashboard"
TAB_DATA_COLLECTION = "Data Collection"
TAB_LICENSE_DETECTION = "License Detection"
TAB_PULL_REQUEST_VERIFICATION = "Pull Request Verification"

LABEL_COUNTRY = "Country:"
GROUP_MAIN_BOUNDARY = "Main Boundary"
LABEL_SOURCE = "Source:"
LABEL_ADM_LEVEL = "ADM Level:"
GROUP_COMPARISON_BOUNDARY = "Comparison Boundary"

BUTTON_RUN_ANALYSIS = "Run Full Analysis"
BUTTON_COMPARE_ON_MAP = "Compare on Map"
BUTTON_START_LICENSE_DETECTION = "Start License Detection"
BUTTON_FETCH_ISSUES = "Fetch Issues"

COMBOBOX_SELECT_COUNTRY_DEFAULT = "Select a Country"
COMBOBOX_SELECT_ADM_DEFAULT = "Select an ADM Level"
COMBOBOX_SELECT_ADM_DEFAULT = "Select ADM Level"

TABLE_HEADERS_LICENSE = ["Country", "ISO", "BoundaryType", "License"]
TABLE_HEADERS_ISSUES = ["Number", "Title", "State", "Labels"]

# Log Messages
LOG_START_ANALYSIS = "Starting full analysis..."
LOG_ANALYSIS_FINISHED = "Full analysis finished."
LOG_LOADED_BOUNDARIES = "Loaded {} boundaries."
LOG_MISSING_LAYERS = "Found {} missing layers."
LOG_SELECT_FULL_BOUNDARIES = "Please make a full selection for both main and comparison boundaries."
LOG_ERROR_MAIN_BOUNDARY_NOT_FOUND = "Error: Could not find a 'Main' boundary for Country='{}', Source='{}', ADM='{}'."
LOG_ERROR_COMP_BOUNDARY_NOT_FOUND = "Error: Could not find a 'Comparison' boundary for Country='{}', Source='{}', ADM='{}'."
LOG_FETCHING_MAIN = "Fetching Main: {}"
LOG_FETCHING_COMPARISON = "Fetching Comparison: {}"
LOG_ERROR_FETCHING_GEOJSON = "Error fetching GeoJSON: {}"
LOG_SENDING_GEOJSON_TO_MAP = "Sending GeoJSON data to map."
LOG_START_LICENSE_DETECTION = "Starting license detection..."
LOG_LICENSE_DETECTION_FINISHED = "License detection finished."
LOG_UNACCEPTABLE_LICENSES = "Found {} boundaries with unacceptable licenses."
LOG_FETCHING_GITHUB_ISSUES = "Fetching GitHub issues..."
LOG_GITHUB_ISSUES_FETCH_FINISHED = "GitHub issues fetch finished."
LOG_NO_ISSUES_FOUND = "No issues found or error fetching issues."


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
