"""Restaurant Inventory & Recipe Pricing – Streamlit App."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from database import (
    init_db,
    seed_default_categories,
    get_categories,
    add_category,
    get_inventory,
    add_inventory_item,
    update_inventory_item,
    delete_inventory_item,
    get_recipes,
    add_recipe,
    update_recipe,
    delete_recipe,
    get_recipe_ingredients,
    set_recipe_ingredients,
    get_recipe_cost,
    get_low_stock_items,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Restaurant Inventory & Recipes",
    page_icon="🍽️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Database bootstrap
# ---------------------------------------------------------------------------
init_db()
seed_default_categories()

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
st.sidebar.title("🍽️ Restaurant Manager")
page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Inventory", "Recipes", "Categories"],
)

# =====================================================================
# DASHBOARD
# =====================================================================
if page == "Dashboard":
    st.title("Dashboard")

    inventory = get_inventory()
    recipes = get_recipes()
    low_stock = get_low_stock_items()

    # KPI row
    col1, col2, col3, col4 = st.columns(4)
    total_value = sum(i["quantity"] * i["cost_per_unit"] for i in inventory)
    col1.metric("Inventory Items", len(inventory))
    col2.metric("Total Inventory Value", f"${total_value:,.2f}")
    col3.metric("Recipes", len(recipes))
    col4.metric("Low-Stock Alerts", len(low_stock), delta=None)

    st.divider()

    # Low-stock alerts
    if low_stock:
        st.subheader("⚠️ Low-Stock Alerts")
        low_df = pd.DataFrame(low_stock)
        low_df = low_df.rename(
            columns={
                "name": "Item",
                "category": "Category",
                "quantity": "In Stock",
                "unit": "Unit",
                "min_stock_level": "Min Level",
                "supplier": "Supplier",
            }
        )
        st.dataframe(
            low_df[["Item", "Category", "In Stock", "Unit", "Min Level", "Supplier"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("All inventory items are above minimum stock levels.")

    st.divider()

    left, right = st.columns(2)

    # Inventory value by category
    with left:
        st.subheader("Inventory Value by Category")
        if inventory:
            df = pd.DataFrame(inventory)
            df["value"] = df["quantity"] * df["cost_per_unit"]
            cat_value = (
                df.groupby("category", dropna=False)["value"].sum().reset_index()
            )
            cat_value.columns = ["Category", "Value"]
            fig = px.pie(
                cat_value,
                names="Category",
                values="Value",
                hole=0.4,
            )
            fig.update_traces(textinfo="label+percent")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No inventory items yet.")

    # Recipe profitability
    with right:
        st.subheader("Recipe Profitability")
        if recipes:
            rows = []
            for r in recipes:
                cost = get_recipe_cost(r["id"])
                margin = r["selling_price"] - cost if r["selling_price"] else 0
                pct = (margin / r["selling_price"] * 100) if r["selling_price"] else 0
                rows.append(
                    {
                        "Recipe": r["name"],
                        "Cost": cost,
                        "Price": r["selling_price"],
                        "Margin": margin,
                        "Margin %": pct,
                    }
                )
            prof_df = pd.DataFrame(rows)
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    name="Cost",
                    x=prof_df["Recipe"],
                    y=prof_df["Cost"],
                    marker_color="#ef553b",
                )
            )
            fig.add_trace(
                go.Bar(
                    name="Margin",
                    x=prof_df["Recipe"],
                    y=prof_df["Margin"],
                    marker_color="#00cc96",
                )
            )
            fig.update_layout(barmode="stack", yaxis_title="$")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No recipes yet.")

# =====================================================================
# INVENTORY
# =====================================================================
elif page == "Inventory":
    st.title("Inventory Management")

    categories = get_categories()
    cat_map = {c["name"]: c["id"] for c in categories}
    cat_names = list(cat_map.keys())

    # --- Add new item ---
    with st.expander("➕ Add New Inventory Item", expanded=False):
        with st.form("add_item_form", clear_on_submit=True):
            cols = st.columns([2, 1, 1, 1])
            new_name = cols[0].text_input("Item Name*")
            new_cat = cols[1].selectbox("Category", cat_names, key="add_cat")
            new_qty = cols[2].number_input(
                "Quantity", min_value=0.0, value=0.0, step=0.5, key="add_qty"
            )
            new_unit = cols[3].text_input("Unit (e.g. kg, L, pcs)", key="add_unit")

            cols2 = st.columns([1, 1, 2])
            new_cost = cols2[0].number_input(
                "Cost per Unit ($)", min_value=0.0, value=0.0, step=0.01, key="add_cost"
            )
            new_min = cols2[1].number_input(
                "Min Stock Level", min_value=0.0, value=0.0, step=0.5, key="add_min"
            )
            new_supplier = cols2[2].text_input("Supplier", key="add_supplier")

            submitted = st.form_submit_button("Add Item")
            if submitted:
                if not new_name.strip():
                    st.error("Item name is required.")
                elif not new_unit.strip():
                    st.error("Unit is required.")
                else:
                    add_inventory_item(
                        new_name.strip(),
                        cat_map[new_cat],
                        new_qty,
                        new_unit.strip(),
                        new_cost,
                        new_min,
                        new_supplier.strip(),
                    )
                    st.success(f"Added **{new_name}**.")
                    st.rerun()

    # --- Filter & display ---
    st.subheader("Current Stock")
    inventory = get_inventory()

    if inventory:
        filter_col1, filter_col2 = st.columns([1, 3])
        with filter_col1:
            filter_cat = st.selectbox(
                "Filter by Category", ["All"] + cat_names, key="filter_cat"
            )
        with filter_col2:
            search = st.text_input("Search items", key="search_inv")

        filtered = inventory
        if filter_cat != "All":
            filtered = [i for i in filtered if i["category"] == filter_cat]
        if search:
            filtered = [i for i in filtered if search.lower() in i["name"].lower()]

        if filtered:
            df = pd.DataFrame(filtered)
            df["value"] = df["quantity"] * df["cost_per_unit"]
            display_df = df.rename(
                columns={
                    "name": "Item",
                    "category": "Category",
                    "quantity": "In Stock",
                    "unit": "Unit",
                    "cost_per_unit": "Cost/Unit ($)",
                    "min_stock_level": "Min Level",
                    "supplier": "Supplier",
                    "value": "Total Value ($)",
                }
            )
            st.dataframe(
                display_df[
                    [
                        "Item",
                        "Category",
                        "In Stock",
                        "Unit",
                        "Cost/Unit ($)",
                        "Min Level",
                        "Supplier",
                        "Total Value ($)",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No items match your filter.")

        # --- Edit / Delete ---
        st.subheader("Edit or Delete Items")
        item_names = {i["name"]: i for i in inventory}
        selected_name = st.selectbox(
            "Select item to edit", list(item_names.keys()), key="edit_select"
        )
        if selected_name:
            item = item_names[selected_name]
            with st.form("edit_item_form"):
                ecols = st.columns([2, 1, 1, 1])
                e_name = ecols[0].text_input("Name", value=item["name"])
                e_cat_idx = (
                    cat_names.index(item["category"])
                    if item["category"] in cat_names
                    else 0
                )
                e_cat = ecols[1].selectbox(
                    "Category", cat_names, index=e_cat_idx, key="edit_cat"
                )
                e_qty = ecols[2].number_input(
                    "Quantity",
                    value=float(item["quantity"]),
                    min_value=0.0,
                    step=0.5,
                    key="edit_qty",
                )
                e_unit = ecols[3].text_input(
                    "Unit", value=item["unit"], key="edit_unit"
                )

                ecols2 = st.columns([1, 1, 2])
                e_cost = ecols2[0].number_input(
                    "Cost/Unit ($)",
                    value=float(item["cost_per_unit"]),
                    min_value=0.0,
                    step=0.01,
                    key="edit_cost",
                )
                e_min = ecols2[1].number_input(
                    "Min Stock",
                    value=float(item["min_stock_level"]),
                    min_value=0.0,
                    step=0.5,
                    key="edit_min",
                )
                e_supplier = ecols2[2].text_input(
                    "Supplier", value=item["supplier"] or "", key="edit_supplier"
                )

                btn_col1, btn_col2 = st.columns(2)
                save = btn_col1.form_submit_button("Save Changes")
                delete = btn_col2.form_submit_button("🗑️ Delete Item")

                if save:
                    update_inventory_item(
                        item["id"],
                        e_name.strip(),
                        cat_map[e_cat],
                        e_qty,
                        e_unit.strip(),
                        e_cost,
                        e_min,
                        e_supplier.strip(),
                    )
                    st.success("Item updated.")
                    st.rerun()
                if delete:
                    delete_inventory_item(item["id"])
                    st.success("Item deleted.")
                    st.rerun()
    else:
        st.info("No inventory items yet. Add your first item above!")

# =====================================================================
# RECIPES
# =====================================================================
elif page == "Recipes":
    st.title("Recipe Management & Pricing")

    inventory = get_inventory()
    recipes = get_recipes()

    tab_list, tab_add = st.tabs(["📋 Recipe List", "➕ New Recipe"])

    # --- Recipe list ---
    with tab_list:
        if recipes:
            for r in recipes:
                cost = get_recipe_cost(r["id"])
                margin = r["selling_price"] - cost
                margin_pct = (
                    (margin / r["selling_price"] * 100) if r["selling_price"] else 0
                )

                with st.expander(
                    f"**{r['name']}** — Sells for ${r['selling_price']:.2f}  |  Cost ${cost:.2f}  |  Margin {margin_pct:.1f}%"
                ):
                    st.write(r["description"] or "_No description._")

                    ingredients = get_recipe_ingredients(r["id"])
                    if ingredients:
                        ing_rows = []
                        can_make = float("inf")
                        for ing in ingredients:
                            line_cost = ing["quantity_needed"] * ing["cost_per_unit"]
                            servings = (
                                ing["in_stock"] / ing["quantity_needed"]
                                if ing["quantity_needed"] > 0
                                else float("inf")
                            )
                            can_make = min(can_make, servings)
                            ing_rows.append(
                                {
                                    "Ingredient": ing["ingredient_name"],
                                    "Needed": ing["quantity_needed"],
                                    "Unit": ing["unit"],
                                    "In Stock": ing["in_stock"],
                                    "Cost/Unit ($)": ing["cost_per_unit"],
                                    "Line Cost ($)": round(line_cost, 2),
                                }
                            )
                        ing_df = pd.DataFrame(ing_rows)
                        st.dataframe(ing_df, use_container_width=True, hide_index=True)

                        can_make = int(can_make) if can_make != float("inf") else 0
                        st.info(
                            f"Based on current stock, you can make **{can_make}** servings of this recipe."
                        )
                    else:
                        st.warning("No ingredients assigned yet.")

                    # Summary metrics
                    mc1, mc2, mc3 = st.columns(3)
                    mc1.metric("Ingredient Cost", f"${cost:.2f}")
                    mc2.metric("Selling Price", f"${r['selling_price']:.2f}")
                    color = "normal" if margin >= 0 else "inverse"
                    mc3.metric(
                        "Profit Margin",
                        f"${margin:.2f}",
                        delta=f"{margin_pct:.1f}%",
                        delta_color=color,
                    )

                    st.divider()

                    # Edit recipe
                    with st.form(f"edit_recipe_{r['id']}"):
                        st.subheader("Edit Recipe")
                        er_name = st.text_input(
                            "Recipe Name", value=r["name"], key=f"er_name_{r['id']}"
                        )
                        er_desc = st.text_area(
                            "Description",
                            value=r["description"] or "",
                            key=f"er_desc_{r['id']}",
                        )
                        er_price = st.number_input(
                            "Selling Price ($)",
                            value=float(r["selling_price"]),
                            min_value=0.0,
                            step=0.5,
                            key=f"er_price_{r['id']}",
                        )

                        st.markdown("**Ingredients** — select items and quantities:")
                        inv_names = [i["name"] for i in inventory]
                        inv_map = {i["name"]: i["id"] for i in inventory}
                        current_ing_ids = (
                            {ing["inventory_id"] for ing in ingredients}
                            if ingredients
                            else set()
                        )

                        selected_ingredients = st.multiselect(
                            "Select ingredients",
                            inv_names,
                            default=[i["ingredient_name"] for i in ingredients]
                            if ingredients
                            else [],
                            key=f"er_ing_{r['id']}",
                        )
                        qty_map_existing = (
                            {
                                ing["ingredient_name"]: ing["quantity_needed"]
                                for ing in ingredients
                            }
                            if ingredients
                            else {}
                        )
                        new_ings = []
                        for si in selected_ingredients:
                            default_qty = qty_map_existing.get(si, 1.0)
                            q = st.number_input(
                                f"Qty of {si}",
                                value=default_qty,
                                min_value=0.01,
                                step=0.25,
                                key=f"er_iq_{r['id']}_{si}",
                            )
                            new_ings.append(
                                {"inventory_id": inv_map[si], "quantity_needed": q}
                            )

                        bcol1, bcol2 = st.columns(2)
                        save_recipe = bcol1.form_submit_button("Save Recipe")
                        del_recipe = bcol2.form_submit_button("🗑️ Delete Recipe")

                        if save_recipe:
                            update_recipe(
                                r["id"], er_name.strip(), er_desc.strip(), er_price
                            )
                            set_recipe_ingredients(r["id"], new_ings)
                            st.success("Recipe updated.")
                            st.rerun()
                        if del_recipe:
                            delete_recipe(r["id"])
                            st.success("Recipe deleted.")
                            st.rerun()
        else:
            st.info(
                "No recipes yet. Create your first recipe in the **New Recipe** tab."
            )

    # --- Add new recipe ---
    with tab_add:
        if not inventory:
            st.warning(
                "You need inventory items before creating recipes. Go to the **Inventory** page first."
            )
        else:
            with st.form("add_recipe_form", clear_on_submit=True):
                st.subheader("Create New Recipe")
                nr_name = st.text_input("Recipe Name*")
                nr_desc = st.text_area("Description")
                nr_price = st.number_input(
                    "Selling Price ($)", min_value=0.0, value=0.0, step=0.5
                )

                st.markdown("**Ingredients**")
                inv_names = [i["name"] for i in inventory]
                inv_map = {i["name"]: i["id"] for i in inventory}
                selected = st.multiselect(
                    "Select ingredients", inv_names, key="nr_ings"
                )
                ing_list = []
                for s in selected:
                    q = st.number_input(
                        f"Qty of {s}",
                        min_value=0.01,
                        value=1.0,
                        step=0.25,
                        key=f"nr_q_{s}",
                    )
                    ing_list.append({"inventory_id": inv_map[s], "quantity_needed": q})

                create = st.form_submit_button("Create Recipe")
                if create:
                    if not nr_name.strip():
                        st.error("Recipe name is required.")
                    else:
                        rid = add_recipe(nr_name.strip(), nr_desc.strip(), nr_price)
                        if ing_list:
                            set_recipe_ingredients(rid, ing_list)
                        st.success(f"Created recipe **{nr_name}**!")
                        st.rerun()

# =====================================================================
# CATEGORIES
# =====================================================================
elif page == "Categories":
    st.title("Ingredient Categories")
    categories = get_categories()

    with st.form("add_cat_form", clear_on_submit=True):
        new_cat = st.text_input("New Category Name")
        if st.form_submit_button("Add Category"):
            if new_cat.strip():
                try:
                    add_category(new_cat.strip())
                    st.success(f"Added category **{new_cat}**.")
                    st.rerun()
                except Exception:
                    st.error("Category already exists.")
            else:
                st.error("Name cannot be empty.")

    st.subheader("Existing Categories")
    if categories:
        df = pd.DataFrame(categories)
        df = df.rename(columns={"name": "Category Name"})
        st.dataframe(df[["Category Name"]], use_container_width=True, hide_index=True)
    else:
        st.info("No categories yet.")
