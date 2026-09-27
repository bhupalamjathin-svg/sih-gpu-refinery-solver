"""
Production Scheduling LP Problem Generator.

Models a multi-period refinery production scheduling problem where
processing units must be allocated across time periods to meet demand
while respecting capacity and inventory constraints.

Typical problem:
  - T time periods (days/shifts)
  - N processing units (CDU, FCC, Reformer, VDU, etc.)
  - M products
  - Decision: how much to produce on each unit in each period
"""

import numpy as np
from solver.problem import LPProblem


PROCESSING_UNITS = [
    {"name": "CDU (Crude Distillation)",  "capacity": 5000, "op_cost": 3.5},
    {"name": "FCC (Fluid Cat Cracker)",    "capacity": 2000, "op_cost": 5.0},
    {"name": "Reformer",                   "capacity": 1500, "op_cost": 4.5},
    {"name": "VDU (Vacuum Distillation)",  "capacity": 3000, "op_cost": 3.0},
    {"name": "Hydrocracker",               "capacity": 1800, "op_cost": 6.0},
    {"name": "Coker",                      "capacity": 1200, "op_cost": 4.0},
    {"name": "Alkylation Unit",            "capacity": 800,  "op_cost": 7.0},
    {"name": "Isomerization Unit",         "capacity": 600,  "op_cost": 5.5},
]

SCHED_PRODUCTS = [
    {"name": "Petrol",   "revenue": 110, "storage_cost": 0.5},
    {"name": "Diesel",   "revenue": 95,  "storage_cost": 0.4},
    {"name": "Kerosene", "revenue": 100, "storage_cost": 0.3},
    {"name": "LPG",      "revenue": 85,  "storage_cost": 0.8},
]


def generate_scheduling_problem(
    n_periods: int = 7,
    n_units: int = 4,
    n_products: int = 3,
    seed: int = 42,
) -> LPProblem:
    """
    Generate a multi-period production scheduling LP.

    Decision variables:
      - p[t,u,k] = production of product k on unit u in period t
      - inv[t,k] = inventory of product k at end of period t

    Total variables: n_periods * n_units * n_products + n_periods * n_products

    Parameters
    ----------
    n_periods : number of time periods
    n_units : number of processing units (max 8)
    n_products : number of products (max 4)
    seed : random seed

    Returns
    -------
    LPProblem
    """
    rng = np.random.RandomState(seed)

    units = list(PROCESSING_UNITS)
    if n_units > len(units):
        for u in range(len(units), n_units):
            units.append({
                "name": f"Unit-{u+1}",
                "capacity": float(1000 + rng.randint(500, 4000)),
                "op_cost": float(3.0 + 4.0 * rng.rand()),
            })
    else:
        units = units[:n_units]

    products = list(SCHED_PRODUCTS)
    if n_products > len(products):
        for p in range(len(products), n_products):
            products.append({
                "name": f"Product-{p+1}",
                "revenue": float(80.0 + 40.0 * rng.rand()),
                "storage_cost": float(0.2 + 0.6 * rng.rand()),
            })
    else:
        products = products[:n_products]

    n_prod_vars = n_periods * len(units) * len(products)
    n_inv_vars = n_periods * len(products)
    n = n_prod_vars + n_inv_vars

    # Variable indexing helpers
    def prod_idx(t, u, k):
        return t * (n_units * n_products) + u * n_products + k

    def inv_idx(t, k):
        return n_prod_vars + t * n_products + k

    # Variable names
    var_names = []
    for t in range(n_periods):
        for u in range(n_units):
            for k in range(n_products):
                var_names.append(f"P{t}_{units[u]['name'][:5]}_{products[k]['name'][:5]}")
    for t in range(n_periods):
        for k in range(n_products):
            var_names.append(f"Inv{t}_{products[k]['name'][:5]}")

    # --- Objective: minimize cost = operating cost + storage cost - revenue ---
    c = np.zeros(n)
    for t in range(n_periods):
        for u in range(n_units):
            for k in range(n_products):
                idx = prod_idx(t, u, k)
                c[idx] = units[u]["op_cost"] - products[k]["revenue"]
        for k in range(n_products):
            c[inv_idx(t, k)] = products[k]["storage_cost"]

    # --- Constraints ---
    A_ub_rows = []
    b_ub_vals = []
    A_eq_rows = []
    b_eq_vals = []
    constraint_names = []

    # 1. Unit capacity per period: sum_k p[t,u,k] <= capacity[u]
    for t in range(n_periods):
        for u in range(n_units):
            row = np.zeros(n)
            for k in range(n_products):
                row[prod_idx(t, u, k)] = 1.0
            A_ub_rows.append(row)
            b_ub_vals.append(units[u]["capacity"])
            constraint_names.append(f"Cap_T{t}_{units[u]['name'][:5]}")

    # 2. Demand: generate varying demand per period per product
    demands = np.zeros((n_periods, n_products))
    base_demand = [1500, 2000, 1000, 800][:n_products]
    for t in range(n_periods):
        for k in range(n_products):
            demands[t, k] = base_demand[k] * (0.8 + 0.4 * rng.rand())

    # 3. Inventory balance: inv[t,k] = inv[t-1,k] + sum_u p[t,u,k] - demand[t,k]
    #    → sum_u p[t,u,k] - inv[t,k] + inv[t-1,k] = demand[t,k]
    initial_inventory = [500, 600, 300, 200][:n_products]
    for t in range(n_periods):
        for k in range(n_products):
            row = np.zeros(n)
            for u in range(n_units):
                row[prod_idx(t, u, k)] = 1.0
            row[inv_idx(t, k)] = -1.0
            if t > 0:
                row[inv_idx(t - 1, k)] = 1.0
                rhs = demands[t, k]
            else:
                rhs = demands[t, k] - initial_inventory[k]
            A_eq_rows.append(row)
            b_eq_vals.append(rhs)
            constraint_names.append(f"InvBal_T{t}_{products[k]['name'][:5]}")

    # 4. Minimum production targets per product per period
    for t in range(n_periods):
        for k in range(n_products):
            row = np.zeros(n)
            for u in range(n_units):
                row[prod_idx(t, u, k)] = -1.0
            A_ub_rows.append(row)
            b_ub_vals.append(-demands[t, k] * 0.5)  # At least 50% of demand
            constraint_names.append(f"MinProd_T{t}_{products[k]['name'][:5]}")

    A_ub = np.array(A_ub_rows) if A_ub_rows else None
    b_ub = np.array(b_ub_vals) if b_ub_vals else None
    A_eq = np.array(A_eq_rows) if A_eq_rows else None
    b_eq = np.array(b_eq_vals) if b_eq_vals else None

    return LPProblem(
        c=c,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=A_eq,
        b_eq=b_eq,
        lb=np.zeros(n),
        ub=np.full(n, 10000.0),
        var_names=var_names,
        constraint_names=constraint_names,
        name=f"Production Scheduling ({n_periods} periods × {n_units} units × {n_products} products)",
        metadata={
            "type": "scheduling",
            "n_periods": n_periods,
            "units": [u["name"] for u in units],
            "products": [p["name"] for p in products],
        },
    )
