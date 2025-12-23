# app_rewire_cs_required.py
# -*- coding: utf-8 -*-
"""
REWIRE Compound Semiconductor Classification App (Required Y/N)
- Hardcoded multi-select categories (incl. supply_chain_Equipment)
- REQUIRED field: compound_semiconductor must be selected (Y or N) before Save
- Commit-on-next behavior (no auto-advance); Skip leaves record unlabeled
- Export guard: warns (and blocks by default) if unfinished records exist
- Cheat sheets (one-line keyword hints) under each taxonomy group
"""

import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="REWIRE Compound Semiconductor Classification App", layout="wide")
st.title("REWIRE Compound Semiconductor Classification App")

# ========= Constants =========
ORDER_COL = "__row_order"
MAIN_FLAG_COL = "compound_semiconductor"  # stores 'Y' or 'N'

# Display columns
COL_COMPANY   = "Company name Latin alphabet"
COL_TRADE_EN  = "Trade description (English)"
COL_DESC      = "Description and history"
COL_WEBSITE   = "Website address"
COL_PRI_IND_D = "Primary code in national industry classification - description"
COL_SEC_IND_D = "Secondary code in national industry classification - description"
COL_BVD_SECT  = "BvD sectors"

# ====== Hardcoded tag columns (multi-select) ======
SUPPLY_CHAIN_COLS = [
    "supply_chain_Substrate",
    "supply_chain_Epiwafer",
    "supply_chain_Device_Design",
    "supply_chain_Chip_Processing",
    "supply_chain_Package",
    "supply_chain_Equipment",
]

FUNCTIONAL_COLS = [
    "functional_taxonomy_Compound RF",
    "functional_taxonomy_Compound Photonic",
    "functional_taxonomy_Compound Sensors",
    "functional_taxonomy_Power Devices",
]

TAG_COLS = SUPPLY_CHAIN_COLS + FUNCTIONAL_COLS

# ====== Cheat sheets (one-line keyword hints) ======
CHEATS_SUPPLY = {
    "Substrate": "SiC/GaN/GaAs/InP wafers, substrates, boules, ingots; wafer slicing/polishing.",
    "Epiwafer": "Epitaxy, MOCVD/MBE, epitaxial wafers, epi services, homo/heteroepitaxy.",
    "Device_Design": "Fabless design, IC/device design, circuit design, PDK, reference design.",
    "Chip_Processing": "Wafer fab/foundry, lithography, etch, deposition (CVD/PVD/ALD), implant, CMP.",
    "Package": "Assembly/OSAT, bumping, dicing, wirebond/flip‑chip, testing/ATE.",
    "Equipment": "MOCVD/MBE tools, lithography systems, etchers, CVD/PVD/ALD, implanters, CMP, metrology/inspection, furnaces.",
}

CHEATS_FUNCTIONAL = {
    "Compound RF": "RF front‑end, PA, GaAs PHEMT, GaN HEMT, LNA, switch, mmWave.",
    "Compound Photonic": "LED, laser diode, VCSEL, LiDAR, photonics, optical transceiver.",
    "Compound Sensors": "Photodetector, IR sensor, image/ToF/UV sensors (compound materials).",
    "Power Devices": "SiC diode/MOSFET, GaN HEMT, power rectifier, power electronics.",
}

# ========= Sidebar =========
st.sidebar.header("Data")
uploaded = st.sidebar.file_uploader("Upload data: CSV (recommended) or Excel (with 'Results' sheet)", type=["csv","xlsx"])

st.sidebar.markdown("---")
st.sidebar.header("Export")
default_name = f"classified_results_required_{datetime.datetime.now():%Y%m%d_%H%M%S}.csv"
save_name = st.sidebar.text_input("Output file name", value=default_name)

# ========= Helpers =========
def get_or_blank(row, col):
    return (str(row[col]) if col in row and pd.notna(row[col]) and str(row[col]).strip() else "—")

def normalize_url(url: str) -> str:
    if not url or url == "—":
        return ""
    u = url.strip()
    if not (u.lower().startswith("http://") or u.lower().startswith("https://")):
        u = "https://" + u
    return u

