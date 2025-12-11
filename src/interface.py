import os
import sys
import re
import json
import pandas as pd
import requests
import zipfile
import io
import tempfile
from PySide6 import QtWidgets as qtw, QtGui
from PySide6 import QtWebEngineWidgets as qtwew
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6 import QtCore as qtc

from .analysis import run_full_analysis, check_license, fetch_github_issues, fetch_github_pull_requests, fetch_raw_github_content, fetch_single_pull_request, fetch_pull_request_files
from .config import (
    acceptable_licenses,
    ISO_CODES_PATH, METADATA_PATH, MISSING_LAYERS_PATH, MAP_HTML_PATH,
    MAIN_WINDOW_TITLE, TAB_DATA_COLLECTION, TAB_LICENSE_DETECTION, TAB_PULL_REQUEST_VERIFICATION,
    LABEL_COUNTRY, GROUP_MAIN_BOUNDARY, LABEL_SOURCE, LABEL_ADM_LEVEL,
    GROUP_COMPARISON_BOUNDARY, BUTTON_RUN_ANALYSIS, BUTTON_COMPARE_ON_MAP,
    BUTTON_START_LICENSE_DETECTION,
    COMBOBOX_SELECT_COUNTRY_DEFAULT, COMBOBOX_SELECT_ADM_DEFAULT, TABLE_HEADERS_LICENSE,
    LOG_START_ANALYSIS, LOG_ANALYSIS_FINISHED, LOG_LOADED_BOUNDARIES, LOG_MISSING_LAYERS,
    LOG_SELECT_FULL_BOUNDARIES, LOG_ERROR_MAIN_BOUNDARY_NOT_FOUND,
    LOG_ERROR_COMP_BOUNDARY_NOT_FOUND, LOG_FETCHING_MAIN, LOG_FETCHING_COMPARISON,
    LOG_ERROR_FETCHING_GEOJSON, LOG_SENDING_GEOJSON_TO_MAP, LOG_START_LICENSE_DETECTION,
    LOG_LICENSE_DETECTION_FINISHED, LOG_UNACCEPTABLE_LICENSES, LOG_FETCHING_GITHUB_ISSUES,
    LOG_GITHUB_ISSUES_FETCH_FINISHED, LOG_NO_ISSUES_FOUND
)

class WebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"JS Console: {message} ({sourceID}:{lineNumber})")

class Bridge(qtc.QObject):
    loadGeoJson = qtc.Signal(dict)

class AnalysisWorker(qtc.QThread):
    finished = qtc.Signal(pd.DataFrame, pd.DataFrame)

    def __init__(self, iso_path, completed_path, missing_path, refresh_days=None, parent=None):
        super().__init__(parent)
        self.iso_path = iso_path
        self.completed_path = completed_path
        self.missing_path = missing_path
        self.refresh_days = refresh_days

    def run(self):
        df, missing_df = run_full_analysis(self.iso_path, self.completed_path, self.missing_path, self.refresh_days)
        self.finished.emit(df, missing_df)

class LicenseWorker(qtc.QThread):
    finished = qtc.Signal(pd.DataFrame, pd.DataFrame)

    def __init__(self, completed_path, acceptable_licenses, parent=None):
        super().__init__(parent)
        self.completed_path = completed_path
        self.acceptable_licenses = acceptable_licenses

    def run(self):
        acceptable_df, unacceptable_df = check_license(self.completed_path, self.acceptable_licenses)
        self.finished.emit(acceptable_df, unacceptable_df)

class IssuesWorker(qtc.QThread):
    finished = qtc.Signal(pd.DataFrame)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        issues_df = fetch_github_issues()
        self.finished.emit(issues_df)

class PullRequestWorker(qtc.QThread):
    finished = qtc.Signal(pd.DataFrame)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        prs_df = fetch_github_pull_requests()
        self.finished.emit(prs_df)

