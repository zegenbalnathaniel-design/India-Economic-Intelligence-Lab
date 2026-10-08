import pandas as pd
import numpy as np

years = ["2024-25","2023-24","2022-23","2021-22","2020-21","2019-20","2018-19","2017-18","2016-17","2015-16","2014-15","2013-14","2012-13","2011-12"]

nsdp_current = {
"Andhra Pradesh": [266240,237951,219917,193703,168063,160341,154031,138299,120676,108002,93903,82870,74687,69000],
"Arunachal Pradesh": [None,220209,199543,190851,181537,182171,155103,138836,124129,116985,114789,94135,82626,73540],
"Assam": [154222,139783,119192,103371,86947,90123,81034,75151,66330,60817,52895,49734,44599,41142],
"Bihar": [None,60180,53401,47296,42128,44175,40715,36850,34045,30404,28671,26948,24487,21750],
"Chhattisgarh": [162870,148922,134996,123493,106117,106611,102024,88793,83285,72991,72936,69880,60849,55177],
"Goa": [None,585953,532854,459094,423047,435949,423716,411740,378953,334576,289185,215776,234354,259444],
"Gujarat": [None,297722,272451,241584,207324,212428,197457,176961,156295,139254,127017,113139,102826,87481],
"Haryana": [353182,319363,289213,265163,225137,232530,223022,208437,184982,164963,147382,137770,121269,106085],
"Himachal Pradesh": [257212,234782,214489,193392,173565,186559,174804,165497,150290,135512,123299,114095,99730,87721],
"Jammu & Kashmir": [154703,139880,126301,112898,101645,101868,98738,87710,78960,74950,62327,61907,57279,51775],
"Jharkhand": [None,105274,96449,88500,69963,75016,75421,67484,60018,52754,57301,50006,47360,41254],
"Karnataka": [380906,339813,310325,268963,221683,222141,205245,185840,169898,148108,130024,118829,102319,90263],
"Kerala": [None,279751,252338,230280,194432,208879,205437,183252,166246,148133,135537,123388,110314,97912],
"Madhya Pradesh": [152615,139713,127947,117402,101958,101909,92337,81966,74324,62080,55678,51849,44773,38497],
"Maharashtra": [309340,278681,252289,219620,182454,189843,182865,172663,163726,146815,132836,125261,112092,99597],
"Manipur": [None,128925,111730,98826,75784,78574,73795,71507,59345,55447,52717,47798,41230,39762],
"Meghalaya": [149891,136948,123896,107971,90751,95422,88954,82457,77585,71594,66485,66281,64477,59794],
"Mizoram": [None,235823,215227,190965,173521,195365,164708,155222,127107,114055,103049,77584,65013,57654],
"Nagaland": [None,158730,140673,127225,119781,122759,109198,102003,91347,82466,78367,71510,61225,53010],
"Odisha": [182548,165068,143059,133768,103211,104633,98005,87055,77507,64835,63345,60687,54762,48387],
"Punjab": [209452,195031,182645,170276,150620,154385,149974,139835,128780,118858,108970,103831,94318,85577],
"Rajasthan": [185053,166647,150020,134143,114925,115534,106604,98698,91924,83426,76429,69480,63658,57192],
"Sikkim": [None,587743,520466,466518,415045,412627,375773,349163,280729,245987,214148,194624,174183,158667],
"Tamil Nadu": [358027,315220,277802,242339,209628,206165,194373,175276,156595,142028,129494,116960,105340,93112],
"Telangana": [379751,346457,314066,269000,225734,231326,209848,179358,159395,140840,124104,112162,101007,91121],
"Tripura": [None,176943,154256,137032,118401,121456,113016,100444,91596,84267,69857,61815,52574,47155],
"Uttar Pradesh": [None,93422,83057,74055,61598,65660,62350,57944,52671,47118,42267,40124,35812,32002],
"Uttarakhand": [274064,246178,219850,194670,174526,190558,186207,180858,161752,147936,136099,126356,113654,100314],
"West Bengal": [163467,149515,137909,122883,105108,110316,103920,91401,82291,75992,68876,65932,58195,51543],
"Andaman & Nicobar Islands": [None,275758,258142,229570,205368,219653,204254,178709,153904,137064,126344,111087,98777,89100],
"Chandigarh": [None,430119,393384,337406,290417,330703,307812,280512,252236,230009,212594,203356,180457,158967],
}
# Delhi and Puducherry: only 13 values legible in the screenshot (one column, likely 2024-25
# for Delhi / 2011-12 for Puducherry, unclear which), flagged rather than guessed.
delhi_vals_13 = [459408,417217,370824,322311,355798,338730,318323,295558,270261,247209,227900,205568,185001]
puducherry_vals_13 = [285072,267124,245759,231557,208862,217937,204140,187356,172727,146921,148147,130548,119649]

