# Restaurant Inventory & Recipe Pricing

A Streamlit application for restaurants to manage inventory stock levels and calculate recipe pricing.

## Features

- **Dashboard** — Overview of inventory value, low-stock alerts, and recipe profitability charts
- **Inventory Management** — Add, edit, delete, search, and filter stock items by category
- **Recipe Management** — Create recipes with ingredients from inventory, auto-calculate cost, margin, and servings possible from current stock
- **Categories** — Manage ingredient categories

## Getting Started

### Prerequisites

- Python 3.10+

### Installation

```bash
pip install -r requirements.txt
```

### Running the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

## Data Storage

The app uses a local SQLite database (`restaurant_inventory.db`) created automatically on first run.