class PRDataWorker(qtc.QThread):
    finished = qtc.Signal(dict)

    def __init__(self, pr_url, pr_number, pr_title, branch_name, parent=None):
        super().__init__(parent)
        self.pr_url = pr_url
        self.pr_number = pr_number
        self.pr_title = pr_title
        self.branch_name = branch_name

    def run(self):
        data = {
            'meta_txt': "Failed to load meta.txt",
            'license_png_bytes': None,
            'boundary_preview_bytes': None,
            'projection_info': "Projection not found",
            'issue_details': "No associated issue found.",
            'boundary_error': None,
            'attribute_df': None
        }
        try:
            if not self.pr_url:
                data['meta_txt'] = "Pull request URL missing."
                self.finished.emit(data)
                return

            pr_details = fetch_single_pull_request(self.pr_url)
            if not pr_details:
                self.finished.emit(data)
                return

            candidate_urls = []
            boundary_identifier = None

            # Prefer an explicit ZIP in the PR files
            if self.pr_number:
                files = fetch_pull_request_files(self.pr_number) or []
                for f in files:
                    fname = f.get('filename') or ''
                    if fname.lower().endswith('.zip'):
                        raw_url = f.get('raw_url') or f.get('contents_url') or f.get('blob_url')
                        if raw_url:
                            candidate_urls.append(raw_url)
                        boundary_identifier = os.path.splitext(os.path.basename(fname))[0]
                        break  # only need the first zip

            # 1. Identify the Target Boundary from the Pull Request (using provided pr_title/branch_name)
            if not boundary_identifier and self.branch_name:
                match = re.search(r'([A-Z]{3}_ADM[0-4])', self.branch_name)
                if match:
                    boundary_identifier = match.group(1)

            if not boundary_identifier and self.pr_title:
                match = re.search(r'([A-Z]{3}_ADM[0-4])', self.pr_title)
                if match:
                    boundary_identifier = match.group(1)

            if not boundary_identifier:
                data['meta_txt'] = "Could not identify boundary identifier from PR branch name or title."
                self.finished.emit(data)
                return

            # Extract ISO and ADM level for constructing the path
            iso_code = boundary_identifier[:3]
            adm_level = boundary_identifier[4:] # e.g., 'ADM0'

            # 2. Construct candidate URLs to the Zip File (flat layout)
            zip_file_name = f"{boundary_identifier}.zip"
            candidate_urls.append(
                f"https://raw.githubusercontent.com/wmgeolab/geoBoundaries/main/sourceData/gbOpen/{zip_file_name}"
            )
            candidate_urls.append(
                f"https://github.com/wmgeolab/geoBoundaries/raw/main/sourceData/gbOpen/{zip_file_name}"
            )
            
            # 3. Download the Zip File into Memory
            zip_content = None
            last_error = None
            for url in candidate_urls:
                try:
                    response = requests.get(url, timeout=30) # Increased timeout for zip download
                    response.raise_for_status()
                    content = response.content
                    # Ensure we actually received a zip file
                    if not content.startswith(b"PK"):
                        last_error = f"URL returned non-zip content ({response.headers.get('Content-Type')})"
                        continue
                    zip_content = io.BytesIO(content)
                    break
                except requests.RequestException as e:
                    last_error = e
                    continue
            if not zip_content:
                data['meta_txt'] = f"Error downloading zip file. Last error: {last_error}"
                self.finished.emit(data)
                return

            # 4. Extract Files from the In-Memory Zip
            try:
                with zipfile.ZipFile(zip_content, 'r') as zf, tempfile.TemporaryDirectory() as tmpdir:
                    # Extract meta.txt
                    try:
                        meta_txt_content = None
                        meta_txt_candidates = [f"{boundary_identifier}_meta.txt", "meta.txt"] # Primary, then fallback
                        
                        for candidate in meta_txt_candidates:
                            if candidate in zf.namelist():
                                meta_txt_content = zf.read(candidate).decode('utf-8')
                                break
                        
                        if meta_txt_content:
                            data['meta_txt'] = meta_txt_content
                            projection_info = "Projection not found in meta.txt"
                            for line in meta_txt_content.splitlines():
                                if line.lower().startswith("projection:"):
                                    projection_info = line.split(":", 1)[1].strip()
                                    break
                            data['projection_info'] = projection_info
                        else:
                            data['meta_txt'] = "meta.txt not found in zip."
                    except KeyError:
                        data['meta_txt'] = "meta.txt not found in zip."

                    # Extract license.png
                    try:
                        license_png_content = None
                        license_png_candidates = [f"{boundary_identifier}_license.png", "license.png"] # Primary, then fallback
                        
                        for candidate in license_png_candidates:
                            if candidate in zf.namelist():
                                license_png_content = zf.read(candidate)
                                break
                        
                        data['license_png_bytes'] = license_png_content
                    except KeyError:
                        data['license_png_bytes'] = None

                    # Extract entire archive to temp dir for boundary preview
                    zf.extractall(tmpdir)
                    shapefile_path = None
                    geojson_path = None
                    for root, _, files in os.walk(tmpdir):
                        for fname in files:
                            lower = fname.lower()
                            full_path = os.path.join(root, fname)
                            if lower.endswith(".shp"):
                                shapefile_path = full_path
                            elif lower.endswith(".geojson") or lower.endswith(".json"):
                                geojson_path = full_path
                    preview_source = shapefile_path or geojson_path
                    if preview_source:
                        try:
                            # Prefer geopandas if available
                            try:
                                import matplotlib
                                matplotlib.use("Agg")
                                import matplotlib.pyplot as plt
                                import geopandas as gpd
                                gdf = gpd.read_file(preview_source)
                                
                                # Generate preview
                                fig, ax = plt.subplots(figsize=(6, 5))
                                gdf.plot(ax=ax, linewidth=0.5, edgecolor="black", facecolor="#9ecae1")
                                ax.axis('off')
                                buf = io.BytesIO()
                                fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.05)
                                plt.close(fig)
                                buf.seek(0)
                                data['boundary_preview_bytes'] = buf.read()
                                
                                # Extract attribute table
                                data['attribute_df'] = pd.DataFrame(gdf.drop(columns='geometry'))

                            except ImportError:
                                # Fallback: minimal rendering with pyshp or raw geojson
                                import matplotlib
                                matplotlib.use("Agg")
                                import matplotlib.pyplot as plt
                                fig, ax = plt.subplots(figsize=(6, 5))
                                rendered = False
                                if shapefile_path:
                                    try:
                                        import shapefile as pyshp
                                        reader = pyshp.Reader(shapefile_path)
                                        for shape in reader.shapes():
                                            pts = shape.points
                                            parts = list(shape.parts) + [len(pts)]
                                            for i in range(len(parts) - 1):
                                                seg = pts[parts[i]:parts[i+1]]
                                                if seg:
                                                    xs, ys = zip(*seg)
                                                    ax.plot(xs, ys, color="black", linewidth=0.5)
                                        rendered = True
                                        
                                        # Extract attribute table from shapefile
                                        fields = [field[0] for field in reader.fields[1:]]
                                        records = [record[:] for record in reader.iterRecords()]
                                        data['attribute_df'] = pd.DataFrame(records, columns=fields)

                                    except Exception as e:
                                        data['boundary_error'] = f"Shapefile preview failed: {e}"
                                if geojson_path and not rendered:
                                    try:
                                        with open(geojson_path, "r", encoding="utf-8") as f:
                                            gj = json.load(f)
                                        
                                        # Extract attribute table from GeoJSON
                                        features = gj.get("features", [])
                                        if features:
                                            properties = [feature.get("properties", {}) for feature in features]
                                            data['attribute_df'] = pd.DataFrame(properties)

                                        def plot_coords(coords):
                                            for poly in coords:
                                                for ring in poly:
                                                    xs, ys = zip(*ring)
                                                    ax.plot(xs, ys, color="black", linewidth=0.5)
                                        if gj.get("type") == "FeatureCollection":
                                            for feat in features:
                                                geom = feat.get("geometry") or {}
                                                coords = geom.get("coordinates") or []
                                                if geom.get("type") == "Polygon":
                                                    plot_coords([coords])
                                                elif geom.get("type") == "MultiPolygon":
                                                    plot_coords(coords)
                                        rendered = True
                                    except Exception as e:
                                        data['boundary_error'] = f"GeoJSON preview failed: {e}"
                                if rendered:
                                    ax.axis('off')
                                    buf = io.BytesIO()
                                    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.05)
                                    plt.close(fig)
                                    buf.seek(0)
                                    data['boundary_preview_bytes'] = buf.read()
                                else:
                                    plt.close(fig)
                        except Exception as e:
                            data['boundary_error'] = f"Preview generation failed: {e}"

            except zipfile.BadZipFile:
                data['meta_txt'] = "Downloaded file is not a valid zip archive."
                self.finished.emit(data)
                return
            except Exception as e:
                data['meta_txt'] = f"Error extracting from zip file: {e}"
                self.finished.emit(data)
                return

            # Fetch associated issue
            issue_details = "No associated issue found."
            # Primary: explicit closes #NNN in PR body
            if pr_details.get('body'):
                match = re.search(r'closes #(\d+)', pr_details['body'], re.IGNORECASE)
                if match:
                    issue_number = match.group(1)
                    issue_url = f"https://api.github.com/repos/wmgeolab/geoBoundaries/issues/{issue_number}"
                    issue_data = fetch_single_pull_request(issue_url) # Reusing this function as it just fetches a URL
                    if issue_data:
                        issue_details = f"Title: {issue_data.get('title')}\n\n{issue_data.get('body')}"
            # Secondary: heuristic match on issue title using boundary_identifier
            if issue_details == "No associated issue found." and boundary_identifier:
                issues_df = fetch_github_issues()
                if not issues_df.empty:
                    try:
                        # Look for first issue title containing the boundary identifier
                        match_issue = issues_df[issues_df['title'].str.contains(boundary_identifier, case=False, na=False)]
                        if not match_issue.empty:
                            issue_number = match_issue.iloc[0].get('number')
                            issue_url = f"https://api.github.com/repos/wmgeolab/geoBoundaries/issues/{issue_number}"
                            issue_data = fetch_single_pull_request(issue_url)
                            if issue_data:
                                issue_details = f"Title: {issue_data.get('title')}\n\n{issue_data.get('body')}"
                    except Exception as e:
                        issue_details = f"No associated issue found. ({e})"
            data['issue_details'] = issue_details

            self.finished.emit(data)
        except Exception as e:
            data['meta_txt'] = f"Unexpected error: {e}"
            self.finished.emit(data)


