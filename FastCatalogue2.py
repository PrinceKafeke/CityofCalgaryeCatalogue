#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="City of Calgary Inventory Catalogue",
    page_icon="📦",
    layout="wide",
)

# =========================================================
# GITHUB FILE URLS
# =========================================================
DATA_URL = "https://raw.githubusercontent.com/PrinceKafeke/CityofCalgaryeCatalogue/main/City%20of%20Calgary%20-%20790IN%20Inventory%20Data%20-%20Copy.xlsx"
LOGO_URL = "https://raw.githubusercontent.com/PrinceKafeke/CityofCalgaryeCatalogue/main/calgary_logo.png"

# =========================================================
# BRANDING + CUSTOM CSS
# =========================================================
CITY_RED = "#c8102e"
CITY_GREY = "#5f6368"
LIGHT_GREY = "#f5f5f5"
DARK_GREY = "#333333"
WHITE = "#ffffff"
HEALTHY_GREEN = "#2e7d32"
MEDIUM_YELLOW = "#edb100"
LOW_RED = "#d32f2f"

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {LIGHT_GREY};
    }}

    .brand-header {{
        background: linear-gradient(90deg, {CITY_RED} 0%, {CITY_GREY} 100%);
        padding: 16px 20px;
        border-radius: 12px;
        margin-bottom: 14px;
        color: white;
    }}

    .brand-title {{
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 4px;
    }}

    .brand-subtitle {{
        font-size: 0.95rem;
        opacity: 0.95;
    }}

    .alert-panel {{
        background-color: #fff3f3;
        border-left: 6px solid {LOW_RED};
        padding: 12px 14px;
        border-radius: 8px;
        margin-bottom: 16px;
    }}

    .item-card {{
        background-color: {WHITE};
        border-radius: 10px;
        padding: 10px 12px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(15,17,17,0.10);
        border: 1px solid #e3e6e6;
        min-height: 132px;
    }}

    .item-title {{
        font-size: 0.98rem;
        font-weight: 700;
        color: {CITY_RED};
        margin-bottom: 4px;
        line-height: 1.2;
    }}

    .item-sub {{
        font-size: 0.80rem;
        color: {DARK_GREY};
        margin-bottom: 4px;
        line-height: 1.35;
    }}

    .badge {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 600;
        margin-right: 4px;
        margin-top: 3px;
    }}

    .badge-healthy {{
        background-color: #e8f5e9;
        color: {HEALTHY_GREEN};
    }}

    .badge-medium {{
        background-color: #fff8e1;
        color: #8a6d00;
    }}

    .badge-low {{
        background-color: #ffebee;
        color: {LOW_RED};
    }}

    .badge-neutral {{
        background-color: #eef0f2;
        color: {CITY_GREY};
    }}

    .stock-dot {{
        height: 10px;
        width: 10px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 6px;
    }}

    .small-note {{
        color: {CITY_GREY};
        font-size: 0.78rem;
    }}

    .restock-box {{
        background-color: #f9fafb;
        border: 1px solid #e5e7eb;
        padding: 10px 12px;
        border-radius: 8px;
        margin-top: 8px;
    }}

    mark {{
        background-color: #fff3a3;
        padding: 0 2px;
        border-radius: 3px;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# HELPERS
# =========================================================
def safe_string(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def normalize_columns(df):
    out = df.copy()
    out.columns = (
        out.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(r"[^\w]", "", regex=True)
    )
    return out

def build_col_map(df, expected_cols):
    col_map = {}
    for logical_name, candidates in expected_cols.items():
        for c in candidates:
            if c in df.columns:
                col_map[logical_name] = c
                break
    return col_map

def unique_preserve_order(cols):
    seen = set()
    out = []
    for c in cols:
        if c not in seen:
            out.append(c)
            seen.add(c)
    return out

def to_excel_bytes(df_to_export: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_to_export.to_excel(writer, index=False, sheet_name="Catalogue")
    return buffer.getvalue()

def category_icon(category_value):
    c = safe_string(category_value).lower()
    if any(k in c for k in ["pipe", "plumb", "valve", "water"]):
        return "🚰"
    if any(k in c for k in ["elect", "wire", "cable", "light"]):
        return "⚡"
    if any(k in c for k in ["safety", "ppe", "msds", "whmis"]):
        return "🦺"
    if any(k in c for k in ["tool", "equip"]):
        return "🛠️"
    if any(k in c for k in ["clean", "jan", "chem"]):
        return "🧴"
    if any(k in c for k in ["office", "paper", "admin"]):
        return "📎"
    return "📦"

def stock_badge_html(status):
    s = safe_string(status).lower()
    if "healthy" in s or s == "low":
        return '<span class="badge badge-healthy">Healthy</span>'
    if "medium" in s:
        return '<span class="badge badge-medium">Medium</span>'
    if "risk" in s or "high" in s or "low / risk" in s:
        return '<span class="badge badge-low">Low / Risk</span>'
    return '<span class="badge badge-neutral">Unknown</span>'

def stock_dot_html(status):
    s = safe_string(status).lower()
    if "healthy" in s:
        color = HEALTHY_GREEN
    elif "medium" in s:
        color = MEDIUM_YELLOW
    elif "risk" in s or "high" in s or "low / risk" in s:
        color = LOW_RED
    else:
        color = CITY_GREY
    return f'<span class="stock-dot" style="background-color:{color};"></span>'

def restock_recommendation(row):
    forecast_daily = row.get("Forecast_Demand", np.nan)
    qty = row.get("Qty_On_Hand_Num", np.nan)

    if pd.isna(forecast_daily) or forecast_daily <= 0 or pd.isna(qty):
        return None

    target_days = 30
    target_stock = target_days * forecast_daily
    reorder_qty = max(0, int(np.ceil(target_stock - qty)))
    return {
        "target_days": target_days,
        "forecast_daily": forecast_daily,
        "target_stock": target_stock,
        "reorder_qty": reorder_qty,
    }

def tokenize_search(query):
    return [t for t in re.findall(r"\w+", safe_string(query).lower()) if t]

def highlight_text(text, tokens):
    text = safe_string(text)
    if not text or not tokens:
        return text
    result = text
    for tok in sorted(set(tokens), key=len, reverse=True):
        pattern = re.compile(re.escape(tok), re.IGNORECASE)
        result = pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", result)
    return result

def compute_forecast_and_risk(df, col_map):
    out = df.copy()

    qty_col = col_map.get("Qty On Hand")
    usage_col = col_map.get("Curr Year Usage")
    last_shipment_col = col_map.get("Last Shipment")

    if usage_col is not None:
        out["Forecast_Demand"] = pd.to_numeric(out[usage_col], errors="coerce") / 365.0
    else:
        out["Forecast_Demand"] = np.nan

    if qty_col is not None:
        out["Qty_On_Hand_Num"] = pd.to_numeric(out[qty_col], errors="coerce")
    else:
        out["Qty_On_Hand_Num"] = np.nan

    out["Days_of_Supply"] = np.where(
        (out["Forecast_Demand"] > 0) & out["Qty_On_Hand_Num"].notna(),
        out["Qty_On_Hand_Num"] / out["Forecast_Demand"],
        np.nan,
    )

    out["Stock_Status"] = "Unknown"

    has_qty = out["Qty_On_Hand_Num"].notna()
    out.loc[has_qty, "Stock_Status"] = "Healthy Stock"
    out.loc[has_qty & (out["Qty_On_Hand_Num"] < 30), "Stock_Status"] = "Medium"
    out.loc[has_qty & (out["Qty_On_Hand_Num"] < 10), "Stock_Status"] = "Low / Risk of Stockout"

    has_dos = out["Days_of_Supply"].notna()
    out.loc[has_dos, "Stock_Status"] = "Healthy Stock"
    out.loc[has_dos & (out["Days_of_Supply"] < 30), "Stock_Status"] = "Medium"
    out.loc[has_dos & (out["Days_of_Supply"] < 10), "Stock_Status"] = "Low / Risk of Stockout"

    if last_shipment_col is not None and last_shipment_col in out.columns:
        out[last_shipment_col] = pd.to_datetime(out[last_shipment_col], errors="coerce")

    return out

# =========================================================
# LOAD DATA
# =========================================================
@st.cache_data(show_spinner=False)
def load_city_data():
    return pd.read_excel(DATA_URL)

try:
    df_city = load_city_data()
except Exception as e:
    st.error(f"Could not load the Excel file from GitHub: {e}")
    st.stop()

# =========================================================
# BRAND HEADER
# =========================================================
logo_col, header_col = st.columns([1, 6])

with logo_col:
    st.image(LOGO_URL, width=110)

with header_col:
    st.markdown(
        """
        <div class="brand-header">
            <div class="brand-title">City of Calgary Inventory Catalogue</div>
            <div class="brand-subtitle">
                Browse General Stores inventory, flag low-stock items, and preview restock analytics.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# =========================================================
# COLUMN MAP
# =========================================================
expected_cols_cat = {
    "Item": ["Item"],
    "Name": ["Descript", "Description", "Name", "Item Name"],
    "Category": ["Category", "End Use Code", "Comm Code", "Replen Cls"],
    "Status Current": ["Status Current"],
    "Replen Cls": ["Replen Cls", "Replenishment Class"],
    "Special Inst": ["Special Inst", "Special Instructions"],
    "Std UOM": ["Std UOM", "Standard UOM", "UOM"],
    "End Use Code": ["End Use Code"],
    "Qty On Hand": ["Qty On Hand", "Quantity On Hand"],
    "Qty Avail": ["Qty Avail", "Quantity Available", "Qty Available"],
    "Curr Year Usage": ["Curr Year Usage", "Current Year Usage", "Usage"],
    "Manufacturer": ["Manufacturer Name", "Manufacturer", "manufacturer"],
    "Mfg ID": ["Mfg ID", "Mfg_ID", "Manufacturer ID"],
    "Mfg Itm ID": ["Mfg Itm ID", "Mfg Item ID", "Mfg_Itm_ID"],
    "Vendor Name": ["Vendor Name", "Vendor", "Supplier"],
    "Currency": ["Currency", "Curr"],
    "Unit Cost": ["Unit Cost", "Unit_Cost", "Cost", "Unit Price"],
    "Code": ["Code", "Item Code"],
    "Comm Code": ["Comm Code", "Commodity Code"],
    "MSDS ID": ["MSDS ID", "MSDS_ID"],
    "Location": ["Location", "Area Lev 1", "Lev 2", "Warehouse Location"],
    "Last Shipment": ["Last Shipment", "Last Shipment Date", "Last Received", "Receipt Date", "Date Received"],
    "Demand Rate": ["Demand Rate", "Curr Year Usage"],
    "Transaction Date": ["Transaction Date", "Txn Date", "Date", "Movement Date"],
    "Transaction Qty": ["Transaction Qty", "Qty Change", "Movement Qty", "Issue Qty", "Receipt Qty"],
    "Inventory Level": ["Inventory Level", "On Hand Snapshot", "Qty On Hand"],
}

col_map = build_col_map(df_city, expected_cols_cat)
df_city = compute_forecast_and_risk(df_city, col_map)

# =========================================================
# TABS
# =========================================================
tab_dashboard, tab_catalogue, tab_cleaner = st.tabs(
    ["📊 Dashboard", "📚 Catalogue", "🧹 Data Cleaning & EOQ Tool"]
)

# =========================================================
# DASHBOARD TAB
# =========================================================
with tab_dashboard:
    st.subheader("Inventory Dashboard")

    total_items = len(df_city)
    low_stock_items = (df_city["Stock_Status"] == "Low / Risk of Stockout").sum()
    predicted_stockout = low_stock_items

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Items", f"{total_items:,}")
    m2.metric("Items Low in Stock", f"{low_stock_items:,}")
    m3.metric("Items Predicted to Stock Out", f"{predicted_stockout:,}")

    st.markdown("---")

    risk_counts = (
        df_city["Stock_Status"]
        .value_counts(dropna=False)
        .rename_axis("Stock Status")
        .reset_index(name="Count")
    )
    st.markdown("#### Stock Risk Summary")
    st.bar_chart(risk_counts.set_index("Stock Status"))

    st.markdown("#### Low Stock Alert Panel")
    low_df = df_city[df_city["Stock_Status"] == "Low / Risk of Stockout"].copy()

    low_show_cols = []
    for logical in ["Item", "Name", "Category", "Qty On Hand", "Vendor Name", "Location"]:
        if logical in col_map:
            low_show_cols.append(col_map[logical])
    if "Days_of_Supply" in low_df.columns:
        low_show_cols.append("Days_of_Supply")

    low_show_cols = unique_preserve_order(low_show_cols)

    if not low_df.empty:
        st.dataframe(low_df[low_show_cols], use_container_width=True, height=260)
    else:
        st.success("No high-risk low-stock items detected with current rules.")

# =========================================================
# CATALOGUE TAB
# =========================================================
with tab_catalogue:
    st.subheader("Catalogue View")

    s1, s2, s3 = st.columns([3, 2, 1])
    with s1:
        global_search = st.text_input(
            "Search items",
            value="",
            placeholder="Search by item, name, category, code, manufacturer, supplier...",
        )
    with s2:
        sort_by = st.selectbox("Sort by", ["Relevance", "Name", "Qty On Hand", "Demand Rate", "Last Shipment"])
    with s3:
        sort_order = st.selectbox("Order", ["Ascending", "Descending"], index=0)

    st.sidebar.header("Catalogue Filters")

    if "Category" in col_map:
        category_vals = sorted(df_city[col_map["Category"]].dropna().astype(str).unique())
        selected_categories = st.sidebar.multiselect("Category", category_vals, default=category_vals)
    else:
        selected_categories = None

    low_stock_only = st.sidebar.checkbox("Show low stock only", value=False)

    if "Vendor Name" in col_map:
        supplier_vals = sorted(df_city[col_map["Vendor Name"]].dropna().astype(str).unique())
        selected_suppliers = st.sidebar.multiselect("Supplier", supplier_vals, default=supplier_vals)
    else:
        selected_suppliers = None

    if "Location" in col_map:
        location_vals = sorted(df_city[col_map["Location"]].dropna().astype(str).unique())
        selected_locations = st.sidebar.multiselect("Location", location_vals, default=location_vals)
    else:
        selected_locations = None

    if "Status Current" in col_map:
        status_vals = sorted(df_city[col_map["Status Current"]].dropna().astype(str).unique())
        selected_status = st.sidebar.multiselect("Status", status_vals, default=status_vals)
    else:
        selected_status = None

    show_trend_charts = st.sidebar.checkbox("Show trend charts", value=False)
    max_items_to_show = st.sidebar.selectbox("Items to display", [20, 40, 60, 100], index=1)

    filtered_df = df_city.copy()

    if selected_categories is not None:
        filtered_df = filtered_df[filtered_df[col_map["Category"]].astype(str).isin(selected_categories)]

    if selected_suppliers is not None:
        filtered_df = filtered_df[filtered_df[col_map["Vendor Name"]].astype(str).isin(selected_suppliers)]

    if selected_locations is not None:
        filtered_df = filtered_df[filtered_df[col_map["Location"]].astype(str).isin(selected_locations)]

    if selected_status is not None:
        filtered_df = filtered_df[filtered_df[col_map["Status Current"]].astype(str).isin(selected_status)]

    if low_stock_only:
        filtered_df = filtered_df[filtered_df["Stock_Status"] == "Low / Risk of Stockout"]

    search_tokens = tokenize_search(global_search)
    filtered_df["Search_Score"] = 0

    if search_tokens:
        search_cols = []
        for logical in ["Item", "Name", "Category", "Code", "Mfg ID", "Mfg Itm ID", "Manufacturer", "Vendor Name"]:
            if logical in col_map:
                search_cols.append(col_map[logical])

        search_cols = unique_preserve_order(search_cols)

        if search_cols:
            combined_text = filtered_df[search_cols].fillna("").astype(str).agg(" ".join, axis=1).str.lower()

            mask = pd.Series(False, index=filtered_df.index)
            score = pd.Series(0, index=filtered_df.index, dtype="int64")

            for tok in search_tokens:
                tok_mask = combined_text.str.contains(re.escape(tok), na=False, case=False)
                mask = mask | tok_mask
                score = score + tok_mask.astype(int)

            filtered_df = filtered_df[mask].copy()
            filtered_df["Search_Score"] = score.loc[filtered_df.index]

    risky = filtered_df[filtered_df["Stock_Status"] == "Low / Risk of Stockout"]
    if len(risky) > 0:
        top_names = []
        name_col = col_map.get("Name")
        item_col = col_map.get("Item")
        for _, r in risky.head(8).iterrows():
            nm = safe_string(r.get(name_col, "")) if name_col else safe_string(r.get(item_col, ""))
            if nm:
                top_names.append(nm)

        st.markdown(
            f"""
            <div class="alert-panel">
                <b>Low Stock Alert:</b> {len(risky)} item(s) are currently flagged as low stock / risk of stockout.<br>
                <span class="small-note">{", ".join(top_names)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    sort_map = {}
    if "Name" in col_map:
        sort_map["Name"] = col_map["Name"]
    if "Qty On Hand" in col_map:
        sort_map["Qty On Hand"] = "Qty_On_Hand_Num"
    if "Demand Rate" in col_map:
        sort_map["Demand Rate"] = "Forecast_Demand"
    if "Last Shipment" in col_map:
        sort_map["Last Shipment"] = col_map["Last Shipment"]

    if sort_by == "Relevance" and search_tokens:
        filtered_df = filtered_df.sort_values(
            by=["Search_Score", "Forecast_Demand"],
            ascending=[False, False],
            na_position="last",
        )
    elif sort_by in sort_map:
        filtered_df = filtered_df.sort_values(
            by=sort_map[sort_by],
            ascending=(sort_order == "Ascending"),
            na_position="last",
        )

    num_items = len(filtered_df)
    num_suppliers = filtered_df[col_map["Vendor Name"]].nunique() if "Vendor Name" in col_map else None
    avg_unit_cost = None
    if "Unit Cost" in col_map:
        avg_unit_cost = pd.to_numeric(filtered_df[col_map["Unit Cost"]], errors="coerce").mean()

    c1, c2, c3 = st.columns(3)
    c1.metric("Filtered Items", f"{num_items}")
    c2.metric("Suppliers", f"{num_suppliers}" if num_suppliers is not None else "N/A")
    c3.metric("Avg Unit Cost", f"{avg_unit_cost:,.2f}" if pd.notna(avg_unit_cost) else "N/A")

    st.caption(f"Showing up to {min(len(filtered_df), max_items_to_show)} of {len(filtered_df)} filtered items.")
    st.markdown("---")

    display_df = filtered_df.head(max_items_to_show).copy()

    def render_item_details(row, prefix=""):
        st.markdown("---")
        d1, d2 = st.columns([2, 1])

        with d1:
            details = {
                "Status": safe_string(row.get(col_map.get("Status Current", ""), "")),
                "Replenishment": safe_string(row.get(col_map.get("Replen Cls", ""), "")),
                "Quantity On Hand": row.get(col_map.get("Qty On Hand", ""), ""),
                "Quantity Available": row.get(col_map.get("Qty Avail", ""), ""),
                "Last Shipment": safe_string(row.get(col_map.get("Last Shipment", ""), "")),
                "Manufacturer": safe_string(row.get(col_map.get("Manufacturer", ""), "")),
                "Mfg ID": safe_string(row.get(col_map.get("Mfg ID", ""), "")),
                "Mfg Item ID": safe_string(row.get(col_map.get("Mfg Itm ID", ""), "")),
                "Code": safe_string(row.get(col_map.get("Code", ""), "")),
                "Comm Code": safe_string(row.get(col_map.get("Comm Code", ""), "")),
                "MSDS ID": safe_string(row.get(col_map.get("MSDS ID", ""), "")),
            }
            detail_df = pd.DataFrame({"Field": list(details.keys()), "Value": list(details.values())})
            st.dataframe(detail_df, use_container_width=True, hide_index=True)

        with d2:
            unit_cost = row.get(col_map.get("Unit Cost", ""), "")
            currency = safe_string(row.get(col_map.get("Currency", ""), ""))
            days_supply = row.get("Days_of_Supply", np.nan)

            st.markdown("**Quick Summary**")
            st.write(f"**Unit Cost:** {currency} {unit_cost}")
            st.write(f"**Days of Supply:** {round(days_supply, 1) if pd.notna(days_supply) else 'N/A'}")
            st.write(
                f"**Demand Rate:** {round(row.get('Forecast_Demand', np.nan), 2) if pd.notna(row.get('Forecast_Demand', np.nan)) else 'N/A'} / day"
            )

            rec = restock_recommendation(row)
            item_val = safe_string(row.get(col_map.get("Item", ""), ""))

            if st.button("Restock recommendation", key=f"restock_{prefix}_{item_val}"):
                if rec is None:
                    st.info("No forecast-based recommendation available. Add usage history or Curr Year Usage.")
                else:
                    st.markdown(
                        f"""
                        <div class="restock-box">
                        <b>Forecast suggestion</b><br>
                        Target days of supply: {rec['target_days']}<br>
                        Forecast daily demand: {rec['forecast_daily']:.2f}<br>
                        Target stock level: {rec['target_stock']:.1f}<br>
                        <b>Suggested reorder quantity: {rec['reorder_qty']}</b>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        if show_trend_charts:
            st.markdown("**Inventory Trend**")
            txn_date_col = col_map.get("Transaction Date")
            inv_level_col = col_map.get("Inventory Level")
            txn_qty_col = col_map.get("Transaction Qty")
            item_col = col_map.get("Item")

            if txn_date_col and (inv_level_col or txn_qty_col) and item_col:
                tmp = filtered_df[filtered_df[item_col] == row[item_col]].copy()
                if txn_date_col in tmp.columns:
                    tmp[txn_date_col] = pd.to_datetime(tmp[txn_date_col], errors="coerce")
                    tmp = tmp.sort_values(txn_date_col)

                if inv_level_col and inv_level_col in tmp.columns and tmp[txn_date_col].notna().any():
                    chart_df = tmp[[txn_date_col, inv_level_col]].dropna()
                    if len(chart_df) > 1:
                        st.line_chart(chart_df.set_index(txn_date_col))
                    else:
                        st.caption("Not enough trend points yet for this item.")
                elif txn_qty_col and txn_qty_col in tmp.columns and tmp[txn_date_col].notna().any():
                    chart_df = tmp[[txn_date_col, txn_qty_col]].dropna()
                    if len(chart_df) > 1:
                        st.line_chart(chart_df.set_index(txn_date_col))
                    else:
                        st.caption("Not enough transaction history yet for this item.")
                else:
                    st.caption("Trend chart requires transaction-history columns.")
            else:
                st.caption("Trend chart will appear automatically when transaction-history columns are available.")

    def render_compact_card(row, idx):
        item_col = col_map.get("Item")
        name_col = col_map.get("Name")
        category_col = col_map.get("Category")
        vendor_col = col_map.get("Vendor Name")
        location_col = col_map.get("Location")

        item_val = safe_string(row.get(item_col, "")) if item_col else ""
        name_val = safe_string(row.get(name_col, "")) if name_col else ""
        category_val = safe_string(row.get(category_col, "")) if category_col else ""
        supplier_val = safe_string(row.get(vendor_col, "")) if vendor_col else ""
        location_val = safe_string(row.get(location_col, "")) if location_col else ""

        qty_val = row.get("Qty_On_Hand_Num", np.nan)
        stock_status = row.get("Stock_Status", "Unknown")
        icon = category_icon(category_val)

        title_html = highlight_text(name_val or item_val or "Unnamed Item", search_tokens)
        category_html = highlight_text(category_val or "No category", search_tokens)
        supplier_html = highlight_text(supplier_val or "N/A", search_tokens)

        st.markdown(
            f"""
            <div class="item-card">
                <div class="item-title">{icon} {title_html}</div>
                <div class="item-sub"><b>Category:</b> {category_html}</div>
                <div class="item-sub"><b>Item:</b> {highlight_text(item_val or "N/A", search_tokens)}</div>
                <div class="item-sub"><b>Supplier:</b> {supplier_html}</div>
                <div class="item-sub"><b>Location:</b> {highlight_text(location_val or "N/A", search_tokens)}</div>
                <div class="item-sub"><b>Qty:</b> {qty_val if pd.notna(qty_val) else 'N/A'}</div>
                <div>{stock_dot_html(stock_status)} {stock_badge_html(stock_status)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        details_key = f"open_card_{idx}"
        if details_key not in st.session_state:
            st.session_state[details_key] = False

        b1, b2 = st.columns([1, 1])
        with b1:
            if st.button("Open details" if not st.session_state[details_key] else "Hide details", key=f"toggle_{idx}"):
                st.session_state[details_key] = not st.session_state[details_key]
        with b2:
            if "Search_Score" in row and search_tokens:
                st.caption(f"Match score: {int(row['Search_Score'])}")

        if st.session_state[details_key]:
            render_item_details(row, prefix=f"card_{idx}")

    if display_df.empty:
        st.info("No items match the current filters.")
    else:
        left_col, right_col = st.columns(2)
        for i, (_, row) in enumerate(display_df.iterrows()):
            with left_col if i % 2 == 0 else right_col:
                render_compact_card(row, i)

    with st.expander("View as table (full column view)"):
        display_logical_cols = [
            "Item",
            "Name",
            "Category",
            "Status Current",
            "Replen Cls",
            "Special Inst",
            "Std UOM",
            "End Use Code",
            "Qty On Hand",
            "Qty Avail",
            "Manufacturer",
            "Mfg ID",
            "Mfg Itm ID",
            "Vendor Name",
            "Location",
            "Last Shipment",
            "Currency",
            "Unit Cost",
            "Code",
            "Comm Code",
            "MSDS ID",
        ]

        display_cols = [col_map[l] for l in display_logical_cols if l in col_map]
        extra_cols = [c for c in ["Forecast_Demand", "Days_of_Supply", "Stock_Status"] if c in filtered_df.columns]
        show_cols = unique_preserve_order(display_cols + extra_cols)

        st.dataframe(filtered_df[show_cols], use_container_width=True, height=420)

    st.markdown("---")
    st.subheader("Download Filtered Catalogue")
    export_cols = [c for c in filtered_df.columns if c != "Qty_On_Hand_Num"]
    xlsx_data = to_excel_bytes(filtered_df[export_cols].copy())
    st.download_button(
        label="Download Filtered Catalogue as Excel",
        data=xlsx_data,
        file_name="filtered_catalogue.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# =========================================================
# DATA CLEANING & EOQ TAB
# =========================================================
with tab_cleaner:
    st.subheader("Inventory Data Cleaner & EOQ Preview")

    st.markdown(
        """
Upload an **Excel or CSV** extract and:
- clean the data using simple business rules,
- download a cleaned CSV,
- preview simple EOQ calculations,
- and prepare a dataset that can later support the forecasting / stockout module.
"""
    )

    REQUIRED_COLUMNS = [
        "Item",
        "Descript",
        "Status Current",
        "Replen Cls",
        "Special Inst",
        "Std UOM",
        "End Use Code",
        "Qty On Hand",
        "Qty Avail",
        "Curr Year Usage",
        "Manufacturer Name",
        "Mfg ID",
        "Mfg Itm ID",
        "Vendor Name",
        "Currency",
        "Unit Cost",
        "Code",
        "Comm Code",
        "MSDS ID",
    ]

    def clean_inventory(df):
        df = df.copy()
        df.columns = df.columns.str.strip()

        available_cols = [col for col in REQUIRED_COLUMNS if col in df.columns]
        df = df[available_cols]

        numeric_cols = ["Qty On Hand", "Qty Avail", "Unit Cost", "Curr Year Usage"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = (
                    df[col].astype(str)
                    .str.replace(",", "", regex=False)
                    .str.replace("$", "", regex=False)
                )
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "Status Current" in df.columns:
            df = df[df["Status Current"].astype(str).str.strip().str.lower() == "active"]

        if "Replen Cls" in df.columns:
            df = df[df["Replen Cls"].astype(str).str.strip().str.upper() != "ROR"]

        if "Special Inst" in df.columns:
            df = df[df["Special Inst"].astype(str).str.strip().str.lower() != "reorder on request"]

        if "Special Inst" in df.columns and "Qty On Hand" in df.columns:
            df = df[
                ~(
                    (df["Special Inst"].astype(str).str.strip().str.lower() == "delete") &
                    (df["Qty On Hand"] == 0)
                )
            ]

        if "MSDS ID" in df.columns:
            df["WHMIS Flag"] = df["MSDS ID"].notna()

        return df.dropna(how="all").reset_index(drop=True)

    uploaded_file = st.file_uploader("Upload Excel or CSV", type=["xlsx", "csv"])

    if uploaded_file:
        if uploaded_file.name.endswith(".csv"):
            df_raw = pd.read_csv(uploaded_file, encoding="latin1")
        else:
            df_raw = pd.read_excel(uploaded_file)

        st.success("File loaded successfully.")

        with st.expander("View original column names"):
            st.dataframe(
                pd.DataFrame(df_raw.columns, columns=["Column Name"]),
                use_container_width=True,
                height=300
            )

        cleaned = clean_inventory(df_raw)

        st.markdown("#### Cleaned Data Preview")
        st.dataframe(cleaned, use_container_width=True, height=400)

        st.download_button(
            "Download Cleaned CSV",
            cleaned.to_csv(index=False),
            "cleaned_inventory.csv",
            "text/csv",
        )

        st.markdown("---")
        st.subheader("EOQ Settings (Prototype Preview)")

        ordering_cost = st.number_input("Ordering cost per order (S)", min_value=0.0, value=100.0, step=1.0)
        holding_rate = st.slider("Annual holding cost rate (%)", min_value=0, max_value=100, value=20) / 100

        df_norm = normalize_columns(df_raw)

        required_norm = ["curr_year_usage", "unit_cost", "qty_on_hand", "item"]
        missing_norm = [c for c in required_norm if c not in df_norm.columns]

        if missing_norm:
            st.warning(f"EOQ preview unavailable: missing normalized columns {missing_norm}")
        else:
            df_eoq = df_norm.copy()
            df_eoq["annual_demand"] = pd.to_numeric(df_eoq["curr_year_usage"], errors="coerce")
            df_eoq["unit_cost"] = pd.to_numeric(df_eoq["unit_cost"], errors="coerce")
            df_eoq["qty_on_hand"] = pd.to_numeric(df_eoq["qty_on_hand"], errors="coerce")
            df_eoq["holding_cost"] = df_eoq["unit_cost"] * holding_rate
            df_eoq = df_eoq[df_eoq["holding_cost"] > 0]

            df_eoq["EOQ"] = np.sqrt(
                (2 * df_eoq["annual_demand"] * ordering_cost) / df_eoq["holding_cost"]
            )

            df_eoq["Forecast_Demand"] = df_eoq["annual_demand"] / 365.0
            df_eoq["Days_of_Supply"] = np.where(
                df_eoq["Forecast_Demand"] > 0,
                df_eoq["qty_on_hand"] / df_eoq["Forecast_Demand"],
                np.nan
            )
            df_eoq["Stockout_Risk"] = np.select(
                [
                    df_eoq["Days_of_Supply"] < 10,
                    (df_eoq["Days_of_Supply"] >= 10) & (df_eoq["Days_of_Supply"] < 30),
                    df_eoq["Days_of_Supply"] >= 30
                ],
                [
                    "High",
                    "Medium",
                    "Low"
                ],
                default="Unknown"
            )

            show_cols = [
                "item", "qty_on_hand", "annual_demand", "unit_cost",
                "EOQ", "Forecast_Demand", "Days_of_Supply", "Stockout_Risk"
            ]
            show_cols = [c for c in show_cols if c in df_eoq.columns]

            st.markdown("#### EOQ + Risk Preview")
            st.dataframe(df_eoq[show_cols], use_container_width=True, height=400)

            st.caption(
                "This prototype uses annual demand = current year usage and a simple forecast = annual demand / 365."
            )
    else:
        st.info("Upload an Excel or CSV file to use the cleaning and EOQ tool.")

