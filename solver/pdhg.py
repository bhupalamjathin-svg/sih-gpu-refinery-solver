"""
PDHG (Primal-Dual Hybrid Gradient) Solver for Linear Programming.

Solves:
    minimize    c^T x
    subject to  A_ub x <= b_ub
                A_eq x  = b_eq
                lb <= x <= ub

By converting to saddle-point form and iterating:
    y_{k+1}     = y_k + sigma * (K x_bar_k - q)
    [project inequality duals to >= 0]
    x_{k+1}     = proj_{[lb,ub]}(x_k - tau * (c + K^T y_{k+1}))
    x_bar_{k+1} = x_{k+1} + theta * (x_{k+1} - x_k)

The saddle-point formulation is:
    min_{lb<=x<=ub} max_{y>=0 for ub rows}  c^T x + y^T (K x - q)

where K = [A_eq; A_ub], q = [b_eq; b_ub].

At optimality:
  - Primal feasibility: K_eq x = q_eq,  K_ub x <= q_ub
  - Dual feasibility:   c + K^T y has correct sign w.r.t. bounds
  - Complementarity:    y_ub >= 0

References:
  - Chambolle & Pock (2011)
  - Applegate et al. (2021) — PDLP
  - Lu & Yang (2023) — cuPDLP
"""

import time
from dataclasses import dataclass, field
from typing import Optional, List

import numpy as np
import scipy.sparse as sp

from .problem import LPProblem
from .preprocess import (
    get_backend,
    to_device,
    from_device,
    ruiz_rescaling,
    estimate_operator_norm,
)


@dataclass
class SolveResult:
    """Result of solving an LP."""

    status: str  # "optimal", "iteration_limit", "infeasible", "error"
    x: Optional[np.ndarray] = None  # primal solution
    y: Optional[np.ndarray] = None  # dual solution
    obj_val: float = float("inf")  # optimal objective value
    n_iterations: int = 0
    solve_time: float = 0.0
    primal_residual: float = float("inf")
    dual_residual: float = float("inf")
    duality_gap: float = float("inf")
    convergence_log: List[dict] = field(default_factory=list)
    device: str = "cpu"
    shadow_prices: List[dict] = field(default_factory=list)
    binding_constraints: List[dict] = field(default_factory=list)
    equipment_bottlenecks: List[dict] = field(default_factory=list)
    var_names: Optional[list] = None

    def to_dict(self) -> dict:
        """Serialize for JSON."""
        return {
            "status": self.status,
            "x": self.x.tolist() if self.x is not None else None,
            "obj_val": float(self.obj_val),
            "n_iterations": self.n_iterations,
            "solve_time": self.solve_time,
            "primal_residual": float(self.primal_residual),
            "dual_residual": float(self.dual_residual),
            "duality_gap": float(self.duality_gap),
            "convergence_log": self.convergence_log,
            "device": self.device,
            "var_names": self.var_names,
            "shadow_prices": self.shadow_prices,
            "binding_constraints": self.binding_constraints,
            "equipment_bottlenecks": self.equipment_bottlenecks,
        }