def ensure_order(df: pd.DataFrame):
    # drop typical unnamed columns
    for c in list(df.columns):
        if str(c).strip().lower().startswith("unnamed"):
            df = df.drop(columns=[c])
    if ORDER_COL not in df.columns:
        df[ORDER_COL] = range(1, len(df) + 1)
    return df.sort_values(ORDER_COL, kind="stable").reset_index(drop=True)

def load_input(file):
    if file.name.lower().endswith(".csv"):
        return pd.read_csv(file)
    else:
        xls = pd.ExcelFile(file)
        if "Results" not in xls.sheet_names:
            raise ValueError("Sheet 'Results' not found in Excel")
        return pd.read_excel(xls, sheet_name="Results")

def init_staged_state(order_val):
    """Initialize a blank staged state for the given row order."""
    st.session_state.staged = {
        "order": int(order_val),
        "flag": None,   # REQUIRED field (None means not selected yet)
        "tags": {c: False for c in TAG_COLS},
        "notes": "",
    }

# ========= State =========
if "df" not in st.session_state:
    st.session_state.df = None
if "view_idx" not in st.session_state:
    st.session_state.view_idx = 0
if "filter_unlabeled" not in st.session_state:
    st.session_state.filter_unlabeled = True
if "staged" not in st.session_state:
    st.session_state.staged = None  # holds transient edits for the current record only

# ========= Load data =========
if uploaded is not None and st.session_state.df is None:
    try:
        df = load_input(uploaded)
        # Ensure display columns exist
        needed = [COL_COMPANY, COL_TRADE_EN, COL_DESC, COL_WEBSITE, COL_PRI_IND_D, COL_SEC_IND_D, COL_BVD_SECT]
        for c in needed:
            if c not in df.columns:
                df[c] = pd.NA
        # Ensure tag columns exist
        for c in TAG_COLS:
            if c not in df.columns:
                df[c] = 0
        # Ensure global flag + notes
        if MAIN_FLAG_COL not in df.columns:
            df[MAIN_FLAG_COL] = pd.NA
        if "notes" not in df.columns:
            df["notes"] = pd.NA

        df = ensure_order(df)
        st.session_state.df = df
    except Exception as e:
        st.error(f"Failed to load data: {e}")

df = st.session_state.df
if df is None:
    st.info("Please upload a CSV/Excel file to begin.")
    st.stop()

# ========= Top toolbar =========
st.checkbox("Show only unlabeled (sum of all tags == 0 and CS flag not set)", key="filter_unlabeled", value=st.session_state.filter_unlabeled)
unlabeled_mask = (df[[c for c in TAG_COLS if c in df.columns]].sum(axis=1) == 0) & (df[MAIN_FLAG_COL].isna())
remaining = int(unlabeled_mask.sum())
st.metric("Remaining to label", remaining)
prog = 0 if len(df)==0 else (len(df) - remaining) / max(len(df),1)
st.progress(prog)

view = df[unlabeled_mask].reset_index(drop=True) if st.session_state.filter_unlabeled else df.reset_index(drop=True)
if len(view) == 0:
    st.success("All records are labeled. You can export the CSV below.")
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Export CSV", data=csv_bytes, file_name=save_name, mime="text/csv")
    st.stop()

idx = st.session_state.view_idx
if idx >= len(view):
    idx = 0
    st.session_state.view_idx = 0

row = view.iloc[idx]
real_pos = df.index[df[ORDER_COL] == row[ORDER_COL]][0]

# Initialize staged state for THIS record if it's empty or points to another row
if (st.session_state.staged is None) or (st.session_state.staged.get("order") != int(row[ORDER_COL])):
    init_staged_state(row[ORDER_COL])

st.subheader(f"Record {idx+1}/{len(view)} · Fixed order #{int(row[ORDER_COL])}")

left, right = st.columns([2,1], gap="large")

# ===== Left: info =====
with left:
    st.markdown(f"**Company**: {get_or_blank(row, COL_COMPANY)}")
    web = get_or_blank(row, COL_WEBSITE)
    web_url = normalize_url(web)
    st.markdown(f"**Website**: [{web}]({web_url})" if web_url else f"**Website**: {web}")

    st.markdown("**BvD sectors**:")
    st.write(get_or_blank(row, COL_BVD_SECT))

    st.markdown("**Trade description (English)**:")
    st.write(get_or_blank(row, COL_TRADE_EN))

    st.markdown("**Description and history**:")
    st.write(get_or_blank(row, COL_DESC))

    st.markdown("**Primary industry (desc)**:")
    st.write(get_or_blank(row, COL_PRI_IND_D))

    st.markdown("**Secondary industry (desc)**:")
    st.write(get_or_blank(row, COL_SEC_IND_D))