class GeoJsonWorker(qtc.QThread):
    finished = qtc.Signal(dict)

    def __init__(self, main_url, comp_url, parent=None):
        super().__init__(parent)
        self.main_url = main_url
        self.comp_url = comp_url

    def run(self):
        result = {'error': None, 'geojson': {}}
        try:
            main_resp = requests.get(self.main_url, timeout=10)
            main_resp.raise_for_status()
            result['geojson']['main'] = main_resp.text
        except requests.RequestException as e:
            result['error'] = f"Error fetching main GeoJSON: {e}"
            self.finished.emit(result)
            return

        try:
            comp_resp = requests.get(self.comp_url, timeout=10)
            comp_resp.raise_for_status()
            result['geojson']['comparison'] = comp_resp.text
        except requests.RequestException as e:
            result['error'] = f"Error fetching comparison GeoJSON: {e}"

        self.finished.emit(result)


class DataCollectionTab(qtw.QWidget):
    def __init__(self, parent=None, iso_path=None, completed_path=None, missing_path=None):
        super().__init__(parent)
        self.df = pd.DataFrame() # DataFrame to hold analysis results
        self.iso_path = iso_path
        self.completed_path = completed_path
        self.missing_path = missing_path
        self.init_ui()

    def init_ui(self):
        main_layout = qtw.QVBoxLayout(self)

        # Layout of Top Controls
        controls_layout = qtw.QGridLayout()

        # Country Filter
        controls_layout.addWidget(qtw.QLabel(LABEL_COUNTRY), 0, 0)
        self.country_filter = qtw.QComboBox()
        controls_layout.addWidget(self.country_filter, 0, 1, 1, 3) # Span across columns

        # Main Boundary Group
        main_group = qtw.QGroupBox(GROUP_MAIN_BOUNDARY)
        main_group_layout = qtw.QVBoxLayout()
        self.main_adm_filter = qtw.QComboBox()
        main_group_layout.addWidget(qtw.QLabel(LABEL_ADM_LEVEL))
        main_group_layout.addWidget(self.main_adm_filter)
        self.main_source_filter = qtw.QComboBox()
        main_group_layout.addWidget(qtw.QLabel(LABEL_SOURCE))
        main_group_layout.addWidget(self.main_source_filter)
        main_group.setLayout(main_group_layout)
        controls_layout.addWidget(main_group, 1, 0, 1, 2)

        # Comparison Boundary Group
        comp_group = qtw.QGroupBox(GROUP_COMPARISON_BOUNDARY)
        comp_group_layout = qtw.QVBoxLayout()
        self.comp_adm_filter = qtw.QComboBox()
        comp_group_layout.addWidget(qtw.QLabel(LABEL_ADM_LEVEL))
        comp_group_layout.addWidget(self.comp_adm_filter)
        self.comp_source_filter = qtw.QComboBox()
        comp_group_layout.addWidget(qtw.QLabel(LABEL_SOURCE))
        comp_group_layout.addWidget(self.comp_source_filter)
        comp_group.setLayout(comp_group_layout)
        controls_layout.addWidget(comp_group, 1, 2, 1, 2)

        main_layout.addLayout(controls_layout)

        # --- Action Buttons ---
        action_layout = qtw.QHBoxLayout()
        self.run_analysis_button = qtw.QPushButton(BUTTON_RUN_ANALYSIS)
        self.compare_button = qtw.QPushButton(BUTTON_COMPARE_ON_MAP)
        action_layout.addWidget(self.run_analysis_button)
        action_layout.addWidget(self.compare_button)
        main_layout.addLayout(action_layout)

        # --- Map View ---
        self.map_view = qtwew.QWebEngineView()
        self.setup_web_channel()
        self.map_view.setUrl(qtc.QUrl.fromLocalFile(os.path.abspath(MAP_HTML_PATH)))
        main_layout.addWidget(self.map_view)

        # Log Text
        self.log_text = qtw.QTextEdit()
        self.log_text.setReadOnly(True)
        main_layout.addWidget(self.log_text)

        # Connections
        self.run_analysis_button.clicked.connect(self.run_analysis)
        self.country_filter.currentTextChanged.connect(self.update_filters_for_country)
        self.main_adm_filter.currentTextChanged.connect(self.update_sources_for_adm)
        self.comp_adm_filter.currentTextChanged.connect(lambda text: self.update_sources_for_adm(text, is_comparison=True))
        self.compare_button.clicked.connect(self.compare_on_map)

    def setup_web_channel(self):
        self.page = WebEnginePage(self)
        self.map_view.setPage(self.page)

        self.channel = QWebChannel()
        self.bridge = Bridge()
        self.channel.registerObject("bridge", self.bridge)
        self.page.setWebChannel(self.channel)

    def run_analysis(self):
        self.log_text.append(LOG_START_ANALYSIS)
        self.run_analysis_button.setEnabled(False)
        self._analysis_worker = AnalysisWorker(self.iso_path, self.completed_path, self.missing_path, parent=self)
        self._analysis_worker.finished.connect(self.update_data_table)
        self._analysis_worker.finished.connect(self._analysis_worker.deleteLater)
        self._analysis_worker.start()

    def update_data_table(self, df, missing_df):
        self.log_text.append(LOG_ANALYSIS_FINISHED)
        self.run_analysis_button.setEnabled(True)
        
        self.df = df
        # Normalize missing_df columns for ADM filtering
        self.missing_df = missing_df.copy() if missing_df is not None else pd.DataFrame(columns=['Country', 'ISO', 'ADM_Level'])
        if not self.missing_df.empty:
            self.missing_df.columns = self.missing_df.columns.str.strip()
            if 'ADM_Level' not in self.missing_df.columns:
                # Try to recover from common variants
                for alt in ['ADM Level', 'adm_level', 'Adm_Level', 'ADM']:
                    if alt in self.missing_df.columns:
                        self.missing_df = self.missing_df.rename(columns={alt: 'ADM_Level'})
                        break
            if 'ADM_Level' not in self.missing_df.columns:
                # If still missing, drop to empty to avoid KeyError
                self.missing_df = pd.DataFrame(columns=['Country', 'ISO', 'ADM_Level'])
        # Normalize BoundaryType to avoid whitespace/case mismatches
        if 'BoundaryType' in self.df.columns:
            self.df['BoundaryType'] = self.df['BoundaryType'].astype(str).str.strip().str.upper()
        # Create a display source column for filtering based on year and license, keeping original Source intact
        self.df[['Year', 'License', 'BoundaryName']] = self.df[['Year', 'License', 'BoundaryName']].fillna('unknown')
        self.df['DisplaySource'] = self.df['Year'].astype(str) + " - " + self.df['License'] + " (" + self.df['BoundaryName'] + ")"
        self.populate_country_filter()

    def populate_country_filter(self):
        self.country_filter.blockSignals(True)
        self.country_filter.clear()
        self.country_filter.addItem(COMBOBOX_SELECT_COUNTRY_DEFAULT)
        countries = sorted(self.df['Country'].unique())
        self.country_filter.addItems(countries)
        self.country_filter.blockSignals(False)

    def update_filters_for_country(self):
        selected_country = self.country_filter.currentText()
        
        # Clear all dropdowns
        for combo in [self.main_source_filter, self.main_adm_filter, self.comp_source_filter, self.comp_adm_filter]:
            combo.blockSignals(True)
            combo.clear()
            combo.blockSignals(False)

        if selected_country != COMBOBOX_SELECT_COUNTRY_DEFAULT:
            country_df = self.df[self.df['Country'] == selected_country]
            adms = sorted(country_df['BoundaryType'].unique())
            if hasattr(self, "missing_df") and not self.missing_df.empty:
                try:
                    missing_adms = set(self.missing_df[self.missing_df['Country'] == selected_country]['ADM_Level'])
                except KeyError:
                    missing_adms = set()
                adms = [adm for adm in adms if adm not in missing_adms]
            
            # Add placeholder
            adms.insert(0, COMBOBOX_SELECT_ADM_DEFAULT)

            for combo in [self.main_adm_filter, self.comp_adm_filter]:
                combo.blockSignals(True)
                combo.addItems(adms)
                # Set index to 0 (which is the placeholder)
                if combo.count() > 0:
                    combo.setCurrentIndex(0)
                combo.blockSignals(False)

        # The source filters will be updated when the user makes a selection from the ADM dropdowns.

    def update_sources_for_adm(self, _text=None, is_comparison=False):
        adm_filter = self.comp_adm_filter if is_comparison else self.main_adm_filter
        source_filter = self.comp_source_filter if is_comparison else self.main_source_filter

        source_filter.blockSignals(True)
        source_filter.clear()
        source_filter.blockSignals(False)

        selected_country = self.country_filter.currentText()
        selected_adm = adm_filter.currentText()

        # Guard against placeholder selection
        if selected_adm == COMBOBOX_SELECT_ADM_DEFAULT:
            return

        if selected_country != COMBOBOX_SELECT_COUNTRY_DEFAULT and selected_adm:
            sub_df = self.df[(self.df['Country'] == selected_country) & (self.df['BoundaryType'] == selected_adm)]
            source_filter.blockSignals(True)
            source_filter.clear()
            source_filter.addItem("Select Source", userData=None)
            # Use a tuple of (display_label, real_source_url) to sort and add items
            sources = sorted(sub_df[['DisplaySource', 'Source']].drop_duplicates().itertuples(index=False, name=None))
            for display_label, real_source in sources:
                source_filter.addItem(display_label, userData=real_source)
            source_filter.blockSignals(False)

    def compare_on_map(self):
        country = self.country_filter.currentText()
        main_source_url = self.main_source_filter.currentData()
        main_adm = self.main_adm_filter.currentText()
        comp_source_url = self.comp_source_filter.currentData()
        comp_adm = self.comp_adm_filter.currentText()

        if country == COMBOBOX_SELECT_COUNTRY_DEFAULT or not all([main_source_url, main_adm, comp_source_url, comp_adm]):
            self.log_text.append(LOG_SELECT_FULL_BOUNDARIES)
            return

        # Find the rows in the dataframe using the real source URL from userData
        main_row = self.df[(self.df['Country'] == country) & (self.df['Source'] == main_source_url) & (self.df['BoundaryType'] == main_adm)]
        comp_row = self.df[(self.df['Country'] == country) & (self.df['Source'] == comp_source_url) & (self.df['BoundaryType'] == comp_adm)]

        if main_row.empty:
            # Use currentText() for the user-facing log message
            main_source_text = self.main_source_filter.currentText()
            self.log_text.append(LOG_ERROR_MAIN_BOUNDARY_NOT_FOUND.format(country, main_source_text, main_adm))
            return
        
        if comp_row.empty:
            # Use currentText() for the user-facing log message
            comp_source_text = self.comp_source_filter.currentText()
            self.log_text.append(LOG_ERROR_COMP_BOUNDARY_NOT_FOUND.format(country, comp_source_text, comp_adm))
            return

        main_url = main_row.iloc[0]['GeoJSON']
        comp_url = comp_row.iloc[0]['GeoJSON']

        self.log_text.append(LOG_FETCHING_MAIN.format(main_url))
        self.log_text.append(LOG_FETCHING_COMPARISON.format(comp_url))
        self.compare_button.setEnabled(False)
        self._geojson_worker = GeoJsonWorker(main_url, comp_url)
        self._geojson_worker.setParent(self)
        self._geojson_worker.finished.connect(self.handle_geojson_result)
        self._geojson_worker.finished.connect(self._geojson_worker.deleteLater)
        self._geojson_worker.start()

    def handle_geojson_result(self, result):
        self.compare_button.setEnabled(True)
        error = result.get('error')
        if error:
            self.log_text.append(LOG_ERROR_FETCHING_GEOJSON.format(error))
        else:
            geojson_data = result.get('geojson', {})
            self.log_text.append(LOG_SENDING_GEOJSON_TO_MAP)
            self.bridge.loadGeoJson.emit(geojson_data)
        self._geojson_worker = None


