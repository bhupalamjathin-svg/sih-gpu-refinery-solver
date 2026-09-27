"""
Benchmark harness for GPU vs CPU comparison.

Runs the PDHG solver on problems of increasing size,
compares against SciPy linprog (HiGHS), and generates
speedup data for visualization.
"""

import time
import json
import numpy as np
from scipy.optimize import linprog, minimize
from scipy import sparse as sp

from .problem import LPProblem
from .pdhg import PDHGSolver


def generate_random_lp(n_vars: int, n_constraints: int, density: float = 0.3,
                        seed: int = 42) -> LPProblem:
    """
    Generate a random feasible LP for benchmarking.

    Creates a problem with a known feasible solution to ensure
    both solvers can converge.
    """
    rng = np.random.RandomState(seed)

    # Generate a feasible point first, then build constraints around it
    x_feas = rng.rand(n_vars) * 10  # feasible point in [0, 10]

    # Random sparse constraint matrix
    A = sp.random(n_constraints, n_vars, density=density,
                   random_state=rng, format="csr")
    A.data[:] = rng.randn(len(A.data))

    # Set b = A @ x_feas + slack (slack > 0 for feasibility)
    b = np.array(A @ x_feas).ravel() + rng.rand(n_constraints) * 5

    # Random objective
    c = rng.randn(n_vars)

    return LPProblem(
        c=c,
        A_ub=A,
        b_ub=b,
        lb=np.zeros(n_vars),
        ub=np.full(n_vars, 20.0),
        name=f"Random LP ({n_vars} vars, {n_constraints} cons)",
    )


def benchmark_solver(problem: LPProblem, use_gpu: bool, tol: float = 1e-4,
                      max_iter: int = 5000) -> dict:
    """Run PDHG solver and return timing data."""
    solver = PDHGSolver(
        max_iterations=max_iter,
        tol=tol,
        use_gpu=use_gpu,
        verbose=False,
    )

    # Warm-up run (important for GPU — first run includes kernel compilation)
    if use_gpu:
        try:
            solver.solve(problem)
        except Exception:
            pass

    t_start = time.perf_counter()
    result = solver.solve(problem)
    t_end = time.perf_counter()

    return {
        "device": "GPU" if use_gpu else "CPU",
        "time": t_end - t_start,
        "iterations": result.n_iterations,
        "status": result.status,
        "obj_val": result.obj_val,
        "primal_res": result.primal_residual,
        "dual_res": result.dual_residual,
        "gap": result.duality_gap,
    }


def benchmark_scipy(problem: LPProblem) -> dict:
    """Run SciPy linprog (HiGHS) for LP or minimize (SLSQP) for QP."""
    bounds = list(zip(problem.lb.tolist(), problem.ub.tolist()))

    # Convert sparse to dense for scipy if needed
    A_ub = problem.A_ub
    if sp.issparse(A_ub):
        A_ub = A_ub.toarray()

    A_eq = problem.A_eq
    if A_eq is not None and sp.issparse(A_eq):
        A_eq = A_eq.toarray()

    t_start = time.perf_counter()
    if getattr(problem, "is_qp", False):
        try:
            cons = []
            if A_eq is not None and len(problem.b_eq) > 0:
                cons.append({'type': 'eq', 'fun': lambda x: A_eq @ x - problem.b_eq, 'jac': lambda x: A_eq})
            if A_ub is not None and len(problem.b_ub) > 0:
                cons.append({'type': 'ineq', 'fun': lambda x: problem.b_ub - A_ub @ x, 'jac': lambda x: -A_ub})

            x0 = np.clip(np.where(np.isfinite(problem.ub), (problem.lb + problem.ub) / 2.0, problem.lb + 1.0), problem.lb, problem.ub)
            res = minimize(
                lambda x: 0.5 * float(x @ problem.Q @ x) + float(problem.c @ x),
                x0,
                jac=lambda x: problem.Q @ x + problem.c,
                bounds=bounds,
                constraints=cons,
                method="SLSQP",
                options={"maxiter": 1000}
            )
            status = "optimal" if res.success else "completed"
            obj_val = float(res.fun)
        except Exception as e:
            status = f"error: {e}"
            obj_val = float("inf")
        device_name = "SciPy-SLSQP"
    else:
        try:
            res = linprog(
                c=problem.c,
                A_ub=A_ub,
                b_ub=problem.b_ub,
                A_eq=A_eq,
                b_eq=problem.b_eq,
                bounds=bounds,
                method="highs",
            )
            status = "optimal" if res.success else "failed"
            obj_val = res.fun if res.success else float("inf")
        except Exception as e:
            status = f"error: {e}"
            obj_val = float("inf")
        device_name = "SciPy-HiGHS"
    t_end = time.perf_counter()

    return {
        "device": device_name,
        "time": t_end - t_start,
        "status": status,
        "obj_val": obj_val,
    }


def run_scaling_benchmark(sizes=None, tol=1e-4, max_iter=5000):
    """
    Run benchmark across problem sizes and return results.

    Returns a list of dicts suitable for JSON/charting.
    """
    if sizes is None:
        sizes = [
            (50, 30),
            (100, 60),
            (200, 120),
            (500, 300),
            (1000, 600),
            (2000, 1200),
            (5000, 3000),
        ]

    results = []
    for n_vars, n_cons in sizes:
        print(f"\n--- Problem size: {n_vars} vars, {n_cons} constraints ---")
        problem = generate_random_lp(n_vars, n_cons)

        # CPU
        print("  Running CPU...")
        cpu_res = benchmark_solver(problem, use_gpu=False, tol=tol, max_iter=max_iter)
        print(f"    CPU: {cpu_res['time']:.4f}s, status={cpu_res['status']}")

        # GPU
        print("  Running GPU...")
        try:
            gpu_res = benchmark_solver(problem, use_gpu=True, tol=tol, max_iter=max_iter)
            print(f"    GPU: {gpu_res['time']:.4f}s, status={gpu_res['status']}")
        except Exception as e:
            print(f"    GPU: Failed ({e})")
            gpu_res = {"device": "GPU", "time": float("inf"), "status": "failed",
                       "obj_val": float("inf")}

        # SciPy
        print("  Running SciPy...")
        scipy_res = benchmark_scipy(problem)
        print(f"    SciPy: {scipy_res['time']:.4f}s, status={scipy_res['status']}")

        speedup = cpu_res["time"] / gpu_res["time"] if gpu_res["time"] > 0 else 0

        results.append({
            "n_vars": n_vars,
            "n_constraints": n_cons,
            "cpu_time": cpu_res["time"],
            "gpu_time": gpu_res["time"],
            "scipy_time": scipy_res["time"],
            "speedup_gpu_vs_cpu": round(speedup, 2),
            "cpu_status": cpu_res["status"],
            "gpu_status": gpu_res["status"],
            "scipy_status": scipy_res["status"],
            "cpu_obj": cpu_res.get("obj_val", None),
            "gpu_obj": gpu_res.get("obj_val", None),
            "scipy_obj": scipy_res.get("obj_val", None),
        })

    return results
