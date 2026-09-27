"""
Refinery Unit Commitment & Discrete Schedule (Mixed-Integer Linear Programming - MILP).

Real-World Formulation:
Refineries cannot throttle heavy catalytic processing units to arbitrary fractions.
Units like the Hydrocracker, Catalytic Reformer, and Delayed Coker have:
  1. Discrete On/Off States: z[u,t] in {0, 1}
  2. Minimum Stable Operating Limits: when ON, throughput must be >= 40% capacity
  3. Startup Cost Penalties: turning on a unit incurs high thermal & flaring costs
     v[u,t] >= z[u,t] - z[u,t-1]

Decision Variables per unit u at period t:
  - x[u,t] : Continuous throughput (bbl/day)
  - z[u,t] : Binary operating state (0 = shutdown, 1 = active)
  - v[u,t] : Binary startup event (1 = started up this period)
"""

import numpy as np
from solver.problem import OptimizationProblem


def generate_unit_commitment_milp(
    n_units: int = 4,
    n_periods: int = 5,
    seed: int = 42,
) -> OptimizationProblem:
    """
    Generate a realistic Mixed-Integer Linear Program for refinery unit commitment.

    Parameters
    ----------
    n_units : int
        Number of heavy processing units.
    n_periods : int
        Number of scheduling periods (e.g. days/shifts).
    seed : int
        Random seed for demand and capacity generation.

    Returns
    -------
    OptimizationProblem (classified as MILP)
    """
    rng = np.random.RandomState(seed)

    unit_names = [
        "CDU-Primary", "VDU-Vacuum", "FCC-Cracker", "CRU-Reformer",
        "HCU-Hydrocracker", "DCU-Coker", "DHDS-Desulfurizer", "Alkylation"
    ]
    if n_units > len(unit_names):
        for i in range(len(unit_names), n_units):
            unit_names.append(f"Unit-{i+1}")
    else:
        unit_names = unit_names[:n_units]

    # Unit parameters
    max_capacities = [8000.0, 5000.0, 4500.0, 3000.0, 3500.0, 2500.0, 4000.0, 2000.0][:n_units]
    min_capacities = [cap * 0.35 for cap in max_capacities]  # 35% minimum operating limit
    operating_costs = [4.5, 6.0, 12.0, 15.0, 18.0, 10.0, 8.0, 14.0][:n_units]  # $/bbl
    startup_costs = [5000.0, 8000.0, 25000.0, 30000.0, 45000.0, 20000.0, 12000.0, 18000.0][:n_units]  # $ per startup

    # Variable indices:
    # For each period t and unit u:
    #   x_idx(u, t): Continuous flow
    #   z_idx(u, t): Binary ON/OFF
    #   v_idx(u, t): Binary Startup
    n_vars_per_ut = 3
    n = n_periods * n_units * n_vars_per_ut

    def idx_x(u, t): return (t * n_units + u) * 3 + 0
    def idx_z(u, t): return (t * n_units + u) * 3 + 1
    def idx_v(u, t): return (t * n_units + u) * 3 + 2

    # Objective: Minimize sum_{u,t} (op_cost * x + startup_cost * v - 25 * x)
    # i.e. cost minus revenue (margin)
    c = np.zeros(n)
    lb = np.zeros(n)
    ub = np.zeros(n)
    var_types = ["C"] * n
    var_names = []

    for t in range(n_periods):
        for u in range(n_units):
            ix = idx_x(u, t)
            iz = idx_z(u, t)
            iv = idx_v(u, t)

            # Net cost = operating_cost - $25/bbl margin
            c[ix] = operating_costs[u] - 25.0
            lb[ix] = 0.0
            ub[ix] = max_capacities[u]
            var_types[ix] = "C"

            # Fixed operating cost of unit being ON
            c[iz] = 1000.0
            lb[iz] = 0.0
            ub[iz] = 1.0
            var_types[iz] = "B"

            # Startup penalty
            c[iv] = startup_costs[u]
            lb[iv] = 0.0
            ub[iv] = 1.0
            var_types[iv] = "B"

            var_names.append(f"Flow_{unit_names[u][:6]}_d{t+1}")
            var_names.append(f"On_{unit_names[u][:6]}_d{t+1}")
            var_names.append(f"Start_{unit_names[u][:6]}_d{t+1}")

    # Constraints:
    A_ub_rows = []
    b_ub_vals = []

    # 1. Maximum capacity when ON: x[u,t] <= MaxCap * z[u,t]  ->  x - MaxCap * z <= 0
    # 2. Minimum throughput when ON: x[u,t] >= MinCap * z[u,t]  ->  -x + MinCap * z <= 0
    for t in range(n_periods):
        for u in range(n_units):
            # Max capacity constraint
            row_max = np.zeros(n)
            row_max[idx_x(u, t)] = 1.0
            row_max[idx_z(u, t)] = -max_capacities[u]
            A_ub_rows.append(row_max)
            b_ub_vals.append(0.0)

            # Min operating constraint
            row_min = np.zeros(n)
            row_min[idx_x(u, t)] = -1.0
            row_min[idx_z(u, t)] = min_capacities[u]
            A_ub_rows.append(row_min)
            b_ub_vals.append(0.0)

    # 3. Startup constraint: v[u,t] >= z[u,t] - z[u,t-1]  ->  z[u,t] - z[u,t-1] - v[u,t] <= 0
    for u in range(n_units):
        # Period 0: assume initially OFF
        row_start = np.zeros(n)
        row_start[idx_z(u, 0)] = 1.0
        row_start[idx_v(u, 0)] = -1.0
        A_ub_rows.append(row_start)
        b_ub_vals.append(0.0)

        for t in range(1, n_periods):
            row_start = np.zeros(n)
            row_start[idx_z(u, t)] = 1.0
            row_start[idx_z(u, t - 1)] = -1.0
            row_start[idx_v(u, t)] = -1.0
            A_ub_rows.append(row_start)
            b_ub_vals.append(0.0)

    # 4. Total daily production quota: sum_u x[u,t] >= daily_demand[t]
    # -> -sum_u x[u,t] <= -daily_demand[t]
    avg_total_cap = sum(max_capacities)
    daily_demands = avg_total_cap * (0.55 + 0.25 * rng.rand(n_periods))
    for t in range(n_periods):
        row_dem = np.zeros(n)
        for u in range(n_units):
            row_dem[idx_x(u, t)] = -1.0
        A_ub_rows.append(row_dem)
        b_ub_vals.append(-daily_demands[t])

    return OptimizationProblem(
        c=c,
        A_ub=np.array(A_ub_rows),
        b_ub=np.array(b_ub_vals),
        lb=lb,
        ub=ub,
        var_types=var_types,
        var_names=var_names,
        name=f"Unit Commitment & Schedule ({n_units} units × {n_periods} periods)",
        metadata={
            "n_units": n_units,
            "n_periods": n_periods,
            "type": "MILP",
        }
    )
