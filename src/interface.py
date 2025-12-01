import os
import sys
import pandas as pd
import requests
from PySide6 import QtWidgets as qtw
from PySide6 import QtWebEngineWidgets as qtwew
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6 import QtCore as qtc

from .analysis import run_full_analysis, check_license, fetch_github_issues
from .config import acceptable_licenses

class WebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"JS Console: {message} ({sourceID}:{lineNumber})")

class Bridge(qtc.QObject):
    loadGeoJson = qtc.Signal(dict)

class AnalysisWorker(qtc.QThread):
    finished = qtc.Signal(pd.DataFrame, pd.DataFrame)

    def __init__(self, iso_path, completed_path, missing_path, refresh_days):
        super().__init__()
        self.iso_path = iso_path
        self.completed_path = completed_path
        self.missing_path = missing_path
        self.refresh_days = refresh_days

    def run(self):
        df, missing_df = run_full_analysis(self.iso_path, self.completed_path, self.missing_path, self.refresh_days)
        self.finished.emit(df, missing_df)

class LicenseWorker(qtc.QThread):
    finished = qtc.Signal(pd.DataFrame)

    def __init__(self, completed_path, acceptable_licenses):
        super().__init__()
        self.completed_path = completed_path
        self.acceptable_licenses = acceptable_licenses

    def run(self):
        unacceptable_df = check_license(self.completed_path, self.acceptable_licenses)
        self.finished.emit(unacceptable_df)

class IssuesWorker(qtc.QThread):
    finished = qtc.Signal(pd.DataFrame)

    def run(self):
        issues_df = fetch_github_issues()
        self.finished.emit(issues_df)

