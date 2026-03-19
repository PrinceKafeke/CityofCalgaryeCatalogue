#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO
from datetime import datetime

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
    if "healthy" in s:
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
    avail_col = col_map.get("Qty Avail")
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

    if avail_col is not None:
        out["Qty_Avail_Num"] = pd.to_numeric(out[avail_col], errors="coerce")
    else:
        out["Qty_Avail_Num"] = out["Qty_On_Hand_Num"]

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

@st.cache_data(show_spinner=False)
def load_city_data():
    return pd.read_excel(DATA_URL)

# =========================================================
# LOAD DATA
# =========================================================
try:
    base_df = load_city_data()
except Exception as e:
    st.error(f"Could not load the Excel file from GitHub: {e}")
    st.stop()

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
}

col_map = build_col_map(base_df, expected_cols_cat)

# =========================================================
# SESSION STATE INVENTORY
# =========================================================
if "inventory_df" not in st.session_state:
    working_df = base_df.copy()

    qty_col = col_map.get("Qty On Hand")
    avail_col = col_map.get("Qty Avail")

    if qty_col and qty_col in working_df.columns:
        working_df[qty_col] = pd.to_numeric(working_df[qty_col], errors="coerce").fillna(0)

    if avail_col and avail_col in working_df.columns:
        working_df[avail_col] = pd.to_numeric(working_df[avail_col], errors="coerce").fillna(0)
    elif qty_col and qty_col in working_df.columns:
        working_df["Qty Avail"] = working_df[qty_col]
        col_map["Qty Avail"] = "Qty Avail"

    st.session_state.inventory_df = working_df

if "orders_log" not in st.session_state:
    st.session_state.orders_log = pd.DataFrame(
        columns=["Order Time", "Customer Name", "Department", "Item", "Description", "Order Qty"]
    )

def refresh_inventory():
    df = st.session_state.inventory_df.copy()
    st.session_state.inventory_view = compute_forecast_and_risk(df, col_map)

refresh_inventory()
df_city = st.session_state.inventory_view

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
                Connected customer and internal prototype for General Stores inventory visibility.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.caption("Prototype note: customer orders update the internal view within the same running app session.")

# =========================================================
# ORDER FUNCTION
# =========================================================
def place_order(item_value, customer_name, department, order_qty):
    item_col = col_map.get("Item")
    name_col = col_map.get("Name")
    qty_col = col_map.get("Qty On Hand")
    avail_col = col_map.get("Qty Avail")

    if item_col is None or qty_col is None:
        return False, "Required inventory columns are missing."

    df = st.session_state.inventory_df.copy()
    match_idx = df.index[df[item_col].astype(str) == str(item_value)]

    if len(match_idx) == 0:
        return False, "Item not found."

    idx = match_idx[0]

    current_on_hand = pd.to_numeric(df.at[idx, qty_col], errors="coerce")
    current_on_hand = 0 if pd.isna(current_on_hand) else float(current_on_hand)

    if avail_col and avail_col in df.columns:
        current_avail = pd.to_numeric(df.at[idx, avail_col], errors="coerce")
        current_avail = 0 if pd.isna(current_avail) else float(current_avail)
    else:
        current_avail = current_on_hand

    if order_qty <= 0:
        return False, "Order quantity must be positive."

    if order_qty > current_avail:
        return False, f"Only {int(current_avail)} unit(s) are currently available."

    df.at[idx, qty_col] = max(0, current_on_hand - order_qty)

    if avail_col and avail_col in df.columns:
        df.at[idx, avail_col] = max(0, current_avail - order_qty)

    st.session_state.inventory_df = df

    item_desc = safe_string(df.at[idx, name_col]) if name_col and name_col in df.columns else ""
    new_order = pd.DataFrame(
        [{
            "Order Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Customer Name": customer_name,
            "Department": department,
            "Item": item_value,
            "Description": item_desc,
            "Order Qty": order_qty,
        }]
    )
    st.session_state.orders_log = pd.concat([new_order, st.session_state.orders_log], ignore_index=True)

    refresh_inventory()
    return True, "Order placed successfully."

# =========================================================
# TABS
# =========================================================
tab_customer, tab_internal, tab_orders = st.tabs(
    ["🛒 Customer View", "📊 Internal View", "📋 Orders Log"]
)

