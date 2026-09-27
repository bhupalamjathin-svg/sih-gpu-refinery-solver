"""
cli.py — Command-Line Interface for PDHG-GPU Sovereign Solver
SIH Problem Statement: SIH26119 | Ministry of Petroleum and Natural Gas
"""

import sys
import os
import argparse
import time

# Reconfigure stdout for UTF-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure sih directory is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from solver.pdhg import PDHGSolver
from solver.milp import BranchAndBoundSolver
from solver.mps_parser import parse_mps
from refinery.real_world_data import generate_iocl_refinery_problem, generate_haverly_pooling_problem
from refinery.crude_risk_qp import generate_crude_risk_qp
from refinery.unit_commitment_milp import generate_unit_commitment_milp

# ANSI Colors
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_RESET = "\033[0m"

def print_banner():
    print(f"{C_BOLD}{C_CYAN}======================================================================{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}  PDHG-GPU: Indigenous CUDA Optimization Solver — SIH26119{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}  Ministry of Petroleum & Natural Gas  |  Refinery Digital Twin{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}======================================================================{C_RESET}")

def run_cli():
    print_banner()

    parser = argparse.ArgumentParser(description="Solve LP/QP/MILP using Indigenous PDHG-GPU")
    parser.add_argument("--mps", type=str, help="Path to standard .mps file (e.g., sample_afiro.mps)")
    parser.add_argument("--preset", type=str, default="iocl_bs6",
                        choices=["iocl_bs6", "haverly", "crude_qp", "unit_milp", "afiro"],
                        help="Bundled preset refinery/benchmark problem")
    parser.add_argument("--gpu", action="store_true", default=True, help="Use CUDA GPU acceleration (default: True)")
    parser.add_argument("--cpu", action="store_true", help="Force CPU NumPy execution")
    parser.add_argument("--tol", type=float, default=1e-4, help="KKT convergence tolerance (default: 1e-4)")
    parser.add_argument("--max-iter", type=int, default=10000, help="Maximum PDHG iterations (default: 10000)")

    args = parser.parse_args()
    use_gpu = not args.cpu

    # 1. Load Problem
    if args.mps:
        if not os.path.exists(args.mps):
            print(f"{C_RED}[ERROR] File not found: {args.mps}{C_RESET}")
            sys.exit(1)
        print(f"\n{C_BOLD}Loading MPS File:{C_RESET} {args.mps}")
        prob = parse_mps(args.mps)
    else:
        print(f"\n{C_BOLD}Loading Preset Problem:{C_RESET} {args.preset.upper()}")
        if args.preset == "iocl_bs6":
            prob = generate_iocl_refinery_problem()
        elif args.preset == "haverly":
            prob = generate_haverly_pooling_problem()
        elif args.preset == "crude_qp":
            prob = generate_crude_risk_qp()
        elif args.preset == "unit_milp":
            prob = generate_unit_commitment_milp()
        elif args.preset == "afiro":
            prob = parse_mps(os.path.join(os.path.dirname(__file__), "sample_afiro.mps"))

    print(f"  • Problem Name:        {C_BOLD}{prob.name}{C_RESET}")
    print(f"  • Problem Class:       {C_BOLD}{prob.problem_class.upper()}{C_RESET}")
    print(f"  • Variables:           {prob.n_vars:,}")
    print(f"  • Constraints:         {prob.n_constraints:,} ({prob.n_eq} equality, {prob.n_ub} inequality)")
    print(f"  • Target Hardware:     {C_GREEN if use_gpu else C_YELLOW}{'NVIDIA CUDA GPU' if use_gpu else 'CPU (Fallback)'}{C_RESET}")

    # 2. Solve
    start_t = time.perf_counter()
    if prob.is_milp:
        print(f"\n{C_CYAN}>> Initializing GPU-Accelerated Branch-and-Bound Engine...{C_RESET}")
        solver = BranchAndBoundSolver(max_nodes=150, time_limit=30.0, use_gpu=use_gpu, verbose=True)
        res = solver.solve(prob)
        elapsed = time.perf_counter() - start_t

        print(f"\n{C_BOLD}{C_GREEN}================ SOLUTION RESULTS (MILP) ================{C_RESET}")
        print(f"  • Status:              {C_BOLD}{res.status.upper()}{C_RESET}")
        print(f"  • Best Integer Obj:    {C_BOLD}{C_GREEN}{res.obj_val:,.2f}{C_RESET}")
        print(f"  • Optimality Gap:      {res.mip_gap * 100:.2f}%")
        print(f"  • Explored Nodes:      {res.nodes_explored}")
        print(f"  • Total Solve Time:    {elapsed:.4f} seconds")
    else:
        print(f"\n{C_CYAN}>> Initializing Chambolle-Pock PDHG + Ruiz Preconditioning...{C_RESET}")
        solver = PDHGSolver(max_iterations=args.max_iter, tol=args.tol, use_gpu=use_gpu, verbose=False)
        res = solver.solve(prob)
        elapsed = time.perf_counter() - start_t

        print(f"\n{C_BOLD}{C_GREEN}================ SOLUTION RESULTS ================{C_RESET}")
        print(f"  • Status:              {C_BOLD}{res.status.upper()}{C_RESET}")
        print(f"  • Optimal Objective:   {C_BOLD}{C_GREEN}{res.obj_val:,.2f}{C_RESET}")
        print(f"  • Iterations:          {res.n_iterations:,}")
        print(f"  • Total Solve Time:    {elapsed:.4f} seconds ({elapsed*1000/max(res.n_iterations,1):.2f} ms/iter)")
        print(f"  • Primal Residual:     {res.primal_residual:.2e}  (tol: {args.tol})")
        print(f"  • Dual Residual:       {res.dual_residual:.2e}  (tol: {args.tol})")
        print(f"  • Relative Gap:        {res.duality_gap:.2e}")

        # Debottlenecking Table
        if res.shadow_prices:
            print(f"\n{C_BOLD}{C_YELLOW}--- TOP REFINERY EQUIPMENT & QUALITY BOTTLENECKS ---{C_RESET}")
            print(f"  {'Constraint / Unit':<32} {'Shadow Price ($)':<18} {'Status'}")
            print(f"  {'-'*32} {'-'*18} {'-'*12}")
            sorted_sp = sorted(res.shadow_prices, key=lambda x: abs(x.get('shadow_price', 0)), reverse=True)
            for item in sorted_sp[:8]:
                name = item.get('name', 'Unknown')
                sp = item.get('shadow_price', 0.0)
                color = C_RED if abs(sp) > 10 else C_YELLOW
                status_tag = f"{C_RED}[BOTTLENECK]{C_RESET}" if abs(sp) > 10 else f"{C_YELLOW}ACTIVE{C_RESET}"
                print(f"  {name:<32} {color}{sp:>16.2f}{C_RESET}   {status_tag}")

    print(f"\n{C_BOLD}{C_CYAN}======================================================================{C_RESET}\n")

if __name__ == "__main__":
    run_cli()