class LicenseDetectionTab(qtw.QWidget):
    def __init__(self, parent=None, completed_path=None):
        super().__init__(parent)
        self.completed_path = completed_path
        self.init_ui()

    def init_ui(self):
        layout = qtw.QVBoxLayout(self)

        # Create a splitter to hold the two tables
        splitter = qtw.QSplitter(qtc.Qt.Horizontal)

        # Unacceptable licenses table
        unacceptable_group = qtw.QGroupBox("Unacceptable Licenses")
        unacceptable_layout = qtw.QVBoxLayout()
        self.unacceptable_license_table = qtw.QTableWidget()
        self.unacceptable_license_table.setColumnCount(len(TABLE_HEADERS_LICENSE))
        self.unacceptable_license_table.setHorizontalHeaderLabels(TABLE_HEADERS_LICENSE)
        unacceptable_layout.addWidget(self.unacceptable_license_table)
        unacceptable_group.setLayout(unacceptable_layout)
        splitter.addWidget(unacceptable_group)

        # Acceptable licenses table
        acceptable_group = qtw.QGroupBox("Acceptable Licenses")
        acceptable_layout = qtw.QVBoxLayout()
        self.acceptable_license_table = qtw.QTableWidget()
        self.acceptable_license_table.setColumnCount(len(TABLE_HEADERS_LICENSE))
        self.acceptable_license_table.setHorizontalHeaderLabels(TABLE_HEADERS_LICENSE)
        acceptable_layout.addWidget(self.acceptable_license_table)
        acceptable_group.setLayout(acceptable_layout)
        splitter.addWidget(acceptable_group)

        layout.addWidget(splitter)

        self.start_button = qtw.QPushButton(BUTTON_START_LICENSE_DETECTION)
        self.start_button.clicked.connect(self.run_license_check)
        layout.addWidget(self.start_button)

        self.log_text = qtw.QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

    def run_license_check(self):
        self.log_text.append(LOG_START_LICENSE_DETECTION)
        self.start_button.setEnabled(False)
        self._license_worker = LicenseWorker(self.completed_path, acceptable_licenses, parent=self)
        self._license_worker.finished.connect(self.update_license_tables)
        self._license_worker.finished.connect(self._license_worker.deleteLater)
        self._license_worker.start()

    def update_license_tables(self, acceptable_df, unacceptable_df):
        self.log_text.append(LOG_LICENSE_DETECTION_FINISHED)
        self.start_button.setEnabled(True)

        self.populate_table(self.unacceptable_license_table, unacceptable_df)
        self.populate_table(self.acceptable_license_table, acceptable_df)

        self.log_text.append(LOG_UNACCEPTABLE_LICENSES.format(len(unacceptable_df)))
        self.log_text.append(f"Found {len(acceptable_df)} boundaries with acceptable licenses.")

    def populate_table(self, table, df):
        table.setRowCount(len(df))
        for i, (_, row) in enumerate(df.iterrows()):
            table.setItem(i, 0, qtw.QTableWidgetItem(row["Country"]))
            table.setItem(i, 1, qtw.QTableWidgetItem(row["ISO"]))
            table.setItem(i, 2, qtw.QTableWidgetItem(row["BoundaryType"]))
            table.setItem(i, 3, qtw.QTableWidgetItem(row["License"]))