# =========================================================
# CUSTOMER VIEW
# =========================================================
with tab_customer:
    st.subheader("Customer Catalogue")
    st.write("Search available inventory and place an order request.")

    c1, c2 = st.columns([3, 1])
    with c1:
        customer_search = st.text_input(
            "Search catalogue",
            placeholder="Search by item, description, category, supplier..."
        )
    with c2:
        customer_low_only = st.checkbox("Low stock only", value=False)

    search_tokens = tokenize_search(customer_search)
    customer_df = df_city.copy()

    if customer_low_only:
        customer_df = customer_df[customer_df["Stock_Status"] == "Low / Risk of Stockout"]

    if search_tokens:
        search_cols = []
        for logical in ["Item", "Name", "Category", "Manufacturer", "Vendor Name", "Code"]:
            if logical in col_map:
                search_cols.append(col_map[logical])
        search_cols = unique_preserve_order(search_cols)

        if search_cols:
            combined_text = customer_df[search_cols].fillna("").astype(str).agg(" ".join, axis=1).str.lower()
            mask = pd.Series(False, index=customer_df.index)
            for tok in search_tokens:
                mask = mask | combined_text.str.contains(re.escape(tok), na=False, case=False)
            customer_df = customer_df[mask].copy()

    customer_df = customer_df.sort_values(by="Qty_Avail_Num", ascending=False, na_position="last")

    st.caption(f"{len(customer_df)} item(s) match the current customer view filters.")

    item_col = col_map.get("Item")
    name_col = col_map.get("Name")
    category_col = col_map.get("Category")
    vendor_col = col_map.get("Vendor Name")
    avail_col = col_map.get("Qty Avail")

    for i, (_, row) in enumerate(customer_df.head(40).iterrows()):
        item_val = safe_string(row.get(item_col, "")) if item_col else ""
        name_val = safe_string(row.get(name_col, "")) if name_col else ""
        category_val = safe_string(row.get(category_col, "")) if category_col else ""
        vendor_val = safe_string(row.get(vendor_col, "")) if vendor_col else ""
        qty_avail = row.get("Qty_Avail_Num", np.nan)
        stock_status = row.get("Stock_Status", "Unknown")
        icon = category_icon(category_val)

        with st.expander(f"{icon} {name_val or item_val or 'Unnamed Item'}"):
            st.markdown(
                f"""
                <div class="item-card">
                    <div class="item-title">{highlight_text(name_val or item_val, search_tokens)}</div>
                    <div class="item-sub"><b>Item:</b> {highlight_text(item_val, search_tokens)}</div>
                    <div class="item-sub"><b>Category:</b> {highlight_text(category_val or 'N/A', search_tokens)}</div>
                    <div class="item-sub"><b>Supplier:</b> {highlight_text(vendor_val or 'N/A', search_tokens)}</div>
                    <div class="item-sub"><b>Available Quantity:</b> {int(qty_avail) if pd.notna(qty_avail) else 'N/A'}</div>
                    <div>{stock_dot_html(stock_status)} {stock_badge_html(stock_status)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.form(key=f"order_form_{i}"):
                f1, f2, f3 = st.columns(3)
                with f1:
                    customer_name = st.text_input("Customer name", key=f"name_{i}")
                with f2:
                    department = st.text_input("Department / business unit", key=f"dept_{i}")
                with f3:
                    max_qty = int(qty_avail) if pd.notna(qty_avail) and qty_avail > 0 else 0
                    order_qty = st.number_input(
                        "Order quantity",
                        min_value=1,
                        max_value=max(1, max_qty) if max_qty > 0 else 1,
                        value=1,
                        step=1,
                        key=f"qty_{i}",
                        disabled=(max_qty == 0)
                    )

                submitted = st.form_submit_button("Place order", disabled=(max_qty == 0))

                if submitted:
                    if not safe_string(customer_name):
                        st.warning("Please enter a customer name.")
                    elif not safe_string(department):
                        st.warning("Please enter a department or business unit.")
                    else:
                        ok, msg = place_order(item_val, customer_name, department, int(order_qty))
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

# =========================================================
# INTERNAL VIEW
# =========================================================
with tab_internal:
    st.subheader("Internal Inventory Dashboard")

    total_items = len(df_city)
    low_stock_items = (df_city["Stock_Status"] == "Low / Risk of Stockout").sum()
    medium_stock_items = (df_city["Stock_Status"] == "Medium").sum()
    total_orders = len(st.session_state.orders_log)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Items", f"{total_items:,}")
    m2.metric("Low Stock Items", f"{low_stock_items:,}")
    m3.metric("Medium Risk Items", f"{medium_stock_items:,}")
    m4.metric("Orders Placed", f"{total_orders:,}")

    st.markdown("---")

    st.markdown("#### Stock Risk Summary")
    risk_counts = (
        df_city["Stock_Status"]
        .value_counts(dropna=False)
        .rename_axis("Stock Status")
        .reset_index(name="Count")
    )
    st.bar_chart(risk_counts.set_index("Stock Status"))

    st.markdown("#### Low Stock Alert Panel")
    low_df = df_city[df_city["Stock_Status"] == "Low / Risk of Stockout"].copy()
    low_show_cols = []

    for logical in ["Item", "Name", "Category", "Qty On Hand", "Qty Avail", "Vendor Name"]:
        if logical in col_map:
            low_show_cols.append(col_map[logical])
    low_show_cols += [c for c in ["Forecast_Demand", "Days_of_Supply"] if c in low_df.columns]
    low_show_cols = unique_preserve_order(low_show_cols)

    if not low_df.empty:
        st.dataframe(low_df[low_show_cols], use_container_width=True, height=260)
    else:
        st.success("No high-risk low-stock items detected with current rules.")

    st.markdown("#### Inventory Table")
    display_logical_cols = [
        "Item",
        "Name",
        "Category",
        "Qty On Hand",
        "Qty Avail",
        "Vendor Name",
        "Location",
        "Unit Cost",
    ]
    display_cols = [col_map[l] for l in display_logical_cols if l in col_map]
    extra_cols = [c for c in ["Forecast_Demand", "Days_of_Supply", "Stock_Status"] if c in df_city.columns]
    show_cols = unique_preserve_order(display_cols + extra_cols)
    st.dataframe(df_city[show_cols], use_container_width=True, height=420)

    st.markdown("#### Restock Recommendations")
    restock_rows = []
    for _, row in df_city.iterrows():
        rec = restock_recommendation(row)
        if rec is not None and rec["reorder_qty"] > 0:
            restock_rows.append({
                "Item": safe_string(row.get(col_map.get("Item", ""), "")),
                "Description": safe_string(row.get(col_map.get("Name", ""), "")),
                "Current Qty": row.get("Qty_On_Hand_Num", np.nan),
                "Forecast Daily Demand": round(rec["forecast_daily"], 2),
                "Target Days": rec["target_days"],
                "Suggested Reorder Qty": rec["reorder_qty"],
            })

    if restock_rows:
        restock_df = pd.DataFrame(restock_rows).sort_values("Suggested Reorder Qty", ascending=False)
        st.dataframe(restock_df, use_container_width=True, height=300)
    else:
        st.info("No forecast-based reorder recommendations at this time.")

    st.markdown("---")
    export_cols = [c for c in df_city.columns if c not in ["Qty_On_Hand_Num", "Qty_Avail_Num"]]
    xlsx_data = to_excel_bytes(df_city[export_cols].copy())
    st.download_button(
        label="Download Updated Internal Inventory Excel",
        data=xlsx_data,
        file_name="updated_internal_inventory.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# =========================================================
# ORDERS LOG
# =========================================================
with tab_orders:
    st.subheader("Customer Orders Log")

    if st.session_state.orders_log.empty:
        st.info("No customer orders have been placed in this session yet.")
    else:
        st.dataframe(st.session_state.orders_log, use_container_width=True, height=400)

        orders_xlsx = to_excel_bytes(st.session_state.orders_log.copy())
        st.download_button(
            label="Download Orders Log as Excel",
            data=orders_xlsx,
            file_name="customer_orders_log.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.markdown("---")
    if st.button("Reset prototype inventory to original GitHub file"):
        st.session_state.inventory_df = base_df.copy()
        st.session_state.orders_log = pd.DataFrame(
            columns=["Order Time", "Customer Name", "Department", "Item", "Description", "Order Qty"]
        )
        refresh_inventory()
        st.success("Prototype inventory has been reset.")
        st.rerun()

