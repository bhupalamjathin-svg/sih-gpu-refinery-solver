"""
Crude Oil Blending LP Problem Generator.

Models a refinery blending operation where multiple crude oil types
are mixed to produce petroleum products meeting quality specifications.

Typical MRPL-style problem:
  - 5-20 crude oil types (Bombay High, Arab Light, Basrah, etc.)
  - 4-8 products (Petrol, Diesel, Kerosene, LPG, Fuel Oil, Naphtha)
  - Quality constraints: Octane, Sulfur, API gravity, Reid Vapor Pressure
  - Capacity constraints: CDU throughput
  - Demand constraints: minimum/maximum product output
"""

import numpy as np
from solver.problem import LPProblem


# Blending component streams (post-processing intermediate products)
# In a real refinery, crude is processed through CDU/FCC/Reformer first,
# then the output streams are blended to make final products.
CRUDE_TYPES = [
    {"name": "Reformate",     "cost": 85, "sulfur": 0.01, "api": 45.0, "octane": 98},
    {"name": "FCC Gasoline",  "cost": 70, "sulfur": 0.08, "api": 55.0, "octane": 92},
    {"name": "Straight-Run",  "cost": 55, "sulfur": 0.15, "api": 60.0, "octane": 70},
    {"name": "Isomerate",     "cost": 80, "sulfur": 0.02, "api": 78.0, "octane": 87},
    {"name": "Alkylate",      "cost": 90, "sulfur": 0.01, "api": 72.0, "octane": 95},
    {"name": "Light Naphtha",  "cost": 50, "sulfur": 0.05, "api": 82.0, "octane": 65},
    {"name": "Heavy Naphtha",  "cost": 58, "sulfur": 0.10, "api": 48.0, "octane": 55},
    {"name": "LCO (Lt Cycle)", "cost": 45, "sulfur": 0.80, "api": 22.0, "octane": 30},
    {"name": "VGO",            "cost": 40, "sulfur": 1.50, "api": 20.0, "octane": 0},
    {"name": "Residue",        "cost": 30, "sulfur": 2.50, "api": 12.0, "octane": 0},
]

PRODUCTS = [
    {"name": "Petrol (MS)",     "price": 110, "min_octane": 87, "max_sulfur": 0.10, "min_api": 55},
    {"name": "Diesel (HSD)",    "price": 95,  "min_octane": 0,  "max_sulfur": 0.50, "min_api": 30},
    {"name": "Kerosene (ATF)",  "price": 100, "min_octane": 0,  "max_sulfur": 0.30, "min_api": 38},
    {"name": "LPG",             "price": 85,  "min_octane": 0,  "max_sulfur": 0.50, "min_api": 0},
    {"name": "Fuel Oil",        "price": 55,  "min_octane": 0,  "max_sulfur": 3.50, "min_api": 10},
    {"name": "Naphtha",         "price": 90,  "min_octane": 60, "max_sulfur": 0.20, "min_api": 50},
]