class MainWindow(qtw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Boundary Automation Dashboard")
        self.df = pd.DataFrame()

        # Define paths
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.iso_path = os.path.join(self.data_dir, 'Valid country names and ISO codes - Sheet1.csv')
        self.completed_path = os.path.join(self.data_dir, "geoBoundaries_metadata.csv")
        self.missing_path = os.path.join(self.data_dir, "missing_layers.csv")

        self.init_ui()

    def init_ui(self):
        self.tab_widget = qtw.QTabWidget()
        self.setCentralWidget(self.tab_widget)

        self.data_collection_tab = qtw.QWidget()
        self.license_detection_tab = qtw.QWidget()
        self.issues_tab = qtw.QWidget()

        self.tab_widget.addTab(self.data_collection_tab, "Data Collection")
        self.tab_widget.addTab(self.license_detection_tab, "License Detection")
        self.tab_widget.addTab(self.issues_tab, "GitHub Issues")

        self.setup_data_collection_tab()
        self.setup_license_detection_tab()
        self.setup_issues_tab()

    def setup_data_collection_tab(self):
        # Main layout for the tab
        main_layout = qtw.QVBoxLayout()
        self.data_collection_tab.setLayout(main_layout)

        # --- Top Controls Layout ---
        controls_layout = qtw.QGridLayout()

        # Country Filter
        controls_layout.addWidget(qtw.QLabel("Country:"), 0, 0)
        self.country_filter = qtw.QComboBox()
        controls_layout.addWidget(self.country_filter, 0, 1, 1, 3) # Span across columns

        # Main Boundary Group
        main_group = qtw.QGroupBox("Main Boundary")
        main_group_layout = qtw.QVBoxLayout()
        self.main_source_filter = qtw.QComboBox()
        self.main_adm_filter = qtw.QComboBox()
        main_group_layout.addWidget(qtw.QLabel("Source:"))
        main_group_layout.addWidget(self.main_source_filter)
        main_group_layout.addWidget(qtw.QLabel("ADM Level:"))
        main_group_layout.addWidget(self.main_adm_filter)
        main_group.setLayout(main_group_layout)
        controls_layout.addWidget(main_group, 1, 0, 1, 2)

        # Comparison Boundary Group
        comp_group = qtw.QGroupBox("Comparison Boundary")
        comp_group_layout = qtw.QVBoxLayout()
        self.comp_source_filter = qtw.QComboBox()
        self.comp_adm_filter = qtw.QComboBox()
        comp_group_layout.addWidget(qtw.QLabel("Source:"))
        comp_group_layout.addWidget(self.comp_source_filter)
        comp_group_layout.addWidget(qtw.QLabel("ADM Level:"))
        comp_group_layout.addWidget(self.comp_adm_filter)
        comp_group.setLayout(comp_group_layout)
        controls_layout.addWidget(comp_group, 1, 2, 1, 2)

        main_layout.addLayout(controls_layout)

        # --- Action Buttons ---
        action_layout = qtw.QHBoxLayout()
        self.run_analysis_button = qtw.QPushButton("Run Full Analysis")
        self.compare_button = qtw.QPushButton("Compare on Map")
        action_layout.addWidget(self.run_analysis_button)
        action_layout.addWidget(self.compare_button)
        main_layout.addLayout(action_layout)

        # --- Map View ---
        self.map_view = qtwew.QWebEngineView()
        self.setup_web_channel()
        map_path = os.path.join(os.path.dirname(__file__), 'map.html')
        self.map_view.setUrl(qtc.QUrl.fromLocalFile(os.path.abspath(map_path)))
        main_layout.addWidget(self.map_view)

        # --- Connections ---
        self.run_analysis_button.clicked.connect(self.run_analysis)
        self.country_filter.currentTextChanged.connect(self.update_filters_for_country)
        self.main_source_filter.currentTextChanged.connect(self.update_main_adm_filter)
        self.comp_source_filter.currentTextChanged.connect(self.update_comp_adm_filter)
        self.compare_button.clicked.connect(self.compare_on_map)


    def setup_web_channel(self):
        self.page = WebEnginePage(self)
        self.map_view.setPage(self.page)

        self.channel = QWebChannel()
        self.bridge = Bridge()
        self.channel.registerObject("bridge", self.bridge)
        self.page.setWebChannel(self.channel)

    def setup_license_detection_tab(self):
        layout = qtw.QVBoxLayout()
        self.license_detection_tab.setLayout(layout)

        self.license_table = qtw.QTableWidget()
        self.license_table.setColumnCount(4)
        self.license_table.setHorizontalHeaderLabels(["Country", "ISO", "BoundaryType", "License"])
        layout.addWidget(self.license_table)

        self.start_button = qtw.QPushButton("Start License Detection")
        self.start_button.clicked.connect(self.run_license_check)
        layout.addWidget(self.start_button)

        self.log_text = qtw.QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

    def setup_issues_tab(self):
        layout = qtw.QVBoxLayout()
        self.issues_tab.setLayout(layout)

        self.issues_table = qtw.QTableWidget()
        self.issues_table.setColumnCount(4)
        self.issues_table.setHorizontalHeaderLabels(["Number", "Title", "State", "Labels"])
        layout.addWidget(self.issues_table)

        self.fetch_issues_button = qtw.QPushButton("Fetch Issues")
        self.fetch_issues_button.clicked.connect(self.run_issues_fetch)
        layout.addWidget(self.fetch_issues_button)

        self.issues_log_text = qtw.QTextEdit()
        self.issues_log_text.setReadOnly(True)
        layout.addWidget(self.issues_log_text)

    def run_analysis(self):
        self.log_text.append("Starting full analysis...")
        self.run_analysis_button.setEnabled(False)
        self.worker = AnalysisWorker(self.iso_path, self.completed_path, self.missing_path, refresh_days=None)
        self.worker.finished.connect(self.update_data_table)
        self.worker.start()

    def update_data_table(self, df, missing_df):
        self.log_text.append("Full analysis finished.")
        self.run_analysis_button.setEnabled(True)
        
        self.df = df
        # Create a source column for filtering based on year and license
        self.df['Source'] = self.df['Year'].astype(str) + " - " + self.df['License'].astype(str)
        self.populate_country_filter()

        self.log_text.append(f"Loaded {len(df)} boundaries.")
        if not missing_df.empty:
            self.log_text.append(f"Found {len(missing_df)} missing layers.")

    def populate_country_filter(self):
        self.country_filter.blockSignals(True)
        self.country_filter.clear()
        self.country_filter.addItem("Select a Country")
        countries = sorted(self.df['Country'].unique())
        self.country_filter.addItems(countries)
        self.country_filter.blockSignals(False)

    def update_filters_for_country(self):
        selected_country = self.country_filter.currentText()
        
        # Clear all subsequent dropdowns
        for combo in [self.main_source_filter, self.main_adm_filter, self.comp_source_filter, self.comp_adm_filter]:
            combo.clear()

        if selected_country != "Select a Country":
            country_df = self.df[self.df['Country'] == selected_country]
            sources = sorted(country_df['Source'].unique())
            
            for combo in [self.main_source_filter, self.comp_source_filter]:
                combo.blockSignals(True)
                combo.addItems(sources)
                combo.blockSignals(False)
            
            self.update_main_adm_filter()
            self.update_comp_adm_filter()
    
    def update_main_adm_filter(self):
        self.main_adm_filter.clear()
        selected_country = self.country_filter.currentText()
        selected_source = self.main_source_filter.currentText()

        if selected_country != "Select a Country" and selected_source:
            adm_df = self.df[(self.df['Country'] == selected_country) & (self.df['Source'] == selected_source)]
            adms = sorted(adm_df['BoundaryType'].unique())
            self.main_adm_filter.addItems(adms)

    def update_comp_adm_filter(self):
        self.comp_adm_filter.clear()
        selected_country = self.country_filter.currentText()
        selected_source = self.comp_source_filter.currentText()

        if selected_country != "Select a Country" and selected_source:
            adm_df = self.df[(self.df['Country'] == selected_country) & (self.df['Source'] == selected_source)]
            adms = sorted(adm_df['BoundaryType'].unique())
            self.comp_adm_filter.addItems(adms)

    def compare_on_map(self):
        country = self.country_filter.currentText()
        main_source = self.main_source_filter.currentText()
        main_adm = self.main_adm_filter.currentText()
        comp_source = self.comp_source_filter.currentText()
        comp_adm = self.comp_adm_filter.currentText()

        if country == "Select a Country" or not all([main_source, main_adm, comp_source, comp_adm]):
            self.log_text.append("Please make a full selection for both main and comparison boundaries.")
            return

        # Find the rows in the dataframe
        main_row = self.df[(self.df['Country'] == country) & (self.df['Source'] == main_source) & (self.df['BoundaryType'] == main_adm)]
        comp_row = self.df[(self.df['Country'] == country) & (self.df['Source'] == comp_source) & (self.df['BoundaryType'] == comp_adm)]

        if main_row.empty:
            self.log_text.append(f"Error: Could not find a 'Main' boundary for Country='{country}', Source='{main_source}', ADM='{main_adm}'.")
            return
        
        if comp_row.empty:
            self.log_text.append(f"Error: Could not find a 'Comparison' boundary for Country='{country}', Source='{comp_source}', ADM='{comp_adm}'.")
            return

        main_url = main_row.iloc[0]['GeoJSON']
        comp_url = comp_row.iloc[0]['GeoJSON']

        geojson_data = {}
        try:
            self.log_text.append(f"Fetching Main: {main_url}")
            main_resp = requests.get(main_url, timeout=10)
            main_resp.raise_for_status()
            geojson_data['main'] = main_resp.text
            
            self.log_text.append(f"Fetching Comparison: {comp_url}")
            comp_resp = requests.get(comp_url, timeout=10)
            comp_resp.raise_for_status()
            geojson_data['comparison'] = comp_resp.text

        except requests.RequestException as e:
            self.log_text.append(f"Error fetching GeoJSON: {e}")
            return
            
        self.log_text.append("Sending GeoJSON data to map.")
        self.bridge.loadGeoJson.emit(geojson_data)


    def run_license_check(self):
        self.log_text.append("Starting license detection...")
        self.start_button.setEnabled(False)
        self.license_worker = LicenseWorker(self.completed_path, acceptable_licenses)
        self.license_worker.finished.connect(self.update_license_table)
        self.license_worker.start()

    def update_license_table(self, unacceptable_df):
        self.log_text.append("License detection finished.")
        self.start_button.setEnabled(True)

        self.license_table.setRowCount(len(unacceptable_df))
        for i, (_, row) in enumerate(unacceptable_df.iterrows()):
            self.license_table.setItem(i, 0, qtw.QTableWidgetItem(row["Country"]))
            self.license_table.setItem(i, 1, qtw.QTableWidgetItem(row["ISO"]))
            self.license_table.setItem(i, 2, qtw.QTableWidgetItem(row["BoundaryType"]))
            self.license_table.setItem(i, 3, qtw.QTableWidgetItem(row["License"]))
        self.log_text.append(f"Found {len(unacceptable_df)} boundaries with unacceptable licenses.")

    def run_issues_fetch(self):
        self.issues_log_text.append("Fetching GitHub issues...")
        self.fetch_issues_button.setEnabled(False)
        self.issues_worker = IssuesWorker()
        self.issues_worker.finished.connect(self.update_issues_table)
        self.issues_worker.start()

    def update_issues_table(self, issues_df):
        self.issues_log_text.append("GitHub issues fetch finished.")
        self.fetch_issues_button.setEnabled(True)

        if issues_df.empty:
            self.issues_log_text.append("No issues found or error fetching issues.")
            return

        self.issues_table.setRowCount(len(issues_df))
        for i, row in issues_df.iterrows():
            self.issues_table.setItem(i, 0, qtw.QTableWidgetItem(str(row["number"])))
            self.issues_table.setItem(i, 1, qtw.QTableWidgetItem(row["title"]))
            self.issues_table.setItem(i, 2, qtw.QTableWidgetItem(row["state"]))
            labels = ", ".join([label["name"] for label in row["labels"]])
            self.issues_table.setItem(i, 3, qtw.QTableWidgetItem(labels))
        self.issues_log_text.append(f"Found {len(issues_df)} issues.")

if __name__ == "__main__":
    app = qtw.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())
