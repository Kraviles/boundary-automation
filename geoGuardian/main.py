from analysis import build_country_iso_from_csv, fetch_single_boundary, run_full_analysis

CSV_PATH = 'Valid country names and ISO codes - Sheet1.csv'

records, missing = run_full_analysis(CSV_PATH)

df = pd.DataFrame(records)
df.to_csv("geoBoundaries_metadata.csv", index=False)


# Save missing layers
df_missing = pd.DataFrame(missing, columns=["Country", "ISO", "ADM"])
df_missing.to_csv("missing_layers.csv", index=False)

print("\n Done!")
print(f"   • {len(df)} valid boundaries collected")
print(f"   • {len(df_missing)} missing boundary layers")