def generate_blending_problem(
    n_crudes: int = 6,
    n_products: int = 4,
    total_capacity: float = 15000,  # barrels/day
    seed: int = 42,
) -> LPProblem:
    """
    Generate a realistic crude oil blending LP.

    Decision variables: x[i,j] = barrels of crude i allocated to product j
    Total variables: n_crudes * n_products

    Parameters
    ----------
    n_crudes : number of crude types (max 10)
    n_products : number of product types (max 6)
    total_capacity : total CDU capacity in barrels/day
    seed : random seed for demand/supply variation

    Returns
    -------
    LPProblem
    """
    rng = np.random.RandomState(seed)

    # Base list extended dynamically if user requests larger industrial problems
    crudes = list(CRUDE_TYPES)
    if n_crudes > len(crudes):
        for i in range(len(crudes), n_crudes):
            cost = 40.0 + 50.0 * rng.rand()
            sulfur = 0.01 + 2.0 * rng.rand()
            api = 20.0 + 60.0 * rng.rand()
            octane = 50.0 + 48.0 * rng.rand()
            crudes.append({
                "name": f"Stream-{i+1}",
                "cost": cost,
                "sulfur": sulfur,
                "api": api,
                "octane": octane,
            })
    else:
        crudes = crudes[:n_crudes]

    products = list(PRODUCTS)
    if n_products > len(products):
        for j in range(len(products), n_products):
            price = 70.0 + 50.0 * rng.rand()
            min_oct = 80.0 if rng.rand() > 0.4 else 0.0
            max_s = 0.05 + 0.5 * rng.rand()
            min_api = 25.0 + 30.0 * rng.rand()
            products.append({
                "name": f"Grade-{j+1}",
                "price": price,
                "min_octane": min_oct,
                "max_sulfur": max_s,
                "min_api": min_api,
            })
    else:
        products = products[:n_products]

    n = len(crudes) * len(products)

    # Variable names: x_crude_product
    var_names = []
    for i, cr in enumerate(crudes):
        for j, pr in enumerate(products):
            var_names.append(f"{cr['name'][:8]}→{pr['name'][:8]}")

    # --- Objective: maximize profit = revenue - crude cost ---
    # We negate for minimization: minimize -(revenue - cost) = cost - revenue
    c = np.zeros(n)
    for i, cr in enumerate(crudes):
        for j, pr in enumerate(products):
            idx = i * n_products + j
            c[idx] = cr["cost"] - pr["price"]  # cost - revenue (negative = profit)

    # --- Constraints ---
    A_ub_rows = []
    b_ub_vals = []
    constraint_names = []

    # 1. Crude supply constraints: sum_j x[i,j] <= supply[i]
    supplies = [total_capacity / n_crudes * (0.8 + 0.4 * rng.rand()) for _ in range(n_crudes)]
    for i in range(n_crudes):
        row = np.zeros(n)
        for j in range(n_products):
            row[i * n_products + j] = 1.0
        A_ub_rows.append(row)
        b_ub_vals.append(supplies[i])
        constraint_names.append(f"Supply({crudes[i]['name'][:10]})")

    # 2. Demand constraints: sum_i x[i,j] >= demand[j]  →  -sum_i x[i,j] <= -demand[j]
    demands = [total_capacity / n_products * (0.3 + 0.3 * rng.rand()) for _ in range(n_products)]
    for j in range(n_products):
        row = np.zeros(n)
        for i in range(n_crudes):
            row[i * n_products + j] = -1.0
        A_ub_rows.append(row)
        b_ub_vals.append(-demands[j])
        constraint_names.append(f"Demand({products[j]['name'][:10]})")

    # 3. Total capacity constraint: sum_{i,j} x[i,j] <= total_capacity
    row = np.ones(n)
    A_ub_rows.append(row)
    b_ub_vals.append(total_capacity)
    constraint_names.append("TotalCapacity")

    # 4. Sulfur quality constraints (linearized):
    #    For each product j: sum_i (sulfur_i * x[i,j]) <= max_sulfur_j * sum_i x[i,j]
    #    → sum_i (sulfur_i - max_sulfur_j) * x[i,j] <= 0
    for j, pr in enumerate(products):
        if pr["max_sulfur"] < 3.0:  # Skip fuel oil (anything goes)
            row = np.zeros(n)
            for i, cr in enumerate(crudes):
                idx = i * n_products + j
                row[idx] = cr["sulfur"] - pr["max_sulfur"]
            A_ub_rows.append(row)
            b_ub_vals.append(0.0)
            constraint_names.append(f"Sulfur({pr['name'][:10]})")

    # 5. Octane constraints (for products that need it):
    #    sum_i (octane_i - min_octane_j) * x[i,j] >= 0
    #    → sum_i (min_octane_j - octane_i) * x[i,j] <= 0
    for j, pr in enumerate(products):
        if pr["min_octane"] > 0:
            row = np.zeros(n)
            for i, cr in enumerate(crudes):
                idx = i * n_products + j
                row[idx] = pr["min_octane"] - cr["octane"]
            A_ub_rows.append(row)
            b_ub_vals.append(0.0)
            constraint_names.append(f"Octane({pr['name'][:10]})")

    A_ub = np.array(A_ub_rows)
    b_ub = np.array(b_ub_vals)

    return LPProblem(
        c=c,
        A_ub=A_ub,
        b_ub=b_ub,
        lb=np.zeros(n),
        ub=np.full(n, total_capacity),
        var_names=var_names,
        constraint_names=constraint_names,
        name=f"Crude Oil Blending ({n_crudes} crudes × {n_products} products)",
        metadata={
            "type": "blending",
            "crudes": [cr["name"] for cr in crudes],
            "products": [pr["name"] for pr in products],
            "total_capacity": total_capacity,
        },
    )