rows = []
for state, vals in nsdp_current.items():
    for y, v in zip(years, vals):
        rows.append({"state": state, "financial_year": y, "percapita_nsdp_current_prices_inr": v})
df = pd.DataFrame(rows)
df["transcription_flag"] = ""
df.loc[df["state"]=="Bihar", "transcription_flag"] = "CHECK: 2024-25 blank in screenshot, but a previously-ingested file (state_gsdp_nsdp_percapita.csv) shows a non-blank nsdp_pc_current_2024_25 value for Bihar (69321) and a different 2023-24 value (62201 vs 60180 transcribed here) -- genuine conflict between two sources, not resolved automatically."
df.to_csv("nsdp_current_prices_by_state_2011_12_to_2024_25.csv", index=False)
print("NSDP current-price table:", df.shape)

# Delhi / Puducherry as separate flagged file (ambiguous column alignment)
amb = []
for i, v in enumerate(delhi_vals_13):
    amb.append({"state": "Delhi", "position_from_left": i, "value": v})
for i, v in enumerate(puducherry_vals_13):
    amb.append({"state": "Puducherry", "position_from_left": i, "value": v})
pd.DataFrame(amb).to_csv("nsdp_current_prices_delhi_puducherry_UNALIGNED.csv", index=False)
print("Delhi/Puducherry ambiguous rows written separately, NOT merged into main table")

# --- Gross capital formation by institutional sector, current prices, INR crore ---
gcf_years = ["2023-24","2022-23","2021-22","2020-21","2019-20","2018-19","2017-18","2016-17","2015-16","2014-15","2013-14","2012-13","2011-12"]
gcf = {
    "public_nonfinancial_corp": [1168040,794613,644839,557144,657702,688580,534552,511230,530695,432124,384168,365778,343340],
    "private_nonfinancial_corp": [3308275,3260798,2635259,1946235,2167136,2164264,1895150,1763895,1800493,1611294,1424681,1328882,1123768],
    "public_financial_corp": [18998,14787,11270,13485,11742,14131,13699,11652,12362,11678,13489,9857,8428],
    "private_financial_corp": [76214,53224,46938,45397,47815,34346,44074,16694,57780,54200,24202,26953,34268],
    "general_government": [1208753,957615,886876,765746,719055,675871,621480,578711,500639,440668,397273,343013,306590],
    "households_incl_npish": [3844515,3614851,2968302,2135450,2252167,2309463,1944226,1594573,1317599,1513127,1416428,1465013,1389322],
    "gross_capital_formation_total": [9624795,8695888,7193484,5463457,5855617,5886657,5053181,4918077,4422659,4179779,3794135,3847122,3403008],
}
gcf_rows = []
for sector, vals in gcf.items():
    for y, v in zip(gcf_years, vals):
        gcf_rows.append({"year": y, "sector": sector, "gross_capital_formation_inr_crore": v})
gcf_df = pd.DataFrame(gcf_rows)
gcf_df.to_csv("institutional_sector_gross_capital_formation_2011_12_to_2023_24.csv", index=False)
print("GCF table:", gcf_df.shape)

# --- Cross-validate NSDP current-price transcription against already-ingested file ---
existing = pd.read_csv("/home/user/India-Economic-Intelligence-Lab/data/raw/state_gsdp_nsdp_percapita.csv")
mismatches = []
for _, row in existing.iterrows():
    state = row["state"]
    for yr_col, yr_label in [("nsdp_pc_current_2024_25", "2024-25"), ("nsdp_pc_current_2023_24", "2023-24")]:
        existing_val = row[yr_col]
        match = df[(df["state"]==state) & (df["financial_year"]==yr_label)]
        if len(match) == 0:
            continue
        new_val = match["percapita_nsdp_current_prices_inr"].iloc[0]
        if pd.notna(existing_val) and pd.notna(new_val) and abs(existing_val - new_val) > 1:
            mismatches.append((state, yr_label, existing_val, new_val))
        elif pd.notna(existing_val) and pd.isna(new_val):
            mismatches.append((state, yr_label, existing_val, "BLANK in transcription"))
print(f"\n{len(mismatches)} mismatches between transcription and already-ingested file:")
for m in mismatches:
    print(" ", m)
