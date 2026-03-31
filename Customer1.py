#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import pandas as pd
import numpy as np
import re
import openpyxl
# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="City of Calgary General Stores",
    page_icon="🛒",
    layout="wide",
)

# =========================================================
# DATA SOURCE
# =========================================================
DATA_URL = "https://raw.githubusercontent.com/PrinceKafeke/CityofCalgaryeCatalogue/main/City%20of%20Calgary%20-%20790IN%20Inventory%20Data%20-%20Copy.xlsx"
LOGO_URL = "https://raw.githubusercontent.com/PrinceKafeke/CityofCalgaryeCatalogue/main/calgary_logo.png"

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
        min-height: 170px;
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
    if "low" in s or "risk" in s:
        return '<span class="pill pill-red">Low Stock</span>'
    return '<span class="pill pill-grey">Unknown</span>'

def compute_inventory_metrics(df, col_map):
    out = df.copy()

    qty_col = col_map.get("Qty On Hand")
    avail_col = col_map.get("Qty Avail")
    usage_col = col_map.get("Curr Year Usage")

    if qty_col and qty_col in out.columns:
        out["Qty_On_Hand_Num"] = pd.to_numeric(out[qty_col], errors="coerce")
    else:
        out["Qty_On_Hand_Num"] = np.nan

    if avail_col and avail_col in out.columns:
        out["Qty_Avail_Num"] = pd.to_numeric(out[avail_col], errors="coerce")
    else:
        out["Qty_Avail_Num"] = out["Qty_On_Hand_Num"]

    if usage_col and usage_col in out.columns:
        out["Forecast_Demand"] = pd.to_numeric(out[usage_col], errors="coerce") / 365.0
    else:
        out["Forecast_Demand"] = np.nan

    out["Days_of_Supply"] = np.where(
        (out["Forecast_Demand"] > 0) & out["Qty_On_Hand_Num"].notna(),
        out["Qty_On_Hand_Num"] / out["Forecast_Demand"],
        np.nan,
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
    available = 0 if pd.isna(available) else int(available)

    current_in_cart = st.session_state.cart.get(item_id, {}).get("qty", 0)

    if qty_to_add <= 0:
        return False, "Quantity must be positive."

    if current_in_cart + qty_to_add > available:
        return False, f"Only {available} unit(s) available."

    unit_cost = np.nan
    if unit_cost_col and unit_cost_col in row.index:
        unit_cost = pd.to_numeric(pd.Series([row.get(unit_cost_col, np.nan)]), errors="coerce").iloc[0]

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

def checkout_cart(customer_name, department, col_map):
    if not st.session_state.cart:
        return False, "Cart is empty."

    item_col = col_map.get("Item")
    qty_col = col_map.get("Qty On Hand")
    avail_col = col_map.get("Qty Avail")
    name_col = col_map.get("Name")

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

@st.cache_data(show_spinner=False)
def load_inventory():
    return pd.read_excel(DATA_URL)

# =========================================================
# LOAD DATA
# =========================================================
try:
    raw_df = load_inventory()
except Exception as e:
    st.error(f"Could not load Excel file from GitHub: {e}")
    st.stop()

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
}

col_map = build_col_map(raw_df, expected_cols)

# =========================================================
# SESSION STATE
# =========================================================
if "inventory_df" not in st.session_state:
    st.session_state.inventory_df = raw_df.copy()

if "cart" not in st.session_state:
    st.session_state.cart = {}

if "orders_log" not in st.session_state:
    st.session_state.orders_log = pd.DataFrame(
        columns=["Order Time", "Customer Name", "Department", "Item", "Description", "Order Qty"]
    )

def refresh_inventory():
    st.session_state.inventory_view = compute_inventory_metrics(
        st.session_state.inventory_df.copy(),
        col_map
    )

refresh_inventory()
df = st.session_state.inventory_view

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
            <div class="header-subtitle">Business unit self-service ordering catalogue</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
    search_text = st.text_input("Search catalogue", placeholder="Search warehouse inventory")

with top_right:
    selected_supplier = st.selectbox("Supplier", all_vendors)

