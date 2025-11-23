import pandas as pd

from analysis import build_country_iso_from_csv, fetch_iso, fetch_adm, fetch_single_boundary, run_full_analysis

ISO_PATH = 'Valid country names and ISO codes - Sheet1.csv'
completed_path="geoBoundaries_metadata.csv"
missing_path="missing_layers.csv"

# example of finding an iso code for a country
print(fetch_iso(ISO_PATH, "United states of america"))

# example of geting the adm level in the right format
print(fetch_adm("ADM1"))

# example of findng a country's boundary
print(fetch_single_boundary("USA", 6, ISO_PATH))

df,missing = run_full_analysis(ISO_PATH, completed_path, missing_path, refresh_days=None)

df.to_csv("geoBoundaries_metadata.csv", index=False)


# Save missing layers
df_missing = pd.DataFrame(missing, columns=["Country", "ISO", "ADM"])
df_missing.to_csv("missing_layers.csv", index=False)

print("\n Done!")
print(f"   • {len(df)} valid boundaries collected")
print(f"   • {len(df_missing)} missing boundary layers")

print(df.head())
print(df.columns)

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