class PullRequestVerificationTab(qtw.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = qtw.QVBoxLayout(self)

        # PR Selector
        pr_selector_layout = qtw.QHBoxLayout()
        pr_selector_layout.addWidget(qtw.QLabel("Select Pull Request:"))
        self.pr_selector = qtw.QComboBox()
        pr_selector_layout.addWidget(self.pr_selector)
        self.fetch_prs_button = qtw.QPushButton("Fetch PRs")
        pr_selector_layout.addWidget(self.fetch_prs_button)
        layout.addLayout(pr_selector_layout)

        # Main content splitter (vertical)
        main_splitter = qtw.QSplitter(qtc.Qt.Vertical)

        # Top section for metadata and previews
        top_splitter = qtw.QSplitter(qtc.Qt.Horizontal)

        # Left side: meta.txt and issue details
        left_widget = qtw.QWidget()
        left_layout = qtw.QVBoxLayout(left_widget)
        self.meta_text = qtw.QTextEdit()
        self.meta_text.setReadOnly(True)
        self.meta_text.setPlaceholderText("meta.txt content will be displayed here.")
        left_layout.addWidget(qtw.QLabel("meta.txt"))
        left_layout.addWidget(self.meta_text)

        self.issue_details_text = qtw.QTextEdit()
        self.issue_details_text.setReadOnly(True)
        self.issue_details_text.setPlaceholderText("Associated issue details will be displayed here.")
        left_layout.addWidget(qtw.QLabel("Issue Details"))
        left_layout.addWidget(self.issue_details_text)
        top_splitter.addWidget(left_widget)

        # Right side: license image and boundary preview (in a splitter)
        right_splitter = qtw.QSplitter(qtc.Qt.Vertical)

        license_group = qtw.QGroupBox("license.png")
        license_layout = qtw.QVBoxLayout(license_group)
        self.license_image_label = qtw.QLabel("license.png will be displayed here.")
        self.license_image_label.setFrameShape(qtw.QFrame.StyledPanel)
        self.license_image_label.setAlignment(qtc.Qt.AlignCenter)
        license_layout.addWidget(self.license_image_label)
        right_splitter.addWidget(license_group)

        boundary_group = qtw.QGroupBox("Boundary Preview")
        boundary_layout = qtw.QVBoxLayout(boundary_group)
        self.boundary_image_label = qtw.QLabel("Boundary preview will be displayed here.")
        self.boundary_image_label.setFrameShape(qtw.QFrame.StyledPanel)
        self.boundary_image_label.setAlignment(qtc.Qt.AlignCenter)
        boundary_layout.addWidget(self.boundary_image_label)
        right_splitter.addWidget(boundary_group)
        
        top_splitter.addWidget(right_splitter)
        top_splitter.setSizes([self.width() // 3, 2 * self.width() // 3]) # Give more space to previews
        main_splitter.addWidget(top_splitter)


        # Bottom section for attribute table
        attribute_group = qtw.QGroupBox("Attribute Table")
        attribute_layout = qtw.QVBoxLayout(attribute_group)
        self.attribute_table = qtw.QTableWidget()
        attribute_layout.addWidget(self.attribute_table)
        main_splitter.addWidget(attribute_group)

        main_splitter.setSizes([2 * self.height() // 3, self.height() // 3]) # Give more space to top section
        layout.addWidget(main_splitter)

        # Connections
        self.fetch_prs_button.clicked.connect(self.fetch_pull_requests)
        self.pr_selector.currentIndexChanged.connect(self.on_pr_selected)

    def fetch_pull_requests(self):
        self.fetch_prs_button.setEnabled(False)
        self._pull_request_worker = PullRequestWorker(self)
        self._pull_request_worker.finished.connect(self.update_pr_selector)
        self._pull_request_worker.finished.connect(self._pull_request_worker.deleteLater)
        self._pull_request_worker.start()

    def update_pr_selector(self, prs_df):
        self.fetch_prs_button.setEnabled(True)
        self.pr_selector.clear()
        if not prs_df.empty:
            for _, row in prs_df.iterrows():
                head = row.get('head') or {}
                branch_ref = head.get('ref') if isinstance(head, dict) else None
                self.pr_selector.addItem(
                    f"#{row.get('number')} - {row.get('title')}",
                    userData={
                        'url': row.get('url'),
                        'number': row.get('number'),
                        'title': row.get('title'),
                        'branch': branch_ref
                    }
                )
        else:
            self.pr_selector.addItem("No open pull requests found (check rate limit or set GITHUB_TOKEN).")
        if self.pr_selector.count() > 0:
            self.on_pr_selected()
        self._pull_request_worker = None

    def on_pr_selected(self):
        pr_data = self.pr_selector.currentData()
        if pr_data:
            self._pr_data_worker = PRDataWorker(pr_data['url'], pr_data['number'], pr_data['title'], pr_data['branch'])
            self._pr_data_worker.setParent(self)
            self._pr_data_worker.finished.connect(self.update_pr_data)
            self._pr_data_worker.finished.connect(self._pr_data_worker.deleteLater)
            self._pr_data_worker.start()
            
    def update_pr_data(self, data):
        self.meta_text.setText(data.get('meta_txt', 'Failed to load meta.txt'))
        
        license_png_bytes = data.get('license_png_bytes')
        if license_png_bytes:
            pixmap = QtGui.QPixmap()
            if pixmap.loadFromData(license_png_bytes):
                self.license_image_label.setPixmap(pixmap.scaled(
                    self.license_image_label.width(),
                    self.license_image_label.height(),
                    qtc.Qt.KeepAspectRatio, 
                    qtc.Qt.SmoothTransformation
                ))
            else:
                self.license_image_label.setText("Failed to decode license.png")
        else:
            self.license_image_label.setText("Failed to load license.png")

        boundary_bytes = data.get('boundary_preview_bytes')
        if boundary_bytes:
            bpx = QtGui.QPixmap()
            if bpx.loadFromData(boundary_bytes):
                self.boundary_image_label.setPixmap(bpx.scaled(
                    self.boundary_image_label.width(),
                    self.boundary_image_label.height(),
                    qtc.Qt.KeepAspectRatio,
                    qtc.Qt.SmoothTransformation
                ))
            else:
                self.boundary_image_label.setText("Failed to decode boundary preview")
        else:
            err = data.get('boundary_error')
            if err:
                self.boundary_image_label.setText(f"Boundary preview unavailable: {err}")
            else:
                self.boundary_image_label.setText("Boundary preview unavailable")
            
        self.issue_details_text.setText(data.get('issue_details', ''))
        
        # Populate attribute table
        attribute_df = data.get('attribute_df')
        self.populate_attribute_table(attribute_df)

        self._pr_data_worker = None

    def populate_attribute_table(self, df):
        self.attribute_table.clear()
        if df is None or df.empty:
            self.attribute_table.setRowCount(0)
            self.attribute_table.setColumnCount(0)
            return

        self.attribute_table.setRowCount(df.shape[0])
        self.attribute_table.setColumnCount(df.shape[1])
        self.attribute_table.setHorizontalHeaderLabels(df.columns)

        for row_idx, row in enumerate(df.itertuples(index=False)):
            for col_idx, value in enumerate(row):
                item = qtw.QTableWidgetItem(str(value))
                self.attribute_table.setItem(row_idx, col_idx, item)
        self.attribute_table.resizeColumnsToContents()


class MainWindow(qtw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(MAIN_WINDOW_TITLE)
        self.init_ui()

    def init_ui(self):
        self.tab_widget = qtw.QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # Create tab widgets
        self.data_collection_tab = DataCollectionTab(
            parent=self,
            iso_path=ISO_CODES_PATH,
            completed_path=METADATA_PATH,
            missing_path=MISSING_LAYERS_PATH
        )
        self.license_detection_tab = LicenseDetectionTab(
            parent=self,
            completed_path=METADATA_PATH
        )
        self.pr_verification_tab = PullRequestVerificationTab(parent=self)

        # Add tabs to the tab widget
        self.tab_widget.addTab(self.data_collection_tab, TAB_DATA_COLLECTION)
        self.tab_widget.addTab(self.license_detection_tab, TAB_LICENSE_DETECTION)
        self.tab_widget.addTab(self.pr_verification_tab, TAB_PULL_REQUEST_VERIFICATION)


if __name__ == "__main__":
    app = qtw.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())