# =========================================================
# HERO
# =========================================================
st.markdown(
    """
    <div class="hero">
        <div class="hero-title">Support business unit ordering<br>with faster inventory access</div>
        <div class="hero-sub">Browse General Stores inventory, compare availability, add items to cart, and submit requests by department or business unit.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# FILTER DATA
# =========================================================
filtered_df = df.copy()

if selected_category != "All Departments" and category_col and category_col in filtered_df.columns:
    filtered_df = filtered_df[filtered_df[category_col].astype(str) == selected_category]

if selected_supplier != "All Suppliers" and vendor_col and vendor_col in filtered_df.columns:
    filtered_df = filtered_df[filtered_df[vendor_col].astype(str) == selected_supplier]

tokens = tokenize_search(search_text)
if tokens:
    search_cols = []
    for logical in ["Item", "Name", "Category", "Vendor Name", "Location"]:
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
# SIDEBAR CART
# =========================================================
st.sidebar.header("🛒 Cart Summary")
st.sidebar.metric("Items in Cart", cart_total_items(st.session_state.cart))
st.sidebar.metric("Estimated Value", f"{cart_total_value(st.session_state.cart):,.2f}")

if st.session_state.cart:
    st.sidebar.markdown("---")
    for item_id, cart_item in st.session_state.cart.items():
        st.sidebar.markdown(f"**{cart_item['name'] or item_id}**")
        st.sidebar.caption(f"Item: {item_id}")
        st.sidebar.caption(f"Qty: {cart_item['qty']}")
        if st.sidebar.button("Remove", key=f"sidebar_remove_{item_id}"):
            remove_from_cart(item_id)
            st.rerun()
else:
    st.sidebar.info("Your cart is empty.")

# =========================================================
# METRICS
# =========================================================
low_stock_count = int((filtered_df["Stock_Status"] == "Low / Risk of Stockout").sum())

m1, m2, m3 = st.columns(3)
m1.metric("Items Shown", len(filtered_df))
m2.metric("Low Stock", low_stock_count)
m3.metric("Cart Items", cart_total_items(st.session_state.cart))

# =========================================================
# MAIN CART SECTION
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
    "Other"
]

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
        customer_name = st.text_input("Requestor name", key="main_cart_requestor")
    with c2:
        department_name = st.selectbox(
            "Department / Business Unit",
            BUSINESS_UNITS,
            key="main_cart_department"
        )

    if st.button("Submit order request", key="main_submit_order"):
        if not safe_string(customer_name):
            st.warning("Please enter the requestor name.")
        else:
            ok, msg = checkout_cart(customer_name, department_name, col_map)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# SECTION DATA
# =========================================================
featured_df = filtered_df.sort_values(
    by=["Qty_Avail_Num", "Forecast_Demand"],
    ascending=[False, False],
    na_position="last"
).head(8)

popular_df = filtered_df.sort_values(
    by="Forecast_Demand",
    ascending=False,
    na_position="last"
).head(8)

low_df = filtered_df[filtered_df["Stock_Status"] == "Low / Risk of Stockout"].copy()

# =========================================================
# PRODUCT CARD RENDERER
# =========================================================
def render_product_card(row, idx_prefix):
    item_col = col_map.get("Item")
    name_col = col_map.get("Name")
    category_col = col_map.get("Category")
    vendor_col = col_map.get("Vendor Name")
    unit_cost_col = col_map.get("Unit Cost")
    currency_col = col_map.get("Currency")
    location_col = col_map.get("Location")
    uom_col = col_map.get("Std UOM")

    item_val = safe_string(row.get(item_col, "")) if item_col else ""
    name_val = safe_string(row.get(name_col, "")) if name_col else ""
    category_val = safe_string(row.get(category_col, "")) if category_col else ""
    vendor_val = safe_string(row.get(vendor_col, "")) if vendor_col else ""
    location_val = safe_string(row.get(location_col, "")) if location_col else ""
    uom_val = safe_string(row.get(uom_col, "")) if uom_col else ""
    qty_avail = row.get("Qty_Avail_Num", np.nan)
    status = row.get("Stock_Status", "Unknown")
    unit_cost = row.get(unit_cost_col, "") if unit_cost_col else ""
    currency = safe_string(row.get(currency_col, "")) if currency_col else ""

    icon = category_icon(category_val)

    st.markdown(
        f"""
        <div class="product-card">
            <div class="product-title">{icon} {name_val or item_val or "Unnamed Item"}</div>
            <div class="product-sub"><b>Item:</b> {item_val or "N/A"}</div>
            <div class="product-sub"><b>Category:</b> {category_val or "N/A"}</div>
            <div class="product-sub"><b>Supplier:</b> {vendor_val or "N/A"}</div>
            <div class="product-sub"><b>Available:</b> {int(qty_avail) if pd.notna(qty_avail) else "N/A"} {uom_val}</div>
            <div class="product-sub"><b>Location:</b> {location_val or "N/A"}</div>
            <div class="product-sub"><b>Unit Cost:</b> {currency} {unit_cost}</div>
            <div>{stock_badge_html(status)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
# HOME SECTIONS
# =========================================================
left_col, right_col = st.columns(2)

with left_col:
    st.markdown('<div class="section-box"><div class="section-title">Featured inventory</div>', unsafe_allow_html=True)
    for i, (_, row) in enumerate(featured_df.head(4).iterrows()):
        render_product_card(row, f"featured_left_{i}")
    st.markdown("</div>", unsafe_allow_html=True)

with right_col:
    st.markdown('<div class="section-box"><div class="section-title">High-demand items</div>', unsafe_allow_html=True)
    for i, (_, row) in enumerate(popular_df.head(4).iterrows()):
        render_product_card(row, f"popular_right_{i}")
    st.markdown("</div>", unsafe_allow_html=True)

low_col, browse_col = st.columns(2)

with low_col:
    st.markdown('<div class="section-box"><div class="section-title">Low stock attention items</div>', unsafe_allow_html=True)
    if low_df.empty:
        st.info("No low-stock items in the current filter view.")
    else:
        for i, (_, row) in enumerate(low_df.head(4).iterrows()):
            render_product_card(row, f"low_{i}")
    st.markdown("</div>", unsafe_allow_html=True)

with browse_col:
    st.markdown('<div class="section-box"><div class="section-title">Browse by department result set</div>', unsafe_allow_html=True)
    browse_df = filtered_df.head(4)
    if browse_df.empty:
        st.info("No items match the current filters.")
    else:
        for i, (_, row) in enumerate(browse_df.iterrows()):
            render_product_card(row, f"browse_{i}")
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# FULL CATALOGUE
# =========================================================
st.markdown('<div class="section-box"><div class="section-title">Catalogue results</div>', unsafe_allow_html=True)

sort_option = st.selectbox(
    "Sort results by",
    ["Availability", "Demand rate", "Name", "Unit cost"]
)

catalogue_df = filtered_df.copy()

if sort_option == "Availability":
    catalogue_df = catalogue_df.sort_values(by="Qty_Avail_Num", ascending=False, na_position="last")
elif sort_option == "Demand rate":
    catalogue_df = catalogue_df.sort_values(by="Forecast_Demand", ascending=False, na_position="last")
elif sort_option == "Name" and col_map.get("Name"):
    catalogue_df = catalogue_df.sort_values(by=col_map["Name"], ascending=True, na_position="last")
elif sort_option == "Unit cost" and col_map.get("Unit Cost"):
    cost_col = col_map["Unit Cost"]
    catalogue_df["_unit_cost_num"] = pd.to_numeric(catalogue_df[cost_col], errors="coerce")
    catalogue_df = catalogue_df.sort_values(by="_unit_cost_num", ascending=True, na_position="last")

results_to_show = st.selectbox("Number of results to display", [8, 12, 16, 24], index=1)
grid_rows = catalogue_df.head(results_to_show)

if grid_rows.empty:
    st.info("No items match the current filters.")
else:
    cols = st.columns(4)
    for i, (_, row) in enumerate(grid_rows.iterrows()):
        with cols[i % 4]:
            render_product_card(row, f"grid_{i}")

st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# ORDER HISTORY
# =========================================================
with st.expander("View submitted customer orders"):
    if st.session_state.orders_log.empty:
        st.info("No orders have been submitted in this session yet.")
    else:
        st.dataframe(st.session_state.orders_log, use_container_width=True, height=280)

# =========================================================
# RESET
# =========================================================
if st.button("Reset prototype inventory"):
    st.session_state.inventory_df = raw_df.copy()
    st.session_state.cart = {}
    st.session_state.orders_log = pd.DataFrame(
        columns=["Order Time", "Customer Name", "Department", "Item", "Description", "Order Qty"]
    )
    refresh_inventory()
    st.success("Prototype inventory has been reset.")
    st.rerun()

