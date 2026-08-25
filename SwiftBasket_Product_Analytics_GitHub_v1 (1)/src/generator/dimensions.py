from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


class DimensionValidationError(ValueError):
    """Raised when generated dimension tables fail validation."""


# ----------------------------------------------------------------------
# Static reference data — stores
# ----------------------------------------------------------------------

CITY_ZONES: dict[str, list[str]] = {
    "Bengaluru": ["Indiranagar", "HSR Layout", "Whitefield"],
    "Delhi NCR": ["Gurugram Sector 43", "Noida Sector 62", "South Delhi"],
    "Mumbai": ["Andheri West", "Powai", "Lower Parel"],
    "Hyderabad": ["Gachibowli", "Madhapur", "Kondapur"],
    "Pune": ["Baner", "Kharadi", "Hinjawadi"],
}

STORE_OPEN_RANGE_START = date(2024, 1, 1)
STORE_OPEN_RANGE_END = date(2025, 12, 1)


# ----------------------------------------------------------------------
# Product catalog — Category -> Subcategory -> {items, brands,
# pack_sizes, mrp_range}
#
# Every combination below is chosen to be business-plausible: pack
# sizes match how the item is actually sold, brands are only used
# where they make sense (e.g. TinyCare only appears in baby care),
# and MRP ranges are calibrated per subcategory rather than per
# top-level category.
# ----------------------------------------------------------------------

