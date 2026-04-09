#!/usr/bin/env python
# coding: utf-8

import streamlit as st
import pandas as pd
import numpy as np
import re
from io import BytesIO

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="City of Calgary General Stores",
    page_icon="🛒",
    layout="wide",
)

# =========================================================
# STATIC ASSETS
# =========================================================
LOGO_URL = "https://raw.githubusercontent.com/PrinceKafeke/CityofCalgaryeCatalogue/main/calgary_logo.png"
PLACEHOLDER_IMAGE_URL = "https://raw.githubusercontent.com/PrinceKafeke/CityofCalgaryeCatalogue/main/images/placeholder.png"
IMAGE_MAP_URL = "https://raw.githubusercontent.com/PrinceKafeke/CityofCalgaryeCatalogue/main/item_image_mapping.csv"

# =========================================================
# STYLE
# =========================================================
CITY_RED = "#c8102e"
CITY_GREY = "#5f6368"
NAVY = "#1f2a44"
LIGHT_BG = "#f6f7f9"
WHITE = "#ffffff"
GREEN = "#2e7d32"
YELLOW = "#edb100"
RED = "#d32f2f"

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {LIGHT_BG};
    }}

    .header-box {{
        background-color: {NAVY};
        color: white;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }}

    .header-title {{
        font-size: 1.7rem;
        font-weight: 700;
        margin-bottom: 3px;
    }}

    .header-subtitle {{
        font-size: 0.96rem;
        opacity: 0.95;
    }}

    .hero {{
        background: linear-gradient(90deg, #f2c6e8 0%, #f7d7ea 100%);
        border-radius: 14px;
        padding: 22px 24px;
        margin-bottom: 14px;
    }}

    .hero-title {{
        font-size: 1.9rem;
        font-weight: 800;
        line-height: 1.1;
        color: #14213d;
    }}

    .hero-sub {{
        font-size: 1rem;
        margin-top: 8px;
        color: #1f2937;
    }}

    .section-box {{
        background-color: {WHITE};
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(15,17,17,0.08);
    }}

    .section-title {{
        font-size: 1.12rem;
        font-weight: 700;
        margin-bottom: 10px;
        color: #111827;
    }}

    .product-card {{
        background-color: {WHITE};
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 10px;
        min-height: 210px;
    }}

    .product-title {{
        font-size: 0.98rem;
        font-weight: 700;
        color: {CITY_RED};
        line-height: 1.2;
        margin-bottom: 6px;
    }}

    .product-sub {{
        font-size: 0.83rem;
        color: #374151;
        line-height: 1.35;
        margin-bottom: 3px;
    }}

    .pill {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 600;
        margin-top: 6px;
        margin-right: 4px;
    }}

    .pill-green {{
        background: #e8f5e9;
        color: {GREEN};
    }}

    .pill-yellow {{
        background: #fff8e1;
        color: #8a6d00;
    }}

    .pill-red {{
        background: #ffebee;
        color: {RED};
    }}

    .pill-grey {{
        background: #eef0f2;
        color: {CITY_GREY};
    }}

    .detail-box {{
        background-color: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 10px 12px;
        margin-top: 8px;
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

def tokenize_search(query):
    return [t for t in re.findall(r"\w+", safe_string(query).lower()) if t]

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

def stock_status_from_row(row):
    qty = row.get("Qty_On_Hand_Num", np.nan)
    dos = row.get("Days_of_Supply", np.nan)
    replen_cls = safe_string(row.get("Replen_Cls_Value", "")).upper()

    if replen_cls == "DLY":
        return "Not Restocked (DLY)"

    if pd.notna(dos):
        if dos < 10:
            return "Low / Risk of Stockout"
        elif dos < 30:
            return "Medium"
        return "Healthy Stock"

    if pd.notna(qty):
        if qty < 10:
            return "Low / Risk of Stockout"
        elif qty < 30:
            return "Medium"
        return "Healthy Stock"

    return "Unknown"

def stock_badge_html(status):
    s = safe_string(status).lower()
    if "healthy" in s:
        return '<span class="pill pill-green">In Stock</span>'
    if "medium" in s:
        return '<span class="pill pill-yellow">Limited</span>'
    if "dly" in s or "not restocked" in s:
        return '<span class="pill pill-grey">DLY / Non-Restock</span>'
    if "low" in s or "risk" in s:
        return '<span class="pill pill-red">Low Stock</span>'
    return '<span class="pill pill-grey">Unknown</span>'

def compute_inventory_metrics(df, col_map):
    out = df.copy()

    qty_col = col_map.get("Qty On Hand")
    avail_col = col_map.get("Qty Avail")
    usage_col = col_map.get("Curr Year Usage")
    replen_col = col_map.get("Replen Cls")
    msds_col = col_map.get("MSDS ID")

    if qty_col and qty_col in out.columns:
        out[qty_col] = pd.to_numeric(out[qty_col], errors="coerce")
        out["Qty_On_Hand_Num"] = out[qty_col]
    else:
        out["Qty_On_Hand_Num"] = np.nan

    if avail_col and avail_col in out.columns:
        out[avail_col] = pd.to_numeric(out[avail_col], errors="coerce")
        out["Qty_Avail_Num"] = out[avail_col]
    else:
        out["Qty_Avail_Num"] = out["Qty_On_Hand_Num"]

    if usage_col and usage_col in out.columns:
        out[usage_col] = pd.to_numeric(out[usage_col], errors="coerce")
        out["Avg_Daily_Usage"] = out[usage_col] / 365.0
        out["Curr_Year_Usage_Num"] = out[usage_col]
    else:
        out["Avg_Daily_Usage"] = np.nan
        out["Curr_Year_Usage_Num"] = np.nan

    out["Days_of_Supply"] = np.where(
        (out["Avg_Daily_Usage"] > 0) & out["Qty_On_Hand_Num"].notna(),
        out["Qty_On_Hand_Num"] / out["Avg_Daily_Usage"],
        np.nan,
    )

    if replen_col and replen_col in out.columns:
        out["Replen_Cls_Value"] = out[replen_col].astype(str)
    else:
        out["Replen_Cls_Value"] = ""

    if msds_col and msds_col in out.columns:
        out["WHMIS_Required"] = out[msds_col].notna() & (out[msds_col].astype(str).str.strip() != "")
    else:
        out["WHMIS_Required"] = False

    out["Slow_Moving_Flag"] = np.where(
        (out["Curr_Year_Usage_Num"].fillna(0) <= 5) & (out["Qty_On_Hand_Num"].fillna(0) > 0),
        True,
        False
    )

    out["Stock_Status"] = out.apply(stock_status_from_row, axis=1)
    return out

def cart_total_items(cart):
    return int(sum(item["qty"] for item in cart.values()))

def cart_total_value(cart):
    total = 0.0
    for item in cart.values():
        unit_cost = item.get("unit_cost", np.nan)
        qty = item.get("qty", 0)
        if pd.notna(unit_cost):
            total += float(unit_cost) * qty
    return total

def add_to_cart(row, col_map, qty_to_add):
    item_col = col_map.get("Item")
    name_col = col_map.get("Name")
    category_col = col_map.get("Category")
    vendor_col = col_map.get("Vendor Name")
    unit_cost_col = col_map.get("Unit Cost")
    currency_col = col_map.get("Currency")

    item_id = safe_string(row.get(item_col, ""))
    if not item_id:
        return False, "Item code missing."

    available = row.get("Qty_Avail_Num", np.nan)
    if pd.isna(available) or int(available) <= 0:
        return False, "Item is not available for ordering."
    available = int(available)

    current_in_cart = st.session_state.cart.get(item_id, {}).get("qty", 0)

    if qty_to_add <= 0:
        return False, "Quantity must be positive."

    if current_in_cart + qty_to_add > available:
        return False, f"Only {available} unit(s) available."

    unit_cost = np.nan
    if unit_cost_col and unit_cost_col in row.index:
        unit_cost = pd.to_numeric(
            pd.Series([row.get(unit_cost_col, np.nan)]), errors="coerce"
        ).iloc[0]

    st.session_state.cart[item_id] = {
        "item": item_id,
        "name": safe_string(row.get(name_col, "")) if name_col else "",
        "category": safe_string(row.get(category_col, "")) if category_col else "",
        "vendor": safe_string(row.get(vendor_col, "")) if vendor_col else "",
        "qty": current_in_cart + qty_to_add,
        "unit_cost": unit_cost,
        "currency": safe_string(row.get(currency_col, "")) if currency_col else "",
    }
    return True, "Added to cart."

def remove_from_cart(item_id):
    if item_id in st.session_state.cart:
        del st.session_state.cart[item_id]

def checkout_cart(customer_name, department, col_map, whmis_confirmed=False):
    if not st.session_state.cart:
        return False, "Cart is empty."

    item_col = col_map.get("Item")
    qty_col = col_map.get("Qty On Hand")
    avail_col = col_map.get("Qty Avail")
    name_col = col_map.get("Name")
    msds_col = col_map.get("MSDS ID")

    if item_col is None or qty_col is None:
        return False, "Inventory columns missing."

    df = st.session_state.inventory_df.copy()
    order_rows = []

    for item_id, cart_item in st.session_state.cart.items():
        match_idx = df.index[df[item_col].astype(str) == str(item_id)]
        if len(match_idx) == 0:
            return False, f"Item {item_id} not found."

        idx = match_idx[0]
        order_qty = int(cart_item["qty"])

        current_on_hand = pd.to_numeric(df.at[idx, qty_col], errors="coerce")
        current_on_hand = 0 if pd.isna(current_on_hand) else int(current_on_hand)

        if avail_col and avail_col in df.columns:
            current_avail = pd.to_numeric(df.at[idx, avail_col], errors="coerce")
            current_avail = 0 if pd.isna(current_avail) else int(current_avail)
        else:
            current_avail = current_on_hand

        if order_qty > current_avail:
            return False, f"Item {item_id} no longer has enough available stock."

        if msds_col and msds_col in df.columns:
            msds_val = safe_string(df.at[idx, msds_col])
            if msds_val and not whmis_confirmed:
                return False, "This cart includes WHMIS-controlled item(s). Please confirm WHMIS before submitting."

        df.at[idx, qty_col] = max(0, current_on_hand - order_qty)

        if avail_col and avail_col in df.columns:
            df.at[idx, avail_col] = max(0, current_avail - order_qty)

        item_desc = safe_string(df.at[idx, name_col]) if name_col and name_col in df.columns else ""
        order_rows.append({
            "Order Time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Customer Name": customer_name,
            "Department": department,
            "Item": item_id,
            "Description": item_desc,
            "Order Qty": order_qty,
        })

    st.session_state.inventory_df = df

    if order_rows:
        new_orders = pd.DataFrame(order_rows)
        st.session_state.orders_log = pd.concat(
            [new_orders, st.session_state.orders_log],
            ignore_index=True
        )

    st.session_state.cart = {}
    refresh_inventory()
    return True, "Checkout complete."

def refresh_inventory():
    if "inventory_df" not in st.session_state or "col_map" not in st.session_state:
        return
    st.session_state.inventory_view = compute_inventory_metrics(
        st.session_state.inventory_df.copy(),
        st.session_state.col_map,
    )

def to_excel_bytes(df_to_export: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_to_export.to_excel(writer, index=False, sheet_name="Orders")
    return buffer.getvalue()

def to_csv_bytes(df_to_export: pd.DataFrame) -> bytes:
    return df_to_export.to_csv(index=False).encode("utf-8")

@st.cache_data(show_spinner=False)
def load_image_map_from_github():
    try:
        image_map_df = pd.read_csv(IMAGE_MAP_URL)
        image_map_df.columns = [str(c).strip() for c in image_map_df.columns]
        if "Item" not in image_map_df.columns or "image_url" not in image_map_df.columns:
            return pd.DataFrame(columns=["Item", "image_url"])
        image_map_df["Item"] = image_map_df["Item"].astype(str).str.strip()
        image_map_df["image_url"] = image_map_df["image_url"].astype(str).str.strip()
        image_map_df = image_map_df[["Item", "image_url"]].drop_duplicates(subset=["Item"], keep="last")
        return image_map_df
    except Exception:
        return pd.DataFrame(columns=["Item", "image_url"])

def sync_image_lookup():
    image_map_df = st.session_state.get("image_map_df", pd.DataFrame(columns=["Item", "image_url"])).copy()
    if image_map_df.empty:
        st.session_state.image_lookup = {}
        return

    image_map_df.columns = [str(c).strip() for c in image_map_df.columns]
    if "Item" not in image_map_df.columns or "image_url" not in image_map_df.columns:
        st.session_state.image_lookup = {}
        return

    image_map_df["Item"] = image_map_df["Item"].astype(str).str.strip()
    image_map_df["image_url"] = image_map_df["image_url"].astype(str).str.strip()
    image_map_df = image_map_df[(image_map_df["Item"] != "") & (image_map_df["image_url"] != "")]
    image_map_df = image_map_df.drop_duplicates(subset=["Item"], keep="last")

    st.session_state.image_map_df = image_map_df
    st.session_state.image_lookup = dict(zip(image_map_df["Item"], image_map_df["image_url"]))

def get_item_image_url(row, col_map):
    item_col = col_map.get("Item")
    item_id = safe_string(row.get(item_col, "")) if item_col else ""
    return st.session_state.get("image_lookup", {}).get(item_id, PLACEHOLDER_IMAGE_URL)

def upsert_image_mapping(item_id, image_url):
    item_id = safe_string(item_id)
    image_url = safe_string(image_url)

    if not item_id or not image_url:
        return False, "Item and image URL are required."

    current_df = st.session_state.get("image_map_df", pd.DataFrame(columns=["Item", "image_url"])).copy()
    if current_df.empty:
        current_df = pd.DataFrame(columns=["Item", "image_url"])

    current_df["Item"] = current_df.get("Item", pd.Series(dtype=str)).astype(str).str.strip()
    current_df["image_url"] = current_df.get("image_url", pd.Series(dtype=str)).astype(str).str.strip()

    current_df = current_df[current_df["Item"] != item_id]
    new_row = pd.DataFrame([{"Item": item_id, "image_url": image_url}])
    current_df = pd.concat([current_df, new_row], ignore_index=True)

    st.session_state.image_map_df = current_df
    sync_image_lookup()
    return True, "Image mapping saved for this session."

def remove_image_mapping(item_id):
    item_id = safe_string(item_id)
    current_df = st.session_state.get("image_map_df", pd.DataFrame(columns=["Item", "image_url"])).copy()
    if current_df.empty:
        return False, "No image mapping exists."

    current_df["Item"] = current_df["Item"].astype(str).str.strip()
    new_df = current_df[current_df["Item"] != item_id].copy()

    if len(new_df) == len(current_df):
        return False, "No image mapping found for that item."

    st.session_state.image_map_df = new_df
    sync_image_lookup()
    return True, "Image mapping removed for this session."

# =========================================================
# REQUIRED UPLOAD GATE
# =========================================================
st.markdown("### Upload current PeopleSoft inventory file")
uploaded_file = st.file_uploader(
    "Upload Excel file to enter the catalogue",
    type=["xlsx"],
    help="Users must upload the latest PeopleSoft Excel file before accessing the catalogue.",
)

if uploaded_file is None:
    st.info("Upload the latest PeopleSoft Excel file to enter the catalogue.")
    st.stop()

try:
    raw_df = pd.read_excel(uploaded_file)
except Exception as e:
    st.error(f"Could not read the uploaded file: {e}")
    st.stop()

raw_df.columns = [str(c).strip() for c in raw_df.columns]

# =========================================================
# COLUMN MAP
# =========================================================
expected_cols = {
    "Item": ["Item"],
    "Name": ["Descript", "Description", "Name", "Item Name"],
    "Category": ["Category", "End Use Code", "Comm Code", "Replen Cls"],
    "Qty On Hand": ["Qty On Hand", "Quantity On Hand"],
    "Qty Avail": ["Qty Avail", "Quantity Available", "Qty Available"],
    "Curr Year Usage": ["Curr Year Usage", "Current Year Usage", "Usage"],
    "Vendor Name": ["Vendor Name", "Vendor", "Supplier"],
    "Unit Cost": ["Unit Cost", "Unit_Cost", "Cost", "Unit Price"],
    "Currency": ["Currency", "Curr"],
    "Location": ["Location", "Area Lev 1", "Lev 2", "Warehouse Location"],
    "Status Current": ["Status Current"],
    "Std UOM": ["Std UOM", "Standard UOM", "UOM"],
    "Manufacturer": ["Manufacturer Name", "Manufacturer"],
    "Mfg ID": ["Mfg ID", "Mfg_ID", "Manufacturer ID"],
    "Mfg Itm ID": ["Mfg Itm ID", "Mfg Item ID", "Mfg_Itm_ID"],
    "Code": ["Code", "Item Code"],
    "Special Inst": ["Special Inst", "Special Instructions"],
    "Replen Cls": ["Replen Cls", "Replenishment Class"],
    "End Use Code": ["End Use Code"],
    "MSDS ID": ["MSDS ID", "MSDS_ID"],
    "Comm Code": ["Comm Code", "Commodity Code"],
}

st.session_state.col_map = build_col_map(raw_df, expected_cols)

# =========================================================
# SESSION STATE
# =========================================================
if "inventory_df" not in st.session_state or st.session_state.get("loaded_filename") != uploaded_file.name:
    st.session_state.inventory_df = raw_df.copy()
    st.session_state.loaded_filename = uploaded_file.name
    st.session_state.cart = {}
    st.session_state.orders_log = pd.DataFrame(
        columns=["Order Time", "Customer Name", "Department", "Item", "Description", "Order Qty"]
    )

if "cart" not in st.session_state:
    st.session_state.cart = {}

if "orders_log" not in st.session_state:
    st.session_state.orders_log = pd.DataFrame(
        columns=["Order Time", "Customer Name", "Department", "Item", "Description", "Order Qty"]
    )

if "image_map_df" not in st.session_state:
    st.session_state.image_map_df = load_image_map_from_github().copy()
    sync_image_lookup()

# =========================================================
# CONSTANTS
# =========================================================
BUSINESS_UNITS = [
    "Calgary Transit",
    "Roads",
    "Water Services",
    "Waste & Recycling",
    "Fleet Services",
    "Parks & Open Spaces",
    "Fire Department",
    "Corporate Security",
    "Facilities Management",
    "Other",
]

refresh_inventory()
df = st.session_state.inventory_view.copy()
col_map = st.session_state.col_map

# =========================================================
# HEADER
# =========================================================
logo_col, title_col = st.columns([1, 8])

with logo_col:
    st.image(LOGO_URL, width=95)

with title_col:
    st.markdown(
        """
        <div class="header-box">
            <div class="header-title">City of Calgary General Stores</div>
            <div class="header-subtitle">Business unit ordering with internal planning and warehouse views</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# =========================================================
# VIEW SELECTOR
# =========================================================
st.sidebar.header("View Options")

user_role = st.sidebar.selectbox(
    "Select View",
    [
        "Business Unit View",
        "Inventory Planning View",
        "Warehouse Management View",
    ]
)

is_business_unit_view = user_role == "Business Unit View"
is_internal_view = user_role in ["Inventory Planning View", "Warehouse Management View"]

show_low_stock_only = st.sidebar.checkbox("Low stock only", value=False)

# =========================================================
# TOP FILTERS
# =========================================================
top_left, top_mid, top_right = st.columns([1.2, 3.2, 1.2])

category_col = col_map.get("Category")
vendor_col = col_map.get("Vendor Name")

all_categories = ["All Departments"]
if category_col and category_col in df.columns:
    all_categories += sorted(df[category_col].dropna().astype(str).unique().tolist())

all_vendors = ["All Suppliers"]
if vendor_col and vendor_col in df.columns:
    all_vendors += sorted(df[vendor_col].dropna().astype(str).unique().tolist())

with top_left:
    selected_category = st.selectbox("Department", all_categories)

with top_mid:
    st.markdown(
        """
        <style>
        div[data-baseweb="input"] input {
            min-height: 52px !important;
            font-size: 18px !important;
            border-radius: 12px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    search_text = st.text_input(
        "🔍 Search inventory",
        placeholder="Search items, suppliers, manufacturers, or codes",
    ).strip()

with top_right:
    selected_supplier = st.selectbox("Supplier", all_vendors)

# =========================================================
# HERO
# =========================================================
if user_role == "Inventory Planning View":
    hero_sub = "Review inventory requirements, stocking strategies, replenishment classes, and stockout risk."
elif user_role == "Warehouse Management View":
    hero_sub = "Review storage location, available quantities, handling-related details, and warehouse visibility."
else:
    hero_sub = "Browse General Stores inventory, compare availability, add items to cart, and submit requests by department or business unit."

st.markdown(
    f"""
    <div class="hero">
        <div class="hero-title">Support business unit ordering<br>with faster inventory access</div>
        <div class="hero-sub">{hero_sub}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# SIDEBAR FILTERS
# =========================================================
manufacturer_col = col_map.get("Manufacturer")
status_current_col = col_map.get("Status Current")
location_filter_col = col_map.get("Location")

st.sidebar.markdown("---")
st.sidebar.subheader("Filters")

all_manufacturers = ["All Manufacturers"]
if manufacturer_col and manufacturer_col in df.columns:
    all_manufacturers += sorted(df[manufacturer_col].dropna().astype(str).unique().tolist())
selected_manufacturer = st.sidebar.selectbox("Manufacturer", all_manufacturers)

all_statuses = ["All Statuses"]
if status_current_col and status_current_col in df.columns:
    all_statuses += sorted(df[status_current_col].dropna().astype(str).unique().tolist())
selected_status = st.sidebar.selectbox("Status", all_statuses)

all_locations = ["All Locations"]
if location_filter_col and location_filter_col in df.columns:
    all_locations += sorted(df[location_filter_col].dropna().astype(str).unique().tolist())
selected_location = st.sidebar.selectbox("Location", all_locations)

# =========================================================
# FILTER DATA
# =========================================================
filtered_df = df.copy()

if selected_category != "All Departments" and category_col and category_col in filtered_df.columns:
    filtered_df = filtered_df[filtered_df[category_col].astype(str) == selected_category]

if selected_supplier != "All Suppliers" and vendor_col and vendor_col in filtered_df.columns:
    filtered_df = filtered_df[filtered_df[vendor_col].astype(str) == selected_supplier]

if selected_manufacturer != "All Manufacturers" and manufacturer_col and manufacturer_col in filtered_df.columns:
    filtered_df = filtered_df[filtered_df[manufacturer_col].astype(str) == selected_manufacturer]

if selected_status != "All Statuses" and status_current_col and status_current_col in filtered_df.columns:
    filtered_df = filtered_df[filtered_df[status_current_col].astype(str) == selected_status]

if selected_location != "All Locations" and location_filter_col and location_filter_col in filtered_df.columns:
    filtered_df = filtered_df[filtered_df[location_filter_col].astype(str) == selected_location]

if show_low_stock_only:
    filtered_df = filtered_df[filtered_df["Stock_Status"] == "Low / Risk of Stockout"]

replen_col = col_map.get("Replen Cls")
if replen_col and replen_col in filtered_df.columns:
    filtered_df = filtered_df[
        filtered_df[replen_col].astype(str).str.upper() != "DLY"
    ]

filtered_df = filtered_df[
    filtered_df["Qty_Avail_Num"].notna() & (filtered_df["Qty_Avail_Num"] > 0)
]

tokens = tokenize_search(search_text)
if tokens:
    search_cols = []
    for logical in ["Item", "Name", "Category", "Vendor Name", "Location", "Manufacturer", "Code"]:
        if logical in col_map:
            search_cols.append(col_map[logical])
    search_cols = unique_preserve_order(search_cols)

    if search_cols:
        combined = filtered_df[search_cols].fillna("").astype(str).agg(" ".join, axis=1).str.lower()
        mask = pd.Series(True, index=filtered_df.index)
        for tok in tokens:
            mask = mask & combined.str.contains(re.escape(tok), na=False, case=False)
        filtered_df = filtered_df[mask]

# =========================================================
# BUSINESS UNIT CART SIDEBAR ONLY
# =========================================================
if is_business_unit_view:
    with st.sidebar.expander("🛒 Cart Summary", expanded=False):
        st.metric("Items in Cart", cart_total_items(st.session_state.cart))
        st.metric("Estimated Value", f"{cart_total_value(st.session_state.cart):,.2f}")
        st.caption("Estimated value uses the Unit Cost field from the uploaded PeopleSoft file. That cost may represent a pack, case, box, or other inventory unit depending on the item setup.")

        if st.session_state.cart:
            st.markdown("---")
            for item_id, cart_item in st.session_state.cart.items():
                st.markdown(f"**{cart_item['name'] or item_id}**")
                st.caption(f"Item: {item_id}")
                st.caption(f"Qty: {cart_item['qty']}")
                if st.button("Remove", key=f"sidebar_remove_{item_id}"):
                    remove_from_cart(item_id)
                    st.rerun()
        else:
            st.info("Your cart is empty.")

# =========================================================
# METRICS
# =========================================================
low_stock_count = int((filtered_df["Stock_Status"] == "Low / Risk of Stockout").sum())

if user_role == "Business Unit View":
    m1, m2, m3 = st.columns(3)
    m1.metric("Items Shown", len(filtered_df))
    m2.metric("Low Stock", low_stock_count)
    m3.metric("Cart Items", cart_total_items(st.session_state.cart))
elif user_role == "Inventory Planning View":
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Items Shown", len(filtered_df))
    m2.metric("Stockout Risk Items", low_stock_count)
    m3.metric("Slow Moving Items", int(filtered_df["Slow_Moving_Flag"].fillna(False).sum()))
    m4.metric("WHMIS Items", int(filtered_df["WHMIS_Required"].fillna(False).sum()))
else:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Items Shown", len(filtered_df))
    m2.metric("Low Stock", low_stock_count)
    m3.metric("Locations Represented", filtered_df[col_map["Location"]].nunique() if col_map.get("Location") and col_map["Location"] in filtered_df.columns else 0)
    m4.metric("WHMIS Items", int(filtered_df["WHMIS_Required"].fillna(False).sum()))

# =========================================================
# BUSINESS UNIT CART SECTION ONLY
# =========================================================
if is_business_unit_view:
    st.markdown('<div class="section-box"><div class="section-title">🛒 Cart & Checkout</div>', unsafe_allow_html=True)

    if not st.session_state.cart:
        st.info("Your cart is empty.")
    else:
        cart_rows = []
        for item_id, cart_item in st.session_state.cart.items():
            unit_cost = cart_item.get("unit_cost", np.nan)
            qty = cart_item.get("qty", 0)
            line_total = float(unit_cost) * qty if pd.notna(unit_cost) else np.nan

            cart_rows.append({
                "Item": item_id,
                "Description": cart_item["name"],
                "Category": cart_item["category"],
                "Supplier": cart_item["vendor"],
                "Qty": qty,
                "Unit Cost": unit_cost,
                "Currency": cart_item["currency"],
                "Line Total": line_total,
            })

        cart_df = pd.DataFrame(cart_rows)
        st.dataframe(cart_df, use_container_width=True, height=220)

        remove_cols = st.columns(min(3, len(st.session_state.cart)))
        for i, (item_id, cart_item) in enumerate(st.session_state.cart.items()):
            with remove_cols[i % len(remove_cols)]:
                if st.button(f"Remove {cart_item['name'] or item_id}", key=f"remove_main_{item_id}"):
                    remove_from_cart(item_id)
                    st.rerun()

        st.markdown("---")
        d1, d2 = st.columns(2)
        d1.metric("Total Cart Items", cart_total_items(st.session_state.cart))
        d2.metric("Estimated Value", f"{cart_total_value(st.session_state.cart):,.2f}")

        c1, c2 = st.columns(2)
        with c1:
            first_name = st.text_input("First name", key="main_cart_first_name")
        with c2:
            last_name = st.text_input("Last name", key="main_cart_last_name")

        department_name = st.selectbox("Department / Business Unit", BUSINESS_UNITS, key="main_cart_department")

        main_cart_has_whmis = False
        item_col = col_map.get("Item")
        msds_col = col_map.get("MSDS ID")
        if item_col and msds_col and item_col in st.session_state.inventory_df.columns and msds_col in st.session_state.inventory_df.columns:
            for cart_item_id in st.session_state.cart.keys():
                whmis_match = st.session_state.inventory_df[
                    st.session_state.inventory_df[item_col].astype(str) == str(cart_item_id)
                ]
                if not whmis_match.empty and safe_string(whmis_match.iloc[0][msds_col]):
                    main_cart_has_whmis = True
                    break

        main_whmis_confirmed = False
        if main_cart_has_whmis:
            st.warning("This cart contains WHMIS-controlled item(s).")
            main_whmis_confirmed = st.checkbox("I have WHMIS certification", key="main_whmis_confirmed")

        requestor_name = f"{safe_string(first_name)} {safe_string(last_name)}".strip()

        if st.button("Submit order request", key="main_submit_order"):
            if not safe_string(first_name) or not safe_string(last_name):
                st.warning("Please enter both a first and last name.")
            elif main_cart_has_whmis and not main_whmis_confirmed:
                st.warning("Please confirm WHMIS certification before submitting this order.")
            else:
                ok, msg = checkout_cart(
                    requestor_name,
                    department_name,
                    col_map,
                    whmis_confirmed=main_whmis_confirmed
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# PRODUCT CARD RENDERER
# =========================================================
def render_product_card(row, idx_prefix, user_role="Business Unit View"):
    item_col = col_map.get("Item")
    name_col = col_map.get("Name")
    category_col = col_map.get("Category")
    vendor_col = col_map.get("Vendor Name")
    unit_cost_col = col_map.get("Unit Cost")
    currency_col = col_map.get("Currency")
    location_col = col_map.get("Location")
    uom_col = col_map.get("Std UOM")
    status_current_col = col_map.get("Status Current")
    manufacturer_col = col_map.get("Manufacturer")
    mfg_id_col = col_map.get("Mfg ID")
    mfg_item_col = col_map.get("Mfg Itm ID")
    code_col = col_map.get("Code")
    special_inst_col = col_map.get("Special Inst")
    replen_cls_col = col_map.get("Replen Cls")
    end_use_col = col_map.get("End Use Code")
    comm_code_col = col_map.get("Comm Code")
    msds_col = col_map.get("MSDS ID")

    item_val = safe_string(row.get(item_col, "")) if item_col else ""
    name_val = safe_string(row.get(name_col, "")) if name_col else ""
    category_val = safe_string(row.get(category_col, "")) if category_col else ""
    vendor_val = safe_string(row.get(vendor_col, "")) if vendor_col else ""
    location_val = safe_string(row.get(location_col, "")) if location_col else ""
    uom_val = safe_string(row.get(uom_col, "")) if uom_col else ""
    qty_avail = row.get("Qty_Avail_Num", np.nan)
    qty_on_hand = row.get("Qty_On_Hand_Num", np.nan)
    status = row.get("Stock_Status", "Unknown")
    unit_cost = row.get(unit_cost_col, "") if unit_cost_col else ""
    currency = safe_string(row.get(currency_col, "")) if currency_col else ""

    icon = category_icon(category_val)
    title_text = name_val or item_val or "Unnamed Item"
    image_url = get_item_image_url(row, col_map)

    st.image(image_url, use_container_width=True)

    st.markdown(
        f"""
        <div class="product-card">
            <div class="product-title">{icon} {title_text}</div>
            <div class="product-sub"><b>Item:</b> {item_val or "N/A"}</div>
            <div class="product-sub"><b>Category:</b> {category_val or "N/A"}</div>
            <div class="product-sub"><b>Supplier:</b> {vendor_val or "N/A"}</div>
            <div class="product-sub"><b>Available:</b> {int(qty_avail) if pd.notna(qty_avail) else "N/A"} {uom_val}</div>
            <div class="product-sub"><b>Location:</b> {location_val or "N/A"}</div>
            <div class="product-sub"><b>Unit Cost:</b> {currency} {unit_cost}</div>
            <div class="product-sub"><b>Pricing note:</b> Cost is shown per PeopleSoft unit, which may be a pack, case, or box rather than a single item.</div>
            <div>{stock_badge_html(status)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if user_role == "Inventory Planning View":
        status_current = safe_string(row.get(status_current_col, "")) if status_current_col else ""
        replen_cls = safe_string(row.get(replen_cls_col, "")) if replen_cls_col else ""
        special_inst = safe_string(row.get(special_inst_col, "")) if special_inst_col else ""
        end_use_val = safe_string(row.get(end_use_col, "")) if end_use_col else ""
        manufacturer = safe_string(row.get(manufacturer_col, "")) if manufacturer_col else ""
        code_val = safe_string(row.get(code_col, "")) if code_col else ""
        comm_code = safe_string(row.get(comm_code_col, "")) if comm_code_col else ""

        avg_daily_usage = row.get("Avg_Daily_Usage", np.nan)
        days_supply = row.get("Days_of_Supply", np.nan)
        slow_moving = bool(row.get("Slow_Moving_Flag", False))

        st.markdown(
            f"""
            <div class="detail-box">
                <div class="product-sub"><b>Avg Daily Usage:</b> {round(avg_daily_usage, 2) if pd.notna(avg_daily_usage) else 'N/A'}</div>
                <div class="product-sub"><b>Days Until Stockout:</b> {round(days_supply, 1) if pd.notna(days_supply) else 'N/A'}</div>
                <div class="product-sub"><b>Stock Insight:</b> {status}</div>
                <div class="product-sub"><b>Slow Moving:</b> {'Yes' if slow_moving else 'No'}</div>
                <div class="product-sub"><b>Replen Cls:</b> {replen_cls or 'N/A'}</div>
                <div class="product-sub"><b>Status Current:</b> {status_current or 'N/A'}</div>
                <div class="product-sub"><b>End Use Code:</b> {end_use_val or 'N/A'}</div>
                <div class="product-sub"><b>Manufacturer:</b> {manufacturer or 'N/A'}</div>
                <div class="product-sub"><b>Code:</b> {code_val or 'N/A'}</div>
                <div class="product-sub"><b>Comm Code:</b> {comm_code or 'N/A'}</div>
                <div class="product-sub"><b>Special Inst:</b> {special_inst or 'N/A'}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if user_role == "Warehouse Management View":
        status_current = safe_string(row.get(status_current_col, "")) if status_current_col else ""
        replen_cls = safe_string(row.get(replen_cls_col, "")) if replen_cls_col else ""
        manufacturer = safe_string(row.get(manufacturer_col, "")) if manufacturer_col else ""
        mfg_id = safe_string(row.get(mfg_id_col, "")) if mfg_id_col else ""
        mfg_item = safe_string(row.get(mfg_item_col, "")) if mfg_item_col else ""
        msds_val = safe_string(row.get(msds_col, "")) if msds_col else ""
        whmis_required = bool(row.get("WHMIS_Required", False))

        st.markdown(
            f"""
            <div class="detail-box">
                <div class="product-sub"><b>Location:</b> {location_val or 'N/A'}</div>
                <div class="product-sub"><b>Qty On Hand:</b> {int(qty_on_hand) if pd.notna(qty_on_hand) else 'N/A'}</div>
                <div class="product-sub"><b>Qty Avail:</b> {int(qty_avail) if pd.notna(qty_avail) else 'N/A'}</div>
                <div class="product-sub"><b>Stock Insight:</b> {status}</div>
                <div class="product-sub"><b>Status Current:</b> {status_current or 'N/A'}</div>
                <div class="product-sub"><b>Replen Cls:</b> {replen_cls or 'N/A'}</div>
                <div class="product-sub"><b>WHMIS Required:</b> {'Yes' if whmis_required else 'No'}</div>
                <div class="product-sub"><b>MSDS ID:</b> {msds_val or 'N/A'}</div>
                <div class="product-sub"><b>Manufacturer:</b> {manufacturer or 'N/A'}</div>
                <div class="product-sub"><b>Mfg ID:</b> {mfg_id or 'N/A'}</div>
                <div class="product-sub"><b>Mfg Itm ID:</b> {mfg_item or 'N/A'}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if user_role == "Business Unit View":
        max_qty = int(qty_avail) if pd.notna(qty_avail) and qty_avail > 0 else 0

        c1, c2 = st.columns([1, 1])
        with c1:
            qty_to_add = st.number_input(
                "Qty",
                min_value=1,
                max_value=max(1, max_qty) if max_qty > 0 else 1,
                value=1,
                step=1,
                key=f"qty_add_{idx_prefix}_{item_val}",
                disabled=(max_qty == 0),
            )

        with c2:
            if st.button("Add to cart", key=f"add_{idx_prefix}_{item_val}", disabled=(max_qty == 0)):
                ok, msg = add_to_cart(row, col_map, int(qty_to_add))
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

# =========================================================
# BUSINESS UNIT VIEW
# =========================================================
if is_business_unit_view:
    st.markdown('<div class="section-box"><div class="section-title">Business Unit Catalogue</div>', unsafe_allow_html=True)

    browse_df = filtered_df.head(30)
    if browse_df.empty:
        st.info("No items match the current filters.")
    else:
        browse_cols = st.columns(3)
        for i, (_, row) in enumerate(browse_df.iterrows()):
            with browse_cols[i % 3]:
                render_product_card(row, f"browse_{i}", user_role=user_role)

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# INTERNAL VIEW: INVENTORY PLANNING / WAREHOUSE MANAGEMENT
# =========================================================
if is_internal_view:
    internal_title = user_role
    st.markdown(f'<div class="section-box"><div class="section-title">{internal_title}</div>', unsafe_allow_html=True)

    sort_options = {
        "Inventory Planning View": ["Availability", "Avg Daily Usage", "Name", "Unit cost", "Days of Supply"],
        "Warehouse Management View": ["Availability", "Location", "Name", "Unit cost", "Days of Supply"],
    }

    internal_sort_option = st.selectbox(
        "Sort results by",
        sort_options[user_role]
    )

    internal_df = filtered_df.copy()

    if internal_sort_option == "Availability":
        internal_df = internal_df.sort_values(by="Qty_Avail_Num", ascending=False, na_position="last")
    elif internal_sort_option == "Avg Daily Usage":
        internal_df = internal_df.sort_values(by="Avg_Daily_Usage", ascending=False, na_position="last")
    elif internal_sort_option == "Days of Supply":
        internal_df = internal_df.sort_values(by="Days_of_Supply", ascending=True, na_position="last")
    elif internal_sort_option == "Location" and col_map.get("Location"):
        internal_df = internal_df.sort_values(by=col_map["Location"], ascending=True, na_position="last")
    elif internal_sort_option == "Name" and col_map.get("Name"):
        internal_df = internal_df.sort_values(by=col_map["Name"], ascending=True, na_position="last")
    elif internal_sort_option == "Unit cost" and col_map.get("Unit Cost"):
        cost_col = col_map["Unit Cost"]
        internal_df["_unit_cost_num"] = pd.to_numeric(internal_df[cost_col], errors="coerce")
        internal_df = internal_df.sort_values(by="_unit_cost_num", ascending=True, na_position="last")

    internal_results_to_show = st.selectbox(
        "Number of results to display",
        [12, 16, 20, 24, 28, 30, 40, 50, 75, 100],
        index=5,
        key=f"results_{user_role}"
    )

    internal_grid_rows = internal_df.head(internal_results_to_show)

    if internal_grid_rows.empty:
        st.info("No items match the current filters.")
    else:
        internal_cols = st.columns(3)
        for i, (_, row) in enumerate(internal_grid_rows.iterrows()):
            with internal_cols[i % 3]:
                render_product_card(row, f"internal_grid_{i}", user_role=user_role)

        remaining_results = len(internal_df) - len(internal_grid_rows)
        if remaining_results > 0:
            st.caption(
                f"Showing {len(internal_grid_rows)} of {len(internal_df)} results. "
                f"Refine filters or increase the display count to see more."
            )

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# INTERNAL IMAGE MANAGEMENT ONLY
# =========================================================
if is_internal_view:
    st.markdown('<div class="section-box"><div class="section-title">Internal Image Management</div>', unsafe_allow_html=True)
    st.caption("Images are read from GitHub. Changes made here affect only the current app session until you download the updated CSV and replace item_image_mapping.csv in GitHub.")

    img_item_col = col_map.get("Item")
    img_name_col = col_map.get("Name")

    image_admin_df = st.session_state.inventory_view.copy()

    if img_item_col and img_item_col in image_admin_df.columns:
        image_admin_df["_item_label"] = image_admin_df.apply(
            lambda r: f"{safe_string(r.get(img_item_col, ''))} - {safe_string(r.get(img_name_col, ''))}" if img_name_col else safe_string(r.get(img_item_col, '')),
            axis=1
        )

        item_options = image_admin_df["_item_label"].tolist()
        selected_item_label = st.selectbox("Select item to manage image", item_options)

        selected_row = image_admin_df[image_admin_df["_item_label"] == selected_item_label].iloc[0]
        selected_item_id = safe_string(selected_row.get(img_item_col, ""))
        current_image_url = st.session_state.get("image_lookup", {}).get(selected_item_id, "")

        c1, c2 = st.columns([1, 2])

        with c1:
            st.markdown("**Current image**")
            st.image(current_image_url or PLACEHOLDER_IMAGE_URL, use_container_width=True)

        with c2:
            new_image_url = st.text_input(
                "GitHub raw image URL",
                value=current_image_url,
                key=f"image_url_input_{selected_item_id}"
            )

            b1, b2, b3 = st.columns(3)

            with b1:
                if st.button("Save image mapping", key=f"save_image_mapping_{selected_item_id}"):
                    ok, msg = upsert_image_mapping(selected_item_id, new_image_url)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

            with b2:
                if st.button("Remove image mapping", key=f"remove_image_mapping_{selected_item_id}"):
                    ok, msg = remove_image_mapping(selected_item_id)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

            with b3:
                if st.button("Reload GitHub mappings", key="reload_github_mappings"):
                    load_image_map_from_github.clear()
                    st.session_state.image_map_df = load_image_map_from_github().copy()
                    sync_image_lookup()
                    st.success("Image mappings reloaded from GitHub.")
                    st.rerun()

            st.caption("Use raw GitHub image links, for example: https://raw.githubusercontent.com/.../images/item_100001.png")

    export_df = st.session_state.get("image_map_df", pd.DataFrame(columns=["Item", "image_url"])).copy()
    export_df = export_df.sort_values(by="Item", ascending=True, na_position="last")

    st.download_button(
        label="Download updated image mapping CSV",
        data=to_csv_bytes(export_df),
        file_name="item_image_mapping.csv",
        mime="text/csv",
    )

    with st.expander("Current image mappings"):
        if export_df.empty:
            st.info("No image mappings are currently loaded.")
        else:
            st.dataframe(export_df, use_container_width=True, height=250)

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# INTERNAL SUBMITTED REQUESTS VIEW
# =========================================================
if is_internal_view:
    st.markdown('<div class="section-box"><div class="section-title">Submitted Business Unit Requests</div>', unsafe_allow_html=True)

    if st.session_state.orders_log.empty:
        st.info("No business unit requests have been submitted in this session yet.")
    else:
        st.dataframe(st.session_state.orders_log, use_container_width=True, height=280)

        orders_xlsx = to_excel_bytes(st.session_state.orders_log.copy())
        st.download_button(
            label="Download Submitted Requests",
            data=orders_xlsx,
            file_name="submitted_business_unit_requests.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# RESET
# =========================================================
if st.button("Reset current uploaded session"):
    st.session_state.inventory_df = raw_df.copy()
    st.session_state.cart = {}
    st.session_state.orders_log = pd.DataFrame(
        columns=["Order Time", "Customer Name", "Department", "Item", "Description", "Order Qty"]
    )
    load_image_map_from_github.clear()
    st.session_state.image_map_df = load_image_map_from_github().copy()
    sync_image_lookup()
    refresh_inventory()
    st.success("Uploaded session inventory has been reset.")
    st.rerun()
