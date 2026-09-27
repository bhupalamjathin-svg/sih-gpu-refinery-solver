"""
Mixed-Integer Linear Programming (MILP) Solver via Branch-and-Bound.

Built strictly from mathematical foundation on top of our GPU PDHG LP solver.
Does NOT call or depend on any open-source or commercial MIP solver libraries.

Mathematical Algorithm:
  1. Solve continuous LP relaxation at the root node using GPU PDHG.
  2. If all integer variables satisfy integrality, root solution is globally optimal.
  3. Otherwise, pick the most fractional integer variable x_j.
  4. Create two sub-problems (branches):
       Branch Floor:  x_j <= floor(x_j*)
       Branch Ceil:   x_j >= ceil(x_j*)
  5. Explore nodes using Best-Bound Search (priority queue).
  6. Prune sub-trees by:
       - Infeasibility (relaxation is infeasible)
       - Bound (relaxation objective >= incumbent best integer objective)
       - Integrality (all integer variables are integer -> update incumbent)
"""

import time
import heapq
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import numpy as np

from .problem import OptimizationProblem
from .pdhg import PDHGSolver, SolveResult


@dataclass
class MILPResult:
    """Result of Branch-and-Bound MILP solve."""
    x: np.ndarray
    obj_val: float
    status: str
    solve_time: float
    nodes_explored: int
    mip_gap: float
    device: str
    incumbent_history: List[Dict[str, Any]] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"=== MILP Solve Summary ===\n"
            f"  Status:          {self.status}\n"
            f"  Objective:       {self.obj_val:.6f}\n"
            f"  Nodes Explored:  {self.nodes_explored}\n"
            f"  MIP Gap:         {self.mip_gap * 100:.2f}%\n"
            f"  Solve Time:      {self.solve_time:.4f}s ({self.device})\n"
        )


