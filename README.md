# City of Calgary General Stores eCatalogue

## Overview
This repository contains a **Streamlit-based eCatalogue prototype** built for the **City of Calgary General Stores warehouse**.

The purpose of the app is to make warehouse inventory easier to access, search, and understand for different internal users. This prototype provides a more user-friendly catalogue interface with role-based views.

The app supports three main user views:

- **Business Unit View**  
  For internal business units acting as customers. Users can search items, browse availability, add items to a cart, and submit order requests.

- **Inventory Planning View**  
  For internal staff responsible for inventory requirements, replenishment strategy, stockout risk, and demand visibility.

- **Warehouse Management View**  
  For internal staff responsible for storage, layout, handling, available stock, and warehouse-side operational visibility.

---

## Project Objectives
The prototype was built to:

- improve inventory visibility across internal users
- provide a self-service catalogue for business units
- reduce time spent answering routine inventory questions manually
- support internal planning and warehouse decision-making
- create a foundation for future integration with live systems

---

## Main Features

### 1. Role-Based Views
The app separates functionality by user need:

#### Business Unit View
- search and filter available inventory
- view item details and availability
- add items to cart
- submit order requests by business unit
- read-only access to catalogue images and item data

#### Inventory Planning View
- view stockout risk and days of supply
- review replenishment class and planning-related fields
- identify slow-moving items
- review average daily usage
- manage image mappings for items

#### Warehouse Management View
- view location and available quantity
- review storage and handling-related inventory information
- review WHMIS / MSDS-related fields
- monitor warehouse-facing inventory details
- manage image mappings for items

---

### 2. Search and Filtering
Users can search the catalogue across multiple fields, including:
- item number
- description
- supplier
- manufacturer
- code
- location

Filters can be applied by:
- department
- supplier
- manufacturer
- status
- location
- low-stock condition

---

### 3. Inventory Metrics
The app calculates simple internal inventory indicators directly from the uploaded inventory file, such as:
- quantity on hand
- quantity available
- average daily usage
- days of supply
- stockout risk
- slow-moving inventory flags

These indicators are intended to support internal decision-making in a simple and transparent way.

---

### 4. Cart and Order Request Workflow
In the Business Unit View, users can:
- add available items to a cart
- adjust quantities
- enter requestor information
- select a department / business unit
- submit an order request

The prototype also includes a basic WHMIS confirmation step for items that require it.

---

### 5. Item Images
The app supports item images through a **GitHub-hosted image mapping file**.

Each item image is linked using a CSV file called:

```text
item_image_mapping.csv
```

This file maps an item number to an image URL.

Example format:

```csv
Item,image_url
100001,https://raw.githubusercontent.com/your-repo/main/images/item_100001.png
100002,https://raw.githubusercontent.com/your-repo/main/images/item_100002.png
```

If an item does not have an assigned image, the app uses a **placeholder image**.

---

## Data Source
The prototype uses an uploaded **PeopleSoft inventory Excel export** as its main input.

The code is designed to read and map expected inventory fields such as:
- Item
- Description
- Quantity On Hand
- Quantity Available
- Unit Cost
- Currency
- Vendor Name
- Manufacturer
- Replenishment Class
- Status Current
- Location
- MSDS ID
- Code

Because the app uses an uploaded file, the prototype can be refreshed with updated inventory data without changing the code.

---

## How the App Works

### Step 1: Upload Inventory File
The user uploads the latest PeopleSoft inventory Excel file when the app starts.

### Step 2: Load Image Mapping
The app loads `item_image_mapping.csv` from GitHub and uses it to match items to images.

### Step 3: Select View
The user chooses one of three views:
- Business Unit View
- Inventory Planning View
- Warehouse Management View

### Step 4: Search / Review / Order
Depending on the selected view, the user can either:
- browse and order items, or
- review internal inventory information and manage images

---

## Repository Setup

A typical repository structure is:

```text
your-repo/
│
├── app.py
├── README.md
├── requirements.txt
├── item_image_mapping.csv
└── images/
    ├── placeholder.png
    ├── item_100001.png
    ├── item_100002.png
    └── ...
```

You can rename `app.py` if your main Streamlit file uses a different name.

---

## Running the App Locally

### 1. Clone the repository
```bash
git clone <your-repository-url>
cd <your-repository-folder>
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Streamlit app
```bash
streamlit run app.py
```

If your main file has a different name, replace `app.py` with that filename.

---

## Suggested Requirements
A basic `requirements.txt` could include:

```text
streamlit
pandas
numpy
openpyxl
```

---

## How to Update Item Images

### For Internal Users
Only the two internal views are intended to manage image mappings:
- Inventory Planning View
- Warehouse Management View

### Current Image Workflow
1. Upload the item image to the repository's `images/` folder.
2. Add or update the item in `item_image_mapping.csv`.
3. Commit the updated CSV and image file to GitHub.
4. Restart or refresh the app if needed.

### Important Note
The current app can **read images from GitHub**, but it does **not directly write changes back to GitHub automatically**.

If image mappings are changed inside the app during a session, those updates should be:
1. downloaded from the app, and then
2. manually uploaded to GitHub to replace the existing `item_image_mapping.csv`

---

## Permissions / Intended Use

### Business Unit View
- can browse catalogue items
- can search and filter
- can add items to cart
- can submit requests
- cannot manage image mappings
- cannot change internal inventory settings

### Internal Views
- can review deeper operational inventory information
- can manage item image mappings
- are intended for planning and warehouse staff only

---

## Prototype Limitations
This project is a **prototype**, not a production system.

Current limitations include:
- uses uploaded Excel exports instead of live PeopleSoft integration
- does not write directly back to PeopleSoft
- image updates are not automatically pushed to GitHub
- forecasting logic is intentionally lightweight
- advanced statistical forecasting was limited by available historical transaction data

---

## Future Improvements
Potential future enhancements include:
- live integration with PeopleSoft or another inventory database
- user authentication and access control
- automatic write-back of image mappings to GitHub or cloud storage
- stronger forecasting models using cleaner historical demand data
- dashboards for warehouse capacity, service levels, and reporting
- direct workflow integration for approvals and request tracking

---

## Handoff Notes
This repository is intended to be understandable for future users, reviewers, and internal handoff.

When handing off this code, make sure to also provide:
- the main Streamlit app file
- `requirements.txt`
- `item_image_mapping.csv`
- the `images/` folder
- a sample PeopleSoft inventory Excel file for testing
- any presentation or documentation that explains the prototype context

---

## Summary
This project demonstrates how a simple web app can improve inventory visibility and internal ordering workflows for the City of Calgary General Stores warehouse.

It combines:
- a customer-style catalogue for business units
- internal operational views for planning and warehouse staff
- lightweight inventory analytics
- GitHub-hosted item images
- a flexible structure for future system integration