# ===== Right: classification (staged) =====
with right:
    st.markdown("**Compound semiconductor (REQUIRED)**")
    # Use a radio selector with explicit "(select)" to force a choice
    cs_choice = st.radio(
        "Belongs to compound semiconductor? *",
        options=["(select)", "Y", "N"],
        index=0 if st.session_state.staged["flag"] is None else (1 if st.session_state.staged["flag"] else 2),
        horizontal=True,
        help="Required. Choose Yes (Y) or No (N)."
    )
    if cs_choice == "(select)":
        st.session_state.staged["flag"] = None
    else:
        st.session_state.staged["flag"] = (cs_choice == "Y")

    st.markdown("---")
    st.markdown("**Select categories (multi‑select)**")

    # Supply chain
    st.caption("Supply chain")
    if CHEATS_SUPPLY:
        cheats_line = " • ".join([f"{k}: {v}" for k, v in CHEATS_SUPPLY.items()])
        st.caption(f"Cheat sheet — {cheats_line}")
    for c in SUPPLY_CHAIN_COLS:
        label = c.replace("supply_chain_", "")
        staged_val = st.session_state.staged["tags"].get(c, False)
        new_val = st.checkbox(label, value=bool(staged_val), key=f"sc_{c}_{row[ORDER_COL]}")
        st.session_state.staged["tags"][c] = bool(new_val)

    # Functional taxonomy
    st.caption("Functional taxonomy")
    if CHEATS_FUNCTIONAL:
        cheats_line = " • ".join([f"{k}: {v}" for k, v in CHEATS_FUNCTIONAL.items()])
        st.caption(f"Cheat sheet — {cheats_line}")
    for c in FUNCTIONAL_COLS:
        label = c.replace("functional_taxonomy_", "")
        staged_val = st.session_state.staged["tags"].get(c, False)
        new_val = st.checkbox(label, value=bool(staged_val), key=f"fn_{c}_{row[ORDER_COL]}")
        st.session_state.staged["tags"][c] = bool(new_val)

    notes_staged = st.session_state.staged.get("notes", "")
    notes_new = st.text_area("Notes (optional)", value=notes_staged, height=120, key=f"notes_{row[ORDER_COL]}")
    st.session_state.staged["notes"] = notes_new

st.markdown("---")
b1, b2, b3, b4 = st.columns([1,1,1,2])
with b1:
    if st.button("⬅️ Prev", use_container_width=True):
        st.session_state.view_idx = max(0, idx - 1)
        st.session_state.staged = None
        st.rerun()
with b2:
    if st.button("Skip ➡️", use_container_width=True):
        st.session_state.view_idx = min(len(view) - 1, idx + 1)
        st.session_state.staged = None
        st.rerun()
with b3:
    # Save button is disabled until REQUIRED Y/N chosen
    save_disabled = st.session_state.staged["flag"] is None
    if save_disabled:
        st.caption("⚠️ Choose Y or N before saving.")
    if st.button("✅ Save & Next", use_container_width=True, disabled=save_disabled):
        # Commit staged edits to df
        df.loc[real_pos, MAIN_FLAG_COL] = "Y" if st.session_state.staged["flag"] else "N"
        for c in TAG_COLS:
            df.loc[real_pos, c] = 1 if st.session_state.staged["tags"].get(c, False) else 0
        df.loc[real_pos, "notes"] = st.session_state.staged.get("notes", "")
        st.session_state.view_idx = min(len(view) - 1, idx + 1)
        st.session_state.staged = None
        st.rerun()

# ===== Export =====
st.markdown("### 📤 Export")
if remaining > 0:
    st.warning(f"There are still {remaining} unfinished records (unlabeled). Exporting now will include them as blanks.")
    allow_export = st.checkbox("I understand — allow export anyway")
else:
    allow_export = True

csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
st.download_button("⬇️ Export CSV", data=csv_bytes, file_name=save_name, mime="text/csv", use_container_width=True, disabled=not allow_export)