PRODUCT_CATALOG: dict[str, dict[str, dict[str, Any]]] = {
    "Fruits and vegetables": {
        "Fresh Fruits": {
            "items": ["Bananas", "Apples", "Mangoes", "Grapes", "Oranges"],
            "brands": ["UrbanHarvest", "FreshNest"],
            "pack_sizes": ["6 Pieces", "4 Pieces", "500 g", "1 kg"],
            "mrp_range": (30, 250),
        },
        "Fresh Vegetables": {
            "items": [
                "Tomatoes", "Onions", "Potatoes", "Carrots", "Cucumbers",
            ],
            "brands": ["UrbanHarvest", "FreshNest"],
            "pack_sizes": ["250 g", "500 g", "1 kg"],
            "mrp_range": (15, 120),
        },
        "Herbs and Leafy Greens": {
            "items": ["Coriander", "Mint", "Spinach", "Curry Leaves"],
            "brands": ["UrbanHarvest"],
            "pack_sizes": ["1 Bunch", "100 g", "200 g"],
            "mrp_range": (10, 50),
        },
    },
    "Dairy and breakfast": {
        "Milk": {
            "items": ["Toned Milk", "Full Cream Milk", "Skimmed Milk"],
            "brands": ["FreshNest", "DailyDrop"],
            "pack_sizes": ["500 ml", "1 L"],
            "mrp_range": (25, 80),
        },
        "Bread": {
            "items": ["Brown Bread", "White Bread", "Multigrain Bread"],
            "brands": ["DailyDrop", "FreshNest"],
            "pack_sizes": ["400 g", "600 g"],
            "mrp_range": (35, 75),
        },
        "Eggs": {
            "items": ["Farm Eggs", "Brown Eggs"],
            "brands": ["DailyDrop"],
            "pack_sizes": ["6 Pieces", "12 Pieces"],
            "mrp_range": (40, 120),
        },
        "Breakfast Cereal": {
            "items": ["Corn Flakes", "Oats", "Muesli"],
            "brands": ["DailyDrop", "QuickChoice"],
            "pack_sizes": ["500 g", "1 kg"],
            "mrp_range": (150, 400),
        },
    },
    "Snacks": {
        "Chips": {
            "items": [
                "Masala Chips", "Salted Chips", "Cream and Onion Chips",
            ],
            "brands": ["SnackCraft", "QuickChoice"],
            "pack_sizes": ["52 g", "90 g", "150 g"],
            "mrp_range": (10, 60),
        },
        "Namkeen": {
            "items": ["Aloo Bhujia", "Moong Dal Namkeen", "Mixture"],
            "brands": ["SnackCraft"],
            "pack_sizes": ["150 g", "200 g", "400 g"],
            "mrp_range": (30, 120),
        },
        "Biscuits": {
            "items": [
                "Cream Biscuits", "Digestive Biscuits", "Marie Biscuits",
            ],
            "brands": ["SnackCraft", "DailyDrop"],
            "pack_sizes": ["100 g", "200 g"],
            "mrp_range": (10, 60),
        },
        "Chocolates": {
            "items": ["Milk Chocolate", "Dark Chocolate", "Chocolate Bar"],
            "brands": ["SnackCraft"],
            "pack_sizes": ["1 Piece", "50 g", "100 g"],
            "mrp_range": (20, 150),
        },
    },
    "Beverages": {
        "Juices": {
            "items": ["Orange Juice", "Mixed Fruit Juice", "Apple Juice"],
            "brands": ["FreshNest", "PureLeaf"],
            "pack_sizes": ["200 ml", "1 L"],
            "mrp_range": (20, 180),
        },
        "Soft Drinks": {
            "items": ["Cola", "Lemon Soda", "Orange Soda"],
            "brands": ["QuickChoice"],
            "pack_sizes": ["250 ml", "750 ml", "1.25 L"],
            "mrp_range": (20, 90),
        },
        "Tea and Coffee": {
            "items": ["Green Tea", "Black Tea", "Instant Coffee"],
            "brands": ["PureLeaf", "DailyDrop"],
            "pack_sizes": ["100 g", "250 g", "500 g"],
            "mrp_range": (80, 500),
        },
        "Packaged Water": {
            "items": ["Packaged Drinking Water"],
            "brands": ["QuickChoice"],
            "pack_sizes": ["500 ml", "1 L", "2 L"],
            "mrp_range": (10, 40),
        },
    },
    "Packaged foods": {
        "Instant Food": {
            "items": [
                "Instant Noodles", "Instant Pasta", "Ready to Eat Poha",
            ],
            "brands": ["QuickChoice", "DailyDrop"],
            "pack_sizes": ["70 g", "140 g", "280 g"],
            "mrp_range": (12, 90),
        },
        "Sauces and Condiments": {
            "items": ["Tomato Ketchup", "Green Chilli Sauce", "Soy Sauce"],
            "brands": ["DailyDrop", "QuickChoice"],
            "pack_sizes": ["200 g", "500 g", "1 kg"],
            "mrp_range": (50, 300),
        },
        "Atta and Flour": {
            "items": ["Wheat Atta", "Multigrain Atta", "Rice Flour"],
            "brands": ["UrbanHarvest", "FreshNest"],
            "pack_sizes": ["1 kg", "5 kg", "10 kg"],
            "mrp_range": (60, 600),
        },
        "Pulses": {
            "items": ["Toor Dal", "Moong Dal", "Chana Dal"],
            "brands": ["UrbanHarvest", "FreshNest"],
            "pack_sizes": ["500 g", "1 kg"],
            "mrp_range": (70, 350),
        },
        "Cooking Oil": {
            "items": ["Sunflower Oil", "Mustard Oil", "Groundnut Oil"],
            "brands": ["UrbanHarvest", "FreshNest"],
            "pack_sizes": ["500 ml", "1 L", "5 L"],
            "mrp_range": (100, 700),
        },
        "Rice": {
            "items": ["Basmati Rice", "Sona Masoori Rice"],
            "brands": ["UrbanHarvest"],
            "pack_sizes": ["1 kg", "5 kg"],
            "mrp_range": (80, 700),
        },
    },
    "Household care": {
        "Cleaners": {
            "items": ["Floor Cleaner", "Toilet Cleaner", "Glass Cleaner"],
            "brands": ["HomeBright"],
            "pack_sizes": ["500 ml", "1 L"],
            "mrp_range": (60, 300),
        },
        "Detergents": {
            "items": [
                "Laundry Detergent Powder", "Laundry Liquid Detergent",
            ],
            "brands": ["HomeBright"],
            "pack_sizes": ["1 kg", "2 kg", "1 L"],
            "mrp_range": (100, 600),
        },
        "Air Fresheners": {
            "items": ["Room Freshener Spray", "Car Freshener"],
            "brands": ["HomeBright"],
            "pack_sizes": ["1 Piece", "300 ml"],
            "mrp_range": (80, 350),
        },
        "Dishwash": {
            "items": ["Dishwash Liquid", "Dishwash Bar"],
            "brands": ["HomeBright"],
            "pack_sizes": ["200 ml", "500 ml", "1 Piece"],
            "mrp_range": (30, 200),
        },
    },
    "Personal care": {
        "Skin Care": {
            "items": ["Face Wash", "Body Lotion", "Sunscreen"],
            "brands": ["PureLeaf", "QuickChoice"],
            "pack_sizes": ["50 g", "100 ml", "200 ml"],
            "mrp_range": (80, 600),
        },
        "Hair Care": {
            "items": ["Shampoo", "Conditioner", "Hair Oil"],
            "brands": ["PureLeaf", "QuickChoice"],
            "pack_sizes": ["100 ml", "200 ml", "340 ml"],
            "mrp_range": (60, 500),
        },
        "Oral Care": {
            "items": ["Toothpaste", "Toothbrush", "Mouthwash"],
            "brands": ["QuickChoice", "PureLeaf"],
            "pack_sizes": ["1 Piece", "100 g", "200 ml"],
            "mrp_range": (40, 250),
        },
        "Hand Hygiene": {
            "items": ["Hand Wash", "Hand Sanitizer"],
            "brands": ["PureLeaf", "QuickChoice"],
            "pack_sizes": ["100 ml", "250 ml", "500 ml"],
            "mrp_range": (50, 300),
        },
    },
    "Baby care": {
        "Diapers": {
            "items": [
                "Baby Diapers Small", "Baby Diapers Medium",
                "Baby Diapers Large",
            ],
            "brands": ["TinyCare"],
            "pack_sizes": ["20 Pieces", "40 Pieces", "60 Pieces"],
            "mrp_range": (300, 1200),
        },
        "Baby Food": {
            "items": ["Baby Cereal", "Baby Formula Milk"],
            "brands": ["TinyCare"],
            "pack_sizes": ["200 g", "400 g"],
            "mrp_range": (250, 900),
        },
        "Baby Skin Care": {
            "items": ["Baby Lotion", "Baby Powder", "Baby Oil"],
            "brands": ["TinyCare"],
            "pack_sizes": ["100 ml", "200 ml", "100 g"],
            "mrp_range": (100, 500),
        },
        "Baby Wipes": {
            "items": ["Baby Wipes"],
            "brands": ["TinyCare"],
            "pack_sizes": ["1 Piece", "2 Piece Pack"],
            "mrp_range": (100, 300),
        },
    },
}

