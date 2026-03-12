"""Database module for restaurant inventory and recipe management."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path("restaurant_inventory.db")


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database tables."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_id INTEGER,
                quantity REAL NOT NULL DEFAULT 0,
                unit TEXT NOT NULL,
                cost_per_unit REAL NOT NULL DEFAULT 0,
                min_stock_level REAL NOT NULL DEFAULT 0,
                supplier TEXT DEFAULT '',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            );

            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                selling_price REAL NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS recipe_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                inventory_id INTEGER NOT NULL,
                quantity_needed REAL NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
                FOREIGN KEY (inventory_id) REFERENCES inventory(id)
            );
        """)


def seed_default_categories():
    """Insert default categories if the table is empty."""
    defaults = [
        "Proteins",
        "Vegetables",
        "Fruits",
        "Dairy",
        "Grains & Starches",
        "Spices & Seasonings",
        "Oils & Fats",
        "Beverages",
        "Sauces & Condiments",
        "Other",
    ]
    with get_connection() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        if existing == 0:
            conn.executemany(
                "INSERT INTO categories (name) VALUES (?)",
                [(c,) for c in defaults],
            )


# --- Category operations ---


def get_categories():
    """Return all categories as a list of dicts."""
    with get_connection() as conn:
        rows = conn.execute("SELECT id, name FROM categories ORDER BY name").fetchall()
        return [dict(r) for r in rows]


def add_category(name: str):
    """Add a new category."""
    with get_connection() as conn:
        conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))


# --- Inventory operations ---


def get_inventory():
    """Return all inventory items joined with category names."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT i.id, i.name, c.name as category, i.quantity, i.unit,
                   i.cost_per_unit, i.min_stock_level, i.supplier, i.updated_at,
                   i.category_id
            FROM inventory i
            LEFT JOIN categories c ON i.category_id = c.id
            ORDER BY i.name
        """).fetchall()
        return [dict(r) for r in rows]


def add_inventory_item(
    name: str,
    category_id: int,
    quantity: float,
    unit: str,
    cost_per_unit: float,
    min_stock_level: float,
    supplier: str,
):
    """Add a new inventory item."""
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO inventory
               (name, category_id, quantity, unit, cost_per_unit, min_stock_level, supplier)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                name,
                category_id,
                quantity,
                unit,
                cost_per_unit,
                min_stock_level,
                supplier,
            ),
        )


def update_inventory_item(
    item_id: int,
    name: str,
    category_id: int,
    quantity: float,
    unit: str,
    cost_per_unit: float,
    min_stock_level: float,
    supplier: str,
):
    """Update an existing inventory item."""
    with get_connection() as conn:
        conn.execute(
            """UPDATE inventory
               SET name=?, category_id=?, quantity=?, unit=?, cost_per_unit=?,
                   min_stock_level=?, supplier=?, updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (
                name,
                category_id,
                quantity,
                unit,
                cost_per_unit,
                min_stock_level,
                supplier,
                item_id,
            ),
        )


def delete_inventory_item(item_id: int):
    """Delete an inventory item."""
    with get_connection() as conn:
        conn.execute("DELETE FROM inventory WHERE id=?", (item_id,))


# --- Recipe operations ---


def get_recipes():
    """Return all recipes."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, description, selling_price, created_at FROM recipes ORDER BY name"
        ).fetchall()
        return [dict(r) for r in rows]


def get_recipe_by_id(recipe_id: int):
    """Return a single recipe by ID."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, description, selling_price FROM recipes WHERE id=?",
            (recipe_id,),
        ).fetchone()
        return dict(row) if row else None


def add_recipe(name: str, description: str, selling_price: float):
    """Add a new recipe and return its ID."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO recipes (name, description, selling_price) VALUES (?, ?, ?)",
            (name, description, selling_price),
        )
        return cursor.lastrowid


def update_recipe(recipe_id: int, name: str, description: str, selling_price: float):
    """Update an existing recipe."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE recipes SET name=?, description=?, selling_price=? WHERE id=?",
            (name, description, selling_price, recipe_id),
        )


def delete_recipe(recipe_id: int):
    """Delete a recipe (cascade deletes ingredients)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM recipes WHERE id=?", (recipe_id,))


# --- Recipe ingredient operations ---


def get_recipe_ingredients(recipe_id: int):
    """Return ingredients for a recipe with inventory details."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT ri.id, ri.inventory_id, ri.quantity_needed,
                      i.name as ingredient_name, i.unit, i.cost_per_unit, i.quantity as in_stock
               FROM recipe_ingredients ri
               JOIN inventory i ON ri.inventory_id = i.id
               WHERE ri.recipe_id = ?
               ORDER BY i.name""",
            (recipe_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def set_recipe_ingredients(recipe_id: int, ingredients: list[dict]):
    """Replace all ingredients for a recipe.

    Each ingredient dict should have 'inventory_id' and 'quantity_needed'.
    """
    with get_connection() as conn:
        conn.execute("DELETE FROM recipe_ingredients WHERE recipe_id=?", (recipe_id,))
        conn.executemany(
            """INSERT INTO recipe_ingredients (recipe_id, inventory_id, quantity_needed)
               VALUES (?, ?, ?)""",
            [
                (recipe_id, ing["inventory_id"], ing["quantity_needed"])
                for ing in ingredients
            ],
        )


def get_recipe_cost(recipe_id: int) -> float:
    """Calculate the total ingredient cost for a recipe."""
    with get_connection() as conn:
        row = conn.execute(
            """SELECT COALESCE(SUM(ri.quantity_needed * i.cost_per_unit), 0) as total_cost
               FROM recipe_ingredients ri
               JOIN inventory i ON ri.inventory_id = i.id
               WHERE ri.recipe_id = ?""",
            (recipe_id,),
        ).fetchone()
        return row["total_cost"]


def get_low_stock_items():
    """Return inventory items where quantity is at or below min_stock_level."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT i.id, i.name, c.name as category, i.quantity, i.unit,
                   i.min_stock_level, i.supplier
            FROM inventory i
            LEFT JOIN categories c ON i.category_id = c.id
            WHERE i.quantity <= i.min_stock_level
            ORDER BY (i.quantity - i.min_stock_level) ASC
        """).fetchall()
        return [dict(r) for r in rows]