class BranchAndBoundSolver:
    """
    Branch-and-Bound Mixed-Integer Linear Programming (MILP) Solver.
    
    Evaluates continuous node relaxations natively on GPU via PDHGSolver.
    """

    def __init__(
        self,
        max_nodes: int = 1000,
        time_limit: float = 30.0,
        tol_integer: float = 1e-4,
        mip_gap_tol: float = 1e-4,
        use_gpu: bool = True,
        node_lp_max_iter: int = 2500,
        verbose: bool = False,
    ):
        self.max_nodes = max_nodes
        self.time_limit = time_limit
        self.tol_integer = tol_integer
        self.mip_gap_tol = mip_gap_tol
        self.use_gpu = use_gpu
        self.node_lp_max_iter = node_lp_max_iter
        self.verbose = verbose

    def solve(self, problem: OptimizationProblem) -> MILPResult:
        """
        Solve a Mixed-Integer Linear Program.

        Parameters
        ----------
        problem : OptimizationProblem with integer/binary variables

        Returns
        -------
        MILPResult
        """
        t0 = time.perf_counter()
        int_indices = problem.integer_indices

        if len(int_indices) == 0:
            # Pure LP: solve directly
            lp_solver = PDHGSolver(
                max_iterations=self.node_lp_max_iter,
                use_gpu=self.use_gpu,
                verbose=self.verbose,
            )
            lp_res = lp_solver.solve(problem)
            return MILPResult(
                x=lp_res.x,
                obj_val=lp_res.obj_val,
                status=lp_res.status,
                solve_time=time.perf_counter() - t0,
                nodes_explored=1,
                mip_gap=0.0,
                device=lp_res.device,
                incumbent_history=[{"node": 1, "time": lp_res.solve_time, "obj": lp_res.obj_val}],
            )

        # Initialize LP solver for node evaluations
        lp_solver = PDHGSolver(
            max_iterations=self.node_lp_max_iter,
            tol=1e-4,
            use_gpu=self.use_gpu,
            verbose=False,
        )

        best_obj = float("inf")
        best_x = None
        global_lower_bound = float("-inf")
        nodes_explored = 0
        incumbent_history = []

        # Priority queue stores tuples: (lower_bound_estimate, node_id, current_lb, current_ub)
        node_counter = 0
        queue = []

        # Root node
        root_lb = problem.lb.copy()
        root_ub = problem.ub.copy()
        heapq.heappush(queue, (0.0, node_counter, root_lb, root_ub))

        status = "time_limit"

        while queue:
            elapsed = time.perf_counter() - t0
            if elapsed > self.time_limit:
                status = "time_limit"
                break
            if nodes_explored >= self.max_nodes:
                status = "node_limit"
                break

            # Pop best bound node
            est_bound, _, curr_lb, curr_ub = heapq.heappop(queue)

            # Prune if bound cannot beat incumbent
            if est_bound >= best_obj - 1e-6:
                continue

            nodes_explored += 1

            # Formulate node relaxation
            node_prob = OptimizationProblem(
                c=problem.c,
                Q=problem.Q,
                A_ub=problem.A_ub,
                b_ub=problem.b_ub,
                A_eq=problem.A_eq,
                b_eq=problem.b_eq,
                lb=curr_lb,
                ub=curr_ub,
                name=f"Node-{nodes_explored}",
            )

            # Solve relaxation on GPU
            res: SolutionResult = lp_solver.solve(node_prob)

            if res.status not in ("optimal", "iteration_limit") or res.primal_residual > 1e-2:
                # Node is infeasible or divergent -> prune
                continue

            node_obj = res.obj_val
            node_x = res.x

            # Prune by bound
            if node_obj >= best_obj - 1e-6:
                continue

            # Check integrality
            fractional_candidates = []
            for j in int_indices:
                val = node_x[j]
                rounded = round(val)
                frac_dist = abs(val - rounded)
                if frac_dist > self.tol_integer:
                    # Score by distance to nearest integer (most fractional)
                    fractional_candidates.append((min(val - np.floor(val), np.ceil(val) - val), j, val))

            if len(fractional_candidates) == 0:
                # Integer feasible solution found!
                if node_obj < best_obj:
                    best_obj = node_obj
                    best_x = node_x.copy()
                    now = time.perf_counter() - t0
                    incumbent_history.append({
                        "node": nodes_explored,
                        "time": round(now, 4),
                        "obj": round(best_obj, 6),
                    })
                    if self.verbose:
                        print(f"  [B&B Node {nodes_explored:4d}] New Incumbent: {best_obj:.6f} at t={now:.2f}s")

                # Check gap
                if queue and queue[0][0] != float("-inf"):
                    global_lower_bound = queue[0][0]
                    gap = abs(best_obj - global_lower_bound) / (1.0 + abs(best_obj))
                    if gap <= self.mip_gap_tol:
                        status = "optimal"
                        break
                continue

            # Branch on most fractional variable
            fractional_candidates.sort(reverse=True, key=lambda c: c[0])
            _, branch_var, branch_val = fractional_candidates[0]

            floor_val = np.floor(branch_val)
            ceil_val = np.ceil(branch_val)

            # Child 1: x_j <= floor(x_j)
            if curr_lb[branch_var] <= floor_val:
                child1_lb = curr_lb.copy()
                child1_ub = curr_ub.copy()
                child1_ub[branch_var] = min(child1_ub[branch_var], floor_val)
                node_counter += 1
                heapq.heappush(queue, (node_obj, node_counter, child1_lb, child1_ub))

            # Child 2: x_j >= ceil(x_j)
            if curr_ub[branch_var] >= ceil_val:
                child2_lb = curr_lb.copy()
                child2_ub = curr_ub.copy()
                child2_lb[branch_var] = max(child2_lb[branch_var], ceil_val)
                node_counter += 1
                heapq.heappush(queue, (node_obj, node_counter, child2_lb, child2_ub))

        # Check final status
        if best_x is not None:
            if not queue:
                status = "optimal"
            global_lb = queue[0][0] if queue else best_obj
            mip_gap = max(0.0, abs(best_obj - global_lb) / (1.0 + abs(best_obj)))
        else:
            status = "infeasible"
            best_obj = float("inf")
            best_x = np.zeros(problem.n_vars)
            mip_gap = 1.0

        total_time = time.perf_counter() - t0
        device_used = "gpu" if self.use_gpu else "cpu"

        return MILPResult(
            x=best_x,
            obj_val=best_obj,
            status=status,
            solve_time=total_time,
            nodes_explored=nodes_explored,
            mip_gap=mip_gap,
            device=device_used,
            incumbent_history=incumbent_history,
        )
