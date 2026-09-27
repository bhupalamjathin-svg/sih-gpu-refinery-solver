"""
Refinery Crude Oil Procurement Risk Optimization (Quadratic Programming - QP).

Real-World Formulation:
Refineries like MRPL purchase diverse crudes on volatile spot & term markets.
Pure LP only minimizes nominal expected purchase cost c^T x.
However, price volatility creates financial risk. 

By adding Markowitz covariance risk term (1/2 x^T Q x), the refinery minimizes
both purchasing cost AND procurement variance:
    minimize    1/2 x^T Q x + c^T x
    subject to  sum_i x_i = Total_Throughput
                sum_i x_i * sulfur_i <= max_sulfur * Total_Throughput
                sum_i x_i * api_i >= min_api * Total_Throughput
                0 <= x_i <= supply_limit_i
where Q is the positive semi-definite (PSD) price covariance matrix between crudes.
"""

import numpy as np
from solver.problem import OptimizationProblem


def generate_crude_risk_qp(
    n_crudes: int = 8,
    total_throughput: float = 30000.0,  # barrels/day
    risk_aversion: float = 0.5,         # lambda weight on variance
    seed: int = 42,
) -> OptimizationProblem:
    """
    Generate a realistic Quadratic Program for refinery crude procurement with market risk.

    Parameters
    ----------
    n_crudes : int
        Number of crude oil types available.
    total_throughput : float
        Target refinery crude distillation intake (bbl/day).
    risk_aversion : float
        Risk aversion multiplier (0 = pure LP, >0 = QP risk penalty).
    seed : int
        Random seed for covariance generation.

    Returns
    -------
    OptimizationProblem (classified as QP)
    """
    rng = np.random.RandomState(seed)

    crude_names = [
        "Bombay High", "Arab Light", "Arab Heavy", "Basrah Medium",
        "Kuwait Export", "Bonny Light", "Murban", "Upper Zakum",
        "Sokol", "Espo", "Maya", "Tapis"
    ]
    if n_crudes > len(crude_names):
        for i in range(len(crude_names), n_crudes):
            crude_names.append(f"Crude-{i+1}")
    else:
        crude_names = crude_names[:n_crudes]

    # Nominal purchase prices ($/bbl)
    base_prices = 60.0 + 25.0 * rng.rand(n_crudes)
    # Physical specs
    sulfur_pct = 0.1 + 2.5 * rng.rand(n_crudes)
    api_gravity = 25.0 + 20.0 * rng.rand(n_crudes)

    # Construct symmetric positive semi-definite (PSD) covariance matrix Q
    # Q = risk_aversion * (F F^T + D)
    n_factors = min(3, n_crudes)
    F = rng.randn(n_crudes, n_factors) * 4.0
    D = np.diag(rng.rand(n_crudes) * 2.0 + 1.0)
    cov_matrix = F @ F.T + D
    # Scale Q by risk aversion
    Q = risk_aversion * cov_matrix

    # Linear objective vector c
    c = base_prices.copy()

    # Constraints:
    # 1. Total throughput equality: sum_i x_i = total_throughput
    A_eq = np.ones((1, n_crudes))
    b_eq = np.array([total_throughput])

    # 2. Maximum blended sulfur content: sum_i sulfur_i * x_i <= 1.2% * total_throughput
    # 3. Minimum blended API gravity: -sum_i api_i * x_i <= -32.0 * total_throughput
    A_ub_rows = [
        sulfur_pct,
        -api_gravity,
    ]
    b_ub_vals = [
        1.2 * total_throughput,
        -32.0 * total_throughput,
    ]

    # Variable bounds: each crude has a pipeline/tanker supply quota
    supply_limits = (total_throughput / n_crudes) * (1.2 + 0.8 * rng.rand(n_crudes))
    lb = np.zeros(n_crudes)
    ub = supply_limits

    return OptimizationProblem(
        c=c,
        Q=Q,
        A_eq=A_eq,
        b_eq=b_eq,
        A_ub=np.array(A_ub_rows),
        b_ub=np.array(b_ub_vals),
        lb=lb,
        ub=ub,
        var_names=crude_names,
        name=f"Crude Procurement Risk Optimization ({n_crudes} crudes)",
        metadata={
            "total_throughput": total_throughput,
            "risk_aversion": risk_aversion,
            "type": "QP",
        }
    )