CATEGORY_WEIGHTS: dict[str, float] = {
    "Fruits and vegetables": 0.15,
    "Dairy and breakfast": 0.15,
    "Snacks": 0.17,
    "Beverages": 0.14,
    "Packaged foods": 0.17,
    "Household care": 0.10,
    "Personal care": 0.08,
    "Baby care": 0.04,
}

# Sanity check at import time: every category in the weights must
# exist in the catalog, and vice versa.
assert set(CATEGORY_WEIGHTS.keys()) == set(PRODUCT_CATALOG.keys()), (
    "CATEGORY_WEIGHTS and PRODUCT_CATALOG must define the same categories."
)

ACTIVE_PRODUCT_PROBABILITY = 0.98

ITEM_PACK_OVERRIDES: dict[str, list[str]] = {
    "Mouthwash": ["200 ml"],
    "Toothpaste": ["100 g"],
    "Toothbrush": ["1 Piece"],
    "Dishwash Liquid": ["200 ml", "500 ml"],
    "Dishwash Bar": ["1 Piece"],
    "Laundry Detergent Powder": ["1 kg", "2 kg"],
    "Laundry Liquid Detergent": ["1 L"],
    "Car Freshener": ["1 Piece"],
    "Room Freshener Spray": ["300 ml"],
}

