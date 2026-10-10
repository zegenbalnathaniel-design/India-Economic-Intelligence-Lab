"""One-off ingestion script: converts the uploaded source files into clean,
documented CSVs under data/raw/. Run once; output is committed to the repo
so re-running isn't required to reproduce what's there, but this script
documents exactly how each file was produced from its source.
"""
import pandas as pd

UP = "/root/.claude/uploads/420dd34c-740e-55fe-965d-98a59052f9e0"

# --- RBI Handbook of Statistics on Indian States, Table 26: per-capita NSDP, constant prices ---
xl_path = f"{UP}/d9558008-26T_15112023E153E32B394446B08A0318979840F668.XLSX"
frames = []
sheet_meta = {
    "T_26(i)":   ("2004-05", range(2004, 2009)),
    "T_26(ii)":  ("2004-05", range(2009, 2015)),
    "T_26(iii)": ("2011-12", range(2011, 2017)),
    "T_26(iv)":  ("2011-12", range(2017, 2023)),
}
for sheet, (base, _) in sheet_meta.items():
    raw = pd.read_excel(xl_path, sheet_name=sheet, header=None)
    years_row = raw.iloc[5, 2:].tolist()
    years = [str(y) for y in years_row if pd.notna(y)]
    data = raw.iloc[6:, 1:2 + len(years)]
    data.columns = ["state"] + years
    data = data.dropna(subset=["state"])
    data = data.melt(id_vars="state", var_name="financial_year", value_name="percapita_nsdp_constant_prices_inr")
    data["base_year"] = base
    data["source_sheet"] = sheet
    data["percapita_nsdp_constant_prices_inr"] = pd.to_numeric(
        data["percapita_nsdp_constant_prices_inr"].replace("-", pd.NA), errors="coerce"
    )
    frames.append(data)
nsdp_long = pd.concat(frames, ignore_index=True)
nsdp_long = nsdp_long[["state", "financial_year", "base_year", "percapita_nsdp_constant_prices_inr", "source_sheet"]]
nsdp_long.to_csv("data/raw/rbi_handbook/percapita_nsdp_constant_prices_2004_05_to_2022_23.csv", index=False)
print("NSDP long:", nsdp_long.shape, "states:", nsdp_long['state'].nunique(), "years:", sorted(nsdp_long['financial_year'].unique()))

# --- NHB RESIDEX: city composite index, 2013-2024 ---
idx_old = pd.read_html(f"{UP}/17cd722c-Residex_Data_1.xls")[0].drop_duplicates()
idx_old = idx_old.melt(id_vars="City", var_name="quarter_raw", value_name="composite_index")
idx_old["quarter_raw"] = idx_old["quarter_raw"].str.replace("--", "-").str.replace(" ", "")
idx_old.to_csv("data/raw/nhb_residex/city_composite_index_2013_2024.csv", index=False)
print("RESIDEX index 2013-2024:", idx_old.shape, "cities:", idx_old['City'].nunique())

# --- NHB RESIDEX: city composite index, latest 5 quarters (2025-2026) ---
idx_new = pd.read_html(f"{UP}/db066c2d-Residex_Data.xls")[0].drop_duplicates()
idx_new = idx_new.melt(id_vars="City", var_name="quarter_raw", value_name="composite_index")
idx_new["quarter_raw"] = idx_new["quarter_raw"].str.replace("- ", "-").str.strip()
idx_new.to_csv("data/raw/nhb_residex/city_composite_index_2025_2026.csv", index=False)
print("RESIDEX index 2025-2026:", idx_new.shape, "cities:", idx_new['City'].nunique())

# --- NHB RESIDEX: actual price levels by city/quarter/unit-size tier ---
prices = pd.read_html(f"{UP}/01440ee5-Residex_Data_2.xls")[0].drop_duplicates()
prices.columns = ["city", "quarter", "composite_price_inr_per_sqft", "price_le_60sqm_inr_per_sqft",
                   "price_60_110sqm_inr_per_sqft", "price_gt_110sqm_inr_per_sqft"]
prices.to_csv("data/raw/nhb_residex/city_price_levels_by_unit_size_2013_2024.csv", index=False)
print("RESIDEX price levels:", prices.shape, "cities:", prices['city'].nunique())

print("\nDone.")
