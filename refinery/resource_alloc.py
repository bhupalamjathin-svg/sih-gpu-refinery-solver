"""
Resource Allocation LP Problem Generator.

Models utility resource allocation across processing units in a refinery:
  - Resources: steam, power, cooling water, hydrogen, catalyst
  - Units: CDU, FCC, Reformer, Hydrocracker, etc.
  - Goal: maximize throughput while respecting resource availability
"""

import numpy as np
from solver.problem import LPProblem


RESOURCES = [
    {"name": "Steam (MT/hr)",        "available": 500,  "cost": 2.0},
    {"name": "Power (MW)",           "available": 120,  "cost": 8.0},
    {"name": "Cooling Water (m³/hr)","available": 8000, "cost": 0.5},
    {"name": "Hydrogen (Nm³/hr)",    "available": 50000,"cost": 3.0},
    {"name": "Catalyst (tons/day)",  "available": 20,   "cost": 50.0},
    {"name": "Fuel Gas (MMBTU/hr)",  "available": 300,  "cost": 4.0},
]

ALLOC_UNITS = [
    {"name": "CDU-1",       "throughput_value": 15, "base_capacity": 5000},
    {"name": "CDU-2",       "throughput_value": 15, "base_capacity": 4000},
    {"name": "FCC",         "throughput_value": 25, "base_capacity": 2000},
    {"name": "Reformer",    "throughput_value": 22, "base_capacity": 1500},
    {"name": "Hydrocracker","throughput_value": 30, "base_capacity": 1800},
    {"name": "VDU",         "throughput_value": 12, "base_capacity": 3000},
    {"name": "Coker",       "throughput_value": 18, "base_capacity": 1200},
    {"name": "Alkylation",  "throughput_value": 35, "base_capacity": 800},
]


def generate_resource_allocation_problem(
    n_resources: int = 4,
    n_units: int = 5,
    seed: int = 42,
) -> LPProblem:
    """
    Generate a resource allocation LP.

    Decision variables:
      - x[u] = throughput of unit u (barrels/day)
      - r[i,u] = amount of resource i allocated to unit u

    Total variables: n_units + n_resources * n_units

    Parameters
    ----------
    n_resources : number of resource types (max 6)
    n_units : number of processing units (max 8)
    seed : random seed

    Returns
    -------
    LPProblem
    """
    rng = np.random.RandomState(seed)
    n_resources = min(n_resources, len(RESOURCES))
    n_units = min(n_units, len(ALLOC_UNITS))

    resources = RESOURCES[:n_resources]
    units = ALLOC_UNITS[:n_units]

    n_throughput = n_units
    n_alloc = n_resources * n_units
    n = n_throughput + n_alloc

    def throughput_idx(u):
        return u

    def alloc_idx(i, u):
        return n_throughput + i * n_units + u

    # Variable names
    var_names = [f"Throughput_{units[u]['name']}" for u in range(n_units)]
    for i in range(n_resources):
        for u in range(n_units):
            var_names.append(f"{resources[i]['name'][:10]}→{units[u]['name']}")

    # --- Objective: maximize throughput value minus resource cost ---
    # minimize -(throughput value) + resource cost
    c = np.zeros(n)
    for u in range(n_units):
        c[throughput_idx(u)] = -units[u]["throughput_value"]
    for i in range(n_resources):
        for u in range(n_units):
            c[alloc_idx(i, u)] = resources[i]["cost"]

    # --- Constraints ---
    A_ub_rows = []
    b_ub_vals = []
    A_eq_rows = []
    b_eq_vals = []
    constraint_names = []

    # 1. Resource availability: sum_u r[i,u] <= available[i]
    for i in range(n_resources):
        row = np.zeros(n)
        for u in range(n_units):
            row[alloc_idx(i, u)] = 1.0
        A_ub_rows.append(row)
        b_ub_vals.append(resources[i]["available"])
        constraint_names.append(f"Avail_{resources[i]['name'][:12]}")

    # 2. Unit capacity: x[u] <= base_capacity[u]
    for u in range(n_units):
        row = np.zeros(n)
        row[throughput_idx(u)] = 1.0
        A_ub_rows.append(row)
        b_ub_vals.append(units[u]["base_capacity"])
        constraint_names.append(f"Cap_{units[u]['name']}")

    # 3. Resource requirement: each unit requires a certain amount of each
    #    resource per unit throughput.
    #    r[i,u] >= consumption_rate[i,u] * x[u]
    #    → consumption_rate[i,u] * x[u] - r[i,u] <= 0
    consumption_rates = rng.rand(n_resources, n_units) * 0.05
    # Make some resources more critical
    consumption_rates[0, :] *= 3   # Steam
    consumption_rates[1, :] *= 1.5 # Power

    for i in range(n_resources):
        for u in range(n_units):
            row = np.zeros(n)
            row[throughput_idx(u)] = consumption_rates[i, u]
            row[alloc_idx(i, u)] = -1.0
            A_ub_rows.append(row)
            b_ub_vals.append(0.0)
            constraint_names.append(f"Req_{resources[i]['name'][:6]}_{units[u]['name']}")

    # 4. Minimum throughput: each unit must operate above 10% of capacity
    for u in range(n_units):
        row = np.zeros(n)
        row[throughput_idx(u)] = -1.0
        A_ub_rows.append(row)
        b_ub_vals.append(-units[u]["base_capacity"] * 0.1)
        constraint_names.append(f"MinOp_{units[u]['name']}")

    A_ub = np.array(A_ub_rows)
    b_ub = np.array(b_ub_vals)

    return LPProblem(
        c=c,
        A_ub=A_ub,
        b_ub=b_ub,
        lb=np.zeros(n),
        ub=np.full(n, 100000.0),
        var_names=var_names,
        constraint_names=constraint_names,
        name=f"Resource Allocation ({n_resources} resources × {n_units} units)",
        metadata={
            "type": "resource_allocation",
            "resources": [r["name"] for r in resources],
            "units": [u["name"] for u in units],
        },
    )