PACK_PRICE_OVERRIDES: dict[tuple[str, str], tuple[int, int]] = {
    ("Wheat Atta", "1 kg"): (45, 100),
    ("Wheat Atta", "5 kg"): (220, 450),
    ("Wheat Atta", "10 kg"): (420, 750),
    ("Multigrain Atta", "1 kg"): (70, 160),
    ("Multigrain Atta", "5 kg"): (300, 650),
    ("Mustard Oil", "500 ml"): (70, 180),
    ("Mustard Oil", "1 L"): (140, 350),
    ("Mustard Oil", "5 L"): (600, 950),
}


# ----------------------------------------------------------------------
# Store generation
# ----------------------------------------------------------------------

def generate_stores(
    config: dict[str, Any],
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Generate the stores dimension table: stores_per_city per city."""

    cities: list[str] = config["cities"]
    stores_per_city: int = config["scale"]["stores_per_city"]

    rows: list[dict[str, Any]] = []
    store_id = 1
    city_counter: dict[str, int] = {}

    open_range_days = (STORE_OPEN_RANGE_END - STORE_OPEN_RANGE_START).days

    for city in cities:
        zones = CITY_ZONES.get(city)

        if zones is None:
            raise DimensionValidationError(
                f"No fictional store zones defined for city '{city}'. "
                f"Add it to CITY_ZONES."
            )

        if len(zones) < stores_per_city:
            raise DimensionValidationError(
                f"City '{city}' has only {len(zones)} defined zones but "
                f"stores_per_city={stores_per_city} requires more."
            )

        city_counter[city] = 0

        for i in range(stores_per_city):
            city_counter[city] += 1
            zone = zones[i]

            offset_days = int(rng.integers(0, open_range_days + 1))
            opened_at = STORE_OPEN_RANGE_START + timedelta(days=offset_days)

            rows.append(
                {
                    "store_id": store_id,
                    "store_name": (
                        f"SwiftBasket {city} {city_counter[city]:02d}"
                    ),
                    "city": city,
                    "zone": zone,
                    "opened_at": opened_at,
                    "is_active": True,
                }
            )
            store_id += 1

    stores = pd.DataFrame(rows)
    return stores


# ----------------------------------------------------------------------
# Product generation — catalog-driven
# ----------------------------------------------------------------------

def _sample_categories(
    n_products: int,
    rng: np.random.Generator,
) -> list[str]:
    """Sample category assignments matching the configured weights."""

    categories = list(CATEGORY_WEIGHTS.keys())
    weights = np.array(list(CATEGORY_WEIGHTS.values()))
    weights = weights / weights.sum()

    return list(rng.choice(categories, size=n_products, p=weights))


def generate_products(
    config: dict[str, Any],
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Generate the products dimension table from the product catalog.

    Every product is built as:
        category -> subcategory -> item -> valid brand -> valid pack
        size -> price drawn from that subcategory's price range.

    This guarantees business-plausible combinations instead of
    independently randomizing each attribute.
    """

    n_products: int = config["scale"]["products"]
    categories = _sample_categories(n_products, rng)

    rows: list[dict[str, Any]] = []
    used_names: set[str] = set()

    for product_id, category in enumerate(categories, start=1):
        subcategories = list(PRODUCT_CATALOG[category].keys())
        subcategory = rng.choice(subcategories)
        group = PRODUCT_CATALOG[category][subcategory]

        item_name = rng.choice(group["items"])
        brand = rng.choice(group["brands"])
        pack_size = rng.choice(ITEM_PACK_OVERRIDES.get(item_name, group["pack_sizes"]))

        product_name = f"{brand} {item_name} {pack_size}"

        used_names.add(product_name)

        mrp_low, mrp_high = PACK_PRICE_OVERRIDES.get(
            (item_name, str(pack_size)), group["mrp_range"]
        )
        raw_mrp = float(rng.uniform(mrp_low, mrp_high))
        mrp = float(round(raw_mrp))

        discount_rate = float(rng.uniform(0.0, 0.25))
        base_selling_price = float(round(mrp * (1 - discount_rate)))

        # Guard against rounding pushing selling price above mrp
        # or down to a non-positive value.
        base_selling_price = min(base_selling_price, mrp)
        if base_selling_price <= 0:
            base_selling_price = float(round(mrp * 0.75))

        is_active = bool(rng.random() < ACTIVE_PRODUCT_PROBABILITY)

        rows.append(
            {
                "product_id": product_id,
                "product_name": product_name,
                "category": category,
                "subcategory": subcategory,
                "brand": brand,
                "mrp": mrp,
                "base_selling_price": base_selling_price,
                "is_active": is_active,
                # Internal-only fields, used for semantic validation.
                # Dropped before the table is saved/exported.
                "item_name_internal": item_name,
                "pack_size_internal": pack_size,
            }
        )

    products = pd.DataFrame(rows)
    return products


# ----------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------

def validate_dimensions(
    stores: pd.DataFrame,
    products: pd.DataFrame,
    config: dict[str, Any],
) -> None:
    """Validate generated stores and products against the specification.

    `products` may include the internal `_item` / `_pack_size` columns
    produced by `generate_products`; they are used here for semantic
    checks and are not required to be present in the saved output.
    """

    cities: list[str] = config["cities"]
    stores_per_city: int = config["scale"]["stores_per_city"]
    expected_store_count = len(cities) * stores_per_city
    expected_product_count: int = config["scale"]["products"]

    acquisition_start = date.fromisoformat(
        config["timeline"]["acquisition_start"]
    )

    # ================= STORES =================

    if len(stores) != expected_store_count:
        raise DimensionValidationError(
            f"Expected {expected_store_count} stores "
            f"(cities x stores_per_city), got {len(stores)}."
        )

    per_city_counts = stores.groupby("city")["store_id"].count()
    for city in cities:
        count = int(per_city_counts.get(city, 0))
        if count != stores_per_city:
            raise DimensionValidationError(
                f"City '{city}' has {count} stores, expected "
                f"{stores_per_city}."
            )

    if stores["store_id"].duplicated().any():
        raise DimensionValidationError("Duplicate store_id values found.")

    if stores["store_name"].duplicated().any():
        raise DimensionValidationError("Duplicate store_name values found.")

    late_openings = stores[
        pd.to_datetime(stores["opened_at"]) > pd.Timestamp(acquisition_start)
    ]
    if not late_openings.empty:
        raise DimensionValidationError(
            "Some stores have opened_at after the dataset acquisition "
            f"start ({acquisition_start}): "
            f"{late_openings['store_id'].tolist()}"
        )

    # ================= PRODUCTS: structural =================

    if len(products) != expected_product_count:
        raise DimensionValidationError(
            f"Expected {expected_product_count} products, "
            f"got {len(products)}."
        )

    if products["product_id"].duplicated().any():
        raise DimensionValidationError("Duplicate product_id values found.")

    if products["category"].isnull().any():
        raise DimensionValidationError("Null category values found.")

    unexpected_categories = set(products["category"].unique()) - set(
        PRODUCT_CATALOG.keys()
    )
    if unexpected_categories:
        raise DimensionValidationError(
            f"Unexpected category values found: {unexpected_categories}"
        )

    if (products["mrp"] <= 0).any():
        raise DimensionValidationError("Non-positive mrp values found.")

    if (products["base_selling_price"] <= 0).any():
        raise DimensionValidationError(
            "Non-positive base_selling_price values found."
        )

    if (products["base_selling_price"] > products["mrp"]).any():
        raise DimensionValidationError(
            "Some products have base_selling_price greater than mrp."
        )

    empty_names = products["product_name"].isnull() | (
        products["product_name"].str.strip() == ""
    )
    if empty_names.any():
        raise DimensionValidationError("Empty product_name values found.")

    # ================= PRODUCTS: semantic (catalog-consistency) =====

    for row in products.itertuples(index=False):
        category = row.category
        subcategory = row.subcategory
        brand = row.brand
        mrp = row.mrp
        item_name = getattr(row, "item_name_internal", None)

        group = PRODUCT_CATALOG.get(category, {}).get(subcategory)

        # 1. Subcategory belongs to its category.
        if group is None:
            raise DimensionValidationError(
                f"product_id={row.product_id}: subcategory "
                f"'{subcategory}' is not valid for category "
                f"'{category}'."
            )

        # 2. Brand is allowed for that product group.
        if brand not in group["brands"]:
            raise DimensionValidationError(
                f"product_id={row.product_id}: brand '{brand}' is not "
                f"a valid brand for {category} / {subcategory}."
            )

        # 3. MRP lies inside its subcategory price range.
        pack_size = getattr(row, "pack_size_internal", None)
        mrp_low, mrp_high = PACK_PRICE_OVERRIDES.get(
            (item_name, pack_size), group["mrp_range"]
        )
        if not (mrp_low <= mrp <= mrp_high):
            raise DimensionValidationError(
                f"product_id={row.product_id}: mrp {mrp} is outside "
                f"the valid range [{mrp_low}, {mrp_high}] for "
                f"{category} / {subcategory}."
            )

        # 4. Pack size is appropriate for the product group.
        if hasattr(row, "pack_size_internal"):
            valid_packs = ITEM_PACK_OVERRIDES.get(item_name, group["pack_sizes"])
            if pack_size not in valid_packs:
                raise DimensionValidationError(
                    f"product_id={row.product_id}: pack size "
                    f"'{pack_size}' is not valid for {category} / "
                    f"{subcategory}."
                )

        # 5. Item is a recognized item for the product group.
        if hasattr(row, "item_name_internal"):
            if item_name not in group["items"]:
                raise DimensionValidationError(
                    f"product_id={row.product_id}: item '{item_name}' "
                    f"is not valid for {category} / {subcategory}."
                )


# ----------------------------------------------------------------------
# Orchestration / CLI entry point
# ----------------------------------------------------------------------

OUTPUT_COLUMNS = [
    "product_id",
    "product_name",
    "category",
    "subcategory",
    "brand",
    "mrp",
    "base_selling_price",
    "is_active",
]


def run(
    config: dict[str, Any],
    output_dir: str | Path = "data",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate, validate, save and summarize stores and products."""

    rng = np.random.default_rng(config["project"]["random_seed"])

    stores = generate_stores(config, rng)
    products_full = generate_products(config, rng)

    # Validate using the full frame (with internal _item / _pack_size
    # columns) so semantic checks can run, then strip those columns
    # before returning/saving the officially-scoped table.
    validate_dimensions(stores, products_full, config)

    products = products_full[OUTPUT_COLUMNS].copy()

    output_dir = Path(output_dir)
    generated_dir = output_dir / "generated"
    samples_dir = output_dir / "samples"
    generated_dir.mkdir(parents=True, exist_ok=True)
    samples_dir.mkdir(parents=True, exist_ok=True)

    try:
        stores.to_parquet(generated_dir / "stores.parquet", index=False)
        products.to_parquet(generated_dir / "products.parquet", index=False)
    except ImportError:
        stores.to_csv(generated_dir / "stores.csv", index=False)
        products.to_csv(generated_dir / "products.csv", index=False)

    stores.head(20).to_csv(samples_dir / "stores_sample.csv", index=False)
    products.head(20).to_csv(samples_dir / "products_sample.csv", index=False)

    active_pct = products["is_active"].mean() * 100

    print(f"Stores generated: {len(stores)}")
    print(f"Products generated: {len(products)}")
    print(f"Cities represented: {stores['city'].nunique()}")
    print(f"Active products: approximately {active_pct:.1f}%")
    print("Dimension validation passed")

    return stores, products


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.generator.config_loader import load_config

    cfg = load_config("config/generation_config.yaml")
    run(cfg)