class PDHGSolver:
    """
    GPU-accelerated PDHG solver for linear programming.

    Parameters
    ----------
    max_iterations : int
        Maximum number of PDHG iterations.
    tol : float
        Convergence tolerance for KKT residuals.
    use_gpu : bool
        Whether to attempt GPU acceleration via CuPy.
    use_preconditioning : bool
        Whether to apply Ruiz equilibration.
    theta : float
        Over-relaxation parameter (1.0 = standard).
    log_interval : int
        Log convergence metrics every N iterations.
    verbose : bool
        Print progress to stdout.
    """

    def __init__(
        self,
        max_iterations: int = 10000,
        tol: float = 1e-4,
        use_gpu: bool = True,
        use_preconditioning: bool = True,
        theta: float = 1.0,
        log_interval: int = 50,
        verbose: bool = False,
    ):
        self.max_iterations = max_iterations
        self.tol = tol
        self.use_gpu = use_gpu
        self.use_preconditioning = use_preconditioning
        self.theta = theta
        self.log_interval = log_interval
        self.verbose = verbose

    def solve(self, problem: LPProblem) -> SolveResult:
        """
        Solve the given LP problem using PDHG.
        """
        t_start = time.perf_counter()

        # --- Setup backend ---
        xp, xsp, is_gpu = get_backend(self.use_gpu)
        device = "gpu" if is_gpu else "cpu"

        if self.verbose:
            print(f"[PDHG] Backend: {'CuPy (GPU)' if is_gpu else 'NumPy (CPU)'}")
            print(f"[PDHG] {problem.summary()}")

        # --- Build constraint matrix K and RHS q ---
        # K = [A_eq; A_ub],  q = [b_eq; b_ub]
        # Saddle point: min_{lb<=x<=ub} max_{y}  c^T x + y^T(Kx - q)
        # with y_i unconstrained for eq rows, y_i >= 0 for ub rows
        K_np, q_np, constraint_types = problem.to_saddle_point()
        c_np = np.asarray(problem.c, dtype=np.float64).ravel()
        lb_np = np.asarray(problem.lb, dtype=np.float64).ravel()
        ub_np = np.asarray(problem.ub, dtype=np.float64).ravel()

        m, n = K_np.shape

        # --- Preconditioning (Ruiz diagonal scaling on CPU to avoid CUDA NVRTC reduction bug) ---
        # After Ruiz: K_s = D_r K D_c, so the problem becomes:
        #   min c_s^T x_s  s.t.  K_s x_s <= q_s   with x_s = D_c^{-1} x
        #   c_s = D_c c,  q_s = D_r q,  lb_s = D_c^{-1} lb,  ub_s = D_c^{-1} ub
        if self.use_preconditioning and m > 0:
            K_s_np, c_s_np, q_s_np, row_scale_np, col_scale_np = ruiz_rescaling(
                K_np, c_np.copy(), q_np.copy(), n_iterations=10, xp=np, xsp=sp
            )
            lb_s_np = lb_np / col_scale_np
            ub_s_np = ub_np / col_scale_np
            lb_s_np = np.where(np.isinf(lb_np), lb_np, lb_s_np)
            ub_s_np = np.where(np.isinf(ub_np), ub_np, ub_s_np)
        else:
            K_s_np = K_np
            c_s_np = c_np.copy()
            q_s_np = q_np.copy() if len(q_np) > 0 else q_np
            lb_s_np = lb_np.copy()
            ub_s_np = ub_np.copy()
            col_scale_np = np.ones(n, dtype=np.float64)
            row_scale_np = np.ones(m, dtype=np.float64) if m > 0 else np.array([], dtype=np.float64)

        # --- Transfer preconditioned problem to target device (GPU or CPU) ---
        K = to_device(K_s_np, xp, xsp, is_gpu)
        c_s = to_device(c_s_np, xp, xsp, is_gpu)
        q_s = to_device(q_s_np, xp, xsp, is_gpu) if len(q_s_np) > 0 else xp.array([], dtype=xp.float64)
        lb_s = to_device(lb_s_np, xp, xsp, is_gpu)
        ub_s = to_device(ub_s_np, xp, xsp, is_gpu)
        col_scale = to_device(col_scale_np, xp, xsp, is_gpu)
        row_scale = to_device(row_scale_np, xp, xsp, is_gpu)

        # --- Quadratic objective support (QP) ---
        is_qp = problem.is_qp
        if is_qp:
            Q_np = problem.Q
            if self.use_preconditioning and m > 0:
                if sp.issparse(Q_np):
                    Q_s_np = sp.diags(col_scale_np) @ Q_np @ sp.diags(col_scale_np)
                else:
                    Q_s_np = col_scale_np[:, None] * Q_np * col_scale_np[None, :]
            else:
                Q_s_np = Q_np
            Q_s = to_device(Q_s_np, xp, xsp, is_gpu)
            norm_Q = estimate_operator_norm(Q_s, n_iterations=20, xp=xp, xsp=xsp)
        else:
            Q_s = None
            norm_Q = 0.0

        # --- Step sizes via power iteration with dynamic primal-dual balancing ---
        norm_K = estimate_operator_norm(K, n_iterations=30, xp=xp, xsp=xsp) if m > 0 else 1.0
        norm_K = max(norm_K, 1e-10)

        # Balance primal-dual step sizes (PDLP/Applegate et al. 2021)
        norm_c = float(xp.linalg.norm(c_s)) if n > 0 else 1.0
        norm_q = float(xp.linalg.norm(q_s)) if m > 0 else 1.0
        omega = float(np.sqrt((norm_c + 1.0) / (norm_q + 1.0)))

        if is_qp:
            # For QP, tau * (sigma * ||K||^2 + ||Q||) < 1 is strictly required for stability
            tau = 0.95 / (norm_K * omega + norm_Q)
            sigma = (0.95 / norm_K) * omega
        else:
            tau = (0.95 / norm_K) / omega
            sigma = (0.95 / norm_K) * omega

        if self.verbose:
            print(f"[PDHG] ||K|| ~ {norm_K:.4f}, ||Q|| ~ {norm_Q:.4f}, omega={omega:.4f}, tau={tau:.6f}, sigma={sigma:.6f}")

        # --- Inequality mask ---
        n_eq = sum(1 for t in constraint_types if t == "eq")
        # ub constraints start at index n_eq
        has_eq = n_eq > 0
        has_ub = n_eq < m

        # --- Initialize ---
        x = xp.zeros(n, dtype=xp.float64)
        # Initialize x at midpoint only when bounds are tight and genuinely finite (< 1e5)
        tight_bounds = xp.isfinite(lb_s) & xp.isfinite(ub_s) & (ub_s < 1e5) & (lb_s > -1e5) & (ub_s > lb_s)
        x = xp.where(tight_bounds, (lb_s + ub_s) / 2.0, x)
        # Clamp initial x to valid range [lb_s, ub_s]
        x = xp.clip(x, lb_s, ub_s)

        y = xp.zeros(m, dtype=xp.float64) if m > 0 else xp.array([], dtype=xp.float64)
        x_bar = x.copy()

        K_T = K.T

        # --- Convergence tracking ---
        convergence_log = []
        best_kkt = float("inf")
        best_x = x.copy()
        best_y = y.copy() if m > 0 else xp.array([], dtype=xp.float64)

        # For adaptive restart
        prev_kkt = float("inf")

        # --- Main PDHG loop ---
        status = "iteration_limit"
        final_iter = self.max_iterations

        # Initialize custom CUDA kernels if on GPU
        cuda_kernels = None
        if is_gpu:
            try:
                from .cuda_kernels import CUDASolverKernels
                cuda_kernels = CUDASolverKernels()
                if self.verbose:
                    print("[PDHG] Compiled custom CUDA C++ kernels for RTX 4070 SM acceleration.")
            except Exception as e:
                if self.verbose:
                    print(f"[PDHG] Warning: Custom CUDA kernel compilation fallback: {e}")
                cuda_kernels = None

        for k in range(self.max_iterations):
            x_old = x.copy()

            # === Dual update ===
            # y_{k+1} = y_k + sigma * (K @ x_bar - q)
            # clamped at 0 for inequality rows (indices >= n_eq)
            if m > 0:
                Kx_bar = K @ x_bar
                if cuda_kernels is not None:
                    cuda_kernels.launch_dual_update(Kx_bar, q_s, y, sigma, n_eq, m)
                else:
                    y = y + sigma * (Kx_bar - q_s)
                    if has_ub:
                        y[n_eq:] = xp.maximum(y[n_eq:], 0.0)

            # === Primal update ===
            # x_{k+1} = proj_{[lb,ub]}(x - tau * (c + Qx + K^T @ y))
            # x_bar_{k+1} = x_{k+1} + theta * (x_{k+1} - x_k)
            if m > 0:
                KTy = K_T @ y
            else:
                KTy = None

            Qx = (Q_s @ x) if is_qp else None

            if cuda_kernels is not None:
                cuda_kernels.launch_primal_update(c_s, KTy, Qx, lb_s, ub_s, x, x_bar, tau, self.theta, n)
            else:
                grad = c_s.copy()
                if Qx is not None:
                    grad = grad + Qx
                if KTy is not None:
                    grad = grad + KTy
                x = xp.clip(x_old - tau * grad, lb_s, ub_s)
                x_bar = x + self.theta * (x - x_old)

            # === Convergence check ===
            if (k + 1) % self.log_interval == 0 or k == 0:
                # Compute residuals directly on the active device (GPU or CPU) without PCIe roundtrips
                if m > 0:
                    Kx_curr = K @ x
                    p_viol = xp.zeros(m, dtype=xp.float64)
                    if has_eq:
                        p_viol[:n_eq] = Kx_curr[:n_eq] - q_s[:n_eq]
                    if has_ub:
                        p_viol[n_eq:] = xp.maximum(Kx_curr[n_eq:] - q_s[n_eq:], 0.0)
                    primal_res = float(xp.linalg.norm(p_viol)) / (1.0 + float(xp.linalg.norm(q_s)))
                else:
                    primal_res = 0.0

                # Dual violation (stationarity: grad = c + Qx + K^T y)
                grad_curr = c_s.copy()
                if is_qp:
                    grad_curr = grad_curr + (Q_s @ x)
                if m > 0 and KTy is not None:
                    grad_curr = grad_curr + KTy

                dual_viol = xp.zeros(n, dtype=xp.float64)
                if cuda_kernels is not None:
                    cuda_kernels.launch_kkt_violation(grad_curr, x, lb_s, ub_s, dual_viol, n)
                else:
                    at_lb = xp.abs(x - lb_s) < 1e-8 * (1.0 + xp.abs(lb_s))
                    at_ub = xp.abs(x - ub_s) < 1e-8 * (1.0 + xp.abs(ub_s))
                    interior = ~at_lb & ~at_ub
                    dual_viol[at_lb] = xp.minimum(grad_curr[at_lb], 0.0)
                    dual_viol[at_ub] = xp.maximum(grad_curr[at_ub], 0.0)
                    dual_viol[interior] = grad_curr[interior]

                dual_res = float(xp.linalg.norm(dual_viol)) / (1.0 + float(xp.linalg.norm(c_s)))
                kkt = max(primal_res, dual_res)

                # Duality gap & objectives directly on device
                primal_obj = float((c_s * x).sum())
                if is_qp:
                    primal_obj += 0.5 * float((x * (Q_s @ x)).sum())
                dual_obj = float((-q_s * y).sum()) if m > 0 else primal_obj
                if is_qp:
                    dual_obj -= 0.5 * float((x * (Q_s @ x)).sum())
                gap = abs(primal_obj - dual_obj) / (1.0 + abs(primal_obj) + abs(dual_obj))

                convergence_log.append({
                    "iteration": k + 1,
                    "primal_res": primal_res,
                    "dual_res": dual_res,
                    "gap": gap,
                    "primal_obj": primal_obj,
                    "dual_obj": dual_obj,
                })

                if self.verbose and (k + 1) % (self.log_interval * 4) == 0:
                    print(
                        f"  iter {k+1:6d} | "
                        f"p_res={primal_res:.2e} | "
                        f"d_res={dual_res:.2e} | "
                        f"gap={gap:.2e} | "
                        f"obj={primal_obj:.6f}"
                    )

                # Track best iterate
                if kkt < best_kkt:
                    best_kkt = kkt
                    best_x = x.copy()
                    best_y = y.copy() if m > 0 else xp.array([], dtype=xp.float64)

                # Convergence check
                if kkt < self.tol:
                    status = "optimal"
                    final_iter = k + 1
                    break

                # Adaptive restart: if KKT residual increased significantly
                if kkt > prev_kkt * 1.2 and k > 200:
                    x_bar = x.copy()
                    if self.verbose:
                        print(f"  [restart at iter {k+1}]")

                prev_kkt = kkt

        # --- Extract best solution ---
        x_final = from_device(best_x * col_scale, is_gpu)
        y_final = from_device(
            best_y * row_scale if m > 0 else best_y, is_gpu
        )

        obj_val = float(c_np @ x_final)
        if is_qp and problem.Q is not None:
            obj_val += 0.5 * float(x_final @ (problem.Q @ x_final))

        # Final residual computation
        if m > 0:
            Kx_final = K_np @ x_final
            p_viol = np.zeros(m)
            if has_eq:
                p_viol[:n_eq] = Kx_final[:n_eq] - q_np[:n_eq]
            if has_ub:
                p_viol[n_eq:] = np.maximum(Kx_final[n_eq:] - q_np[n_eq:], 0.0)
            final_pres = float(np.linalg.norm(p_viol)) / (1.0 + float(np.linalg.norm(q_np)))

            grad_final = c_np.copy()
            if is_qp and problem.Q is not None:
                grad_final += problem.Q @ x_final
            grad_final += K_np.T @ y_final

            d_viol = np.zeros(n)
            at_lb = np.abs(x_final - lb_np) < 1e-8
            at_ub = np.abs(x_final - ub_np) < 1e-8
            interior = ~at_lb & ~at_ub
            d_viol[at_lb] = np.minimum(grad_final[at_lb], 0.0)
            d_viol[at_ub] = np.maximum(grad_final[at_ub], 0.0)
            d_viol[interior] = grad_final[interior]
            final_dres = float(np.linalg.norm(d_viol)) / (1.0 + float(np.linalg.norm(c_np)))

            dual_obj_final = float(-q_np @ y_final)
            final_gap = abs(obj_val - dual_obj_final) / (1.0 + abs(obj_val) + abs(dual_obj_final))
        else:
            final_pres = 0.0
            final_dres = 0.0
            final_gap = 0.0

        # --- Economic Shadow Prices & Marginal Dual Analysis ---
        shadow_prices = []
        equipment_bottlenecks = []
        material_balances = []
        binding_constraints = []

        if m > 0 and y_final is not None:
            c_names = problem.constraint_names or [f"Constraint_{i}" for i in range(m)]
            for i in range(m):
                is_eq = (i < n_eq)
                c_name = c_names[i] if i < len(c_names) else f"Row_{i}"
                lhs_val = float(Kx_final[i])
                rhs_val = float(q_np[i])
                dual_val = float(y_final[i])
                slack_val = 0.0 if is_eq else (rhs_val - lhs_val)

                # A constraint is an equipment bottleneck if inequality slack is near 0 and dual is active
                scale_ref = max(1.0, abs(rhs_val))
                is_capacity_bottleneck = (not is_eq) and (abs(slack_val) / scale_ref < 1e-2 or abs(slack_val) < 50.0) and (abs(dual_val) > 1e-3)

                # Classify constraint type
                if is_eq:
                    c_type = "Material Balance (Eq)"
                elif "RON" in c_name or "Sulfur" in c_name or "Spec" in c_name:
                    c_type = "BS-VI Quality Spec"
                elif "Capacity" in c_name or "Max" in c_name or "Limit" in c_name:
                    c_type = "Unit Capacity Ceiling"
                else:
                    c_type = "Operating Inequality"

                # Economic interpretation
                if c_type == "BS-VI Quality Spec":
                    if "RON" in c_name:
                        impact = f"Active BS-VI Octane Spec: 1.0 pt RON relaxation expands daily margin by +${abs(dual_val):,.2f}/RON-bbl"
                    elif "Sulfur" in c_name:
                        impact = f"Active BS-VI Sulfur Spec (<10 ppm): 1.0 ppm diesel sulfur relaxation expands margin by +${abs(dual_val):,.2f}/ppm-bbl"
                    else:
                        impact = f"Active Quality Specification: shadow price ${abs(dual_val):.2f} / unit"
                elif is_capacity_bottleneck and ("bpd" in c_name or "Capacity" in c_name or "Max" in c_name):
                    impact = f"CRITICAL BOTTLENECK: Debottlenecking by 1,000 bpd expands net margin by +${abs(dual_val)*1000:,.1f}/day (+${abs(dual_val)*365000:,.1f}/yr)"
                elif is_capacity_bottleneck:
                    impact = f"Binding Capacity Limit: expanding boundary by 1 unit improves objective by +${abs(dual_val):.2f}"
                elif is_eq:
                    impact = f"Material Balance: stream marginal economic value ${abs(dual_val):.2f} / unit"
                elif abs(dual_val) > 1e-4:
                    impact = f"Active Constraint: marginal price ${abs(dual_val):.2f} / unit"
                else:
                    impact = f"Non-binding Constraint: {slack_val:,.1f} slack headroom available"

                item = {
                    "index": i,
                    "name": c_name,
                    "type": c_type,
                    "lhs": round(lhs_val, 2),
                    "rhs": round(rhs_val, 2),
                    "slack": round(slack_val, 2),
                    "shadow_price": round(abs(dual_val), 4),
                    "is_binding": is_capacity_bottleneck,
                    "is_eq": is_eq,
                    "economic_impact": impact,
                }
                shadow_prices.append(item)
                if is_capacity_bottleneck:
                    equipment_bottlenecks.append(item)
                elif is_eq and abs(dual_val) > 1e-4:
                    material_balances.append(item)

            # Sort bottlenecks by economic shadow price descending
            equipment_bottlenecks.sort(key=lambda x: x["shadow_price"], reverse=True)
            material_balances.sort(key=lambda x: x["shadow_price"], reverse=True)
            # Binding constraints puts physical equipment bottlenecks first, followed by key stream balances
            binding_constraints = equipment_bottlenecks + material_balances

        solve_time = time.perf_counter() - t_start

        if self.verbose:
            print(f"[PDHG] Status: {status}")
            print(f"[PDHG] Objective: {obj_val:.8f}")
            print(f"[PDHG] Time: {solve_time:.4f}s")
            print(f"[PDHG] Iterations: {final_iter}")
            if binding_constraints:
                print(f"[PDHG] Top Bottleneck: {binding_constraints[0]['name']} (Shadow Price: {binding_constraints[0]['shadow_price']:.4f})")

        return SolveResult(
            status=status,
            x=x_final,
            y=y_final,
            obj_val=obj_val,
            n_iterations=final_iter,
            solve_time=solve_time,
            primal_residual=final_pres,
            dual_residual=final_dres,
            duality_gap=final_gap,
            convergence_log=convergence_log,
            device=device,
            var_names=problem.var_names,
            shadow_prices=shadow_prices,
            binding_constraints=binding_constraints,
            equipment_bottlenecks=equipment_bottlenecks,
        )
