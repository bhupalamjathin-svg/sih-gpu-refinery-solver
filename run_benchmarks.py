#!/usr/bin/env python3
"""
Standalone benchmark runner for the PDHG GPU LP Solver.

Usage:
    python run_benchmarks.py                    # Run scaling benchmarks
    python run_benchmarks.py --validate         # Cross-validate against SciPy
    python run_benchmarks.py --refinery         # Benchmark refinery presets
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from solver.pdhg import PDHGSolver
from solver.benchmarks import (
    run_scaling_benchmark,
    benchmark_solver,
    benchmark_scipy,
    generate_random_lp,
)
from refinery.blending import generate_blending_problem
from refinery.scheduling import generate_scheduling_problem
from refinery.resource_alloc import generate_resource_allocation_problem


def print_banner():
    print("=" * 65)
    print("  PDHG-GPU: Indigenous CUDA LP Solver — Benchmark Suite")
    print("  SIH Problem Statement: SIH26119")
    print("=" * 65)
    print()


def validate_solver():
    """Cross-validate PDHG against SciPy linprog on small problems."""
    print("\n--- Cross-Validation: PDHG vs SciPy ---\n")

    problems = [
        generate_random_lp(10, 5, seed=1),
        generate_random_lp(50, 30, seed=2),
        generate_random_lp(100, 60, seed=3),
        generate_blending_problem(4, 3),
        generate_scheduling_problem(3, 2, 2),
        generate_resource_allocation_problem(3, 3),
    ]

    for prob in problems:
        print(f"\n  Problem: {prob.name}")
        print(f"  Size: {prob.n_vars} vars, {prob.n_constraints} constraints")

        # PDHG
        solver = PDHGSolver(max_iterations=10000, tol=1e-4, use_gpu=False, verbose=False)
        pdhg_result = solver.solve(prob)

        # SciPy
        scipy_result = benchmark_scipy(prob)

        print(f"  PDHG:  obj={pdhg_result.obj_val:.4f}  status={pdhg_result.status}  "
              f"time={pdhg_result.solve_time:.4f}s  iter={pdhg_result.n_iterations}")
        print(f"  SciPy: obj={scipy_result['obj_val']:.4f}  status={scipy_result['status']}  "
              f"time={scipy_result['time']:.4f}s")

        if pdhg_result.status == "optimal" and scipy_result["status"] == "optimal":
            diff = abs(pdhg_result.obj_val - scipy_result["obj_val"])
            rel_diff = diff / max(abs(scipy_result["obj_val"]), 1e-10)
            status = "✓ PASS" if rel_diff < 0.01 else "✗ FAIL"
            print(f"  Δobj={diff:.6f} (relative: {rel_diff:.2e})  {status}")
        else:
            print(f"  ⚠ Cannot compare — one solver didn't reach optimal")


def benchmark_refinery():
    """Benchmark all refinery presets."""
    print("\n--- Refinery Preset Benchmarks ---\n")

    presets = [
        ("Blending (Pilot 4×3)", generate_blending_problem(4, 3)),
        ("Blending (Industrial 50×20)", generate_blending_problem(50, 20, 50000)),
        ("Multi-Unit Sched (60-Day)", generate_scheduling_problem(60, 8, 4)),
        ("MRPL Mega-Complex (5k)", generate_random_lp(5000, 2500, density=0.1)),
        ("National Grid (8k)", generate_random_lp(8000, 4000, density=0.05)),
    ]

    print(f"  {'Preset':<25} {'Vars':>6} {'Cons':>6} {'CPU(s)':>9} {'GPU(s)':>9} "
          f"{'SciPy(s)':>9} {'Speedup':>8}")
    print("  " + "-" * 80)

    for name, prob in presets:
        cpu = benchmark_solver(prob, use_gpu=False, tol=1e-4)
        try:
            gpu = benchmark_solver(prob, use_gpu=True, tol=1e-4)
        except Exception:
            gpu = {"time": float("inf"), "status": "N/A"}
        scipy = benchmark_scipy(prob)

        speedup = cpu["time"] / gpu["time"] if gpu["time"] > 0 and gpu["time"] != float("inf") else 0

        print(f"  {name:<25} {prob.n_vars:>6} {prob.n_constraints:>6} "
              f"{cpu['time']:>9.4f} {gpu['time']:>9.4f} {scipy['time']:>9.4f} "
              f"{speedup:>7.1f}×")


def main():
    parser = argparse.ArgumentParser(description="PDHG GPU LP Solver Benchmarks")
    parser.add_argument("--validate", action="store_true", help="Cross-validate against SciPy")
    parser.add_argument("--refinery", action="store_true", help="Benchmark refinery presets")
    parser.add_argument("--sizes", nargs="+", type=int, default=None,
                        help="Custom problem sizes (pairs of n_vars n_cons)")
    args = parser.parse_args()

    print_banner()

    if args.validate:
        validate_solver()
    elif args.refinery:
        benchmark_refinery()
    else:
        sizes = None
        if args.sizes and len(args.sizes) >= 2:
            sizes = [(args.sizes[i], args.sizes[i+1]) for i in range(0, len(args.sizes), 2)]
        results = run_scaling_benchmark(sizes=sizes)
        print("\n\n=== Summary ===")
        print(f"  {'Size':<20} {'CPU':>8} {'GPU':>8} {'SciPy':>8} {'Speedup':>8}")
        print("  " + "-" * 52)
        for r in results:
            print(f"  {r['n_vars']}×{r['n_constraints']:<13} "
                  f"{r['cpu_time']:>8.3f} {r['gpu_time']:>8.3f} {r['scipy_time']:>8.3f} "
                  f"{r['speedup_gpu_vs_cpu']:>7.1f}×")


if __name__ == "__main__":
    main()
