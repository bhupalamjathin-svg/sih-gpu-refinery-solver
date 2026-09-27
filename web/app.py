"""
Flask Web Application for the GPU LP Solver.

REST API + Serve frontend.
"""

import sys
import os
import json
import traceback

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS

from solver.problem import OptimizationProblem, LPProblem
from solver.pdhg import PDHGSolver
from solver.milp import BranchAndBoundSolver
from solver.benchmarks import (
    generate_random_lp,
    benchmark_solver,
    benchmark_scipy,
    run_scaling_benchmark,
)
from refinery.blending import generate_blending_problem
from refinery.scheduling import generate_scheduling_problem
from refinery.resource_alloc import generate_resource_allocation_problem
from refinery.crude_risk_qp import generate_crude_risk_qp
from refinery.unit_commitment_milp import generate_unit_commitment_milp
from refinery.real_world_data import (
    generate_iocl_refinery_problem,
    generate_haverly_pooling_problem,
)
from solver.mps_parser import parse_mps, export_mps
from solver.memory_profiler import GPUMemoryProfiler


app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
CORS(app)


@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ---------- Pages ----------

@app.route("/")
def index():
    return render_template("index.html")


# ---------- API Endpoints ----------

@app.route("/api/presets", methods=["GET"])
def get_presets():
    """Return available preset refinery problems."""
    presets = [
        {
            "id": "iocl_bs6_refinery",
            "name": "IOCL Mathura 8-Crude Distillation & BS-VI Blending",
            "description": "Authentic Indian refinery: 8 crudes (Bombay High, Arab Light, etc.) with BS-VI specs (<10 ppm sulfur, 91 RON)",
            "type": "refinery_real",
            "params": {"n_crudes": 8, "n_units": 5, "cdu_cap": 150000},
        },
        {
            "id": "haverly_pooling",
            "name": "Haverly Petroleum Pooling Benchmark (1978)",
            "description": "The international petroleum pooling gold standard for tracking crude stream sulfur quality",
            "type": "refinery_real",
            "params": {"case": 1},
        },
        {
            "id": "netlib_afiro",
            "name": "Netlib AFIRO (Standard Real-World MPS Benchmark)",
            "description": "Canonical real-world industrial standard benchmark loaded from standard .mps file",
            "type": "standard_mps",
            "params": {"file": "afiro.mps"},
        },
        {
            "id": "blending_industrial",
            "name": "Crude & Stream Blending (Industrial)",
            "description": "50 component streams × 20 product blends (1,000 variables)",
            "type": "blending",
            "params": {"n_crudes": 50, "n_products": 20, "total_capacity": 50000},
        },
        {
            "id": "scheduling_multiunit",
            "name": "Multi-Unit Refinery Scheduling (60 Days)",
            "description": "60 days × 8 units × 4 products (2,160 variables)",
            "type": "scheduling",
            "params": {"n_periods": 60, "n_units": 8, "n_products": 4},
        },
        {
            "id": "mega_refinery_5k",
            "name": "MRPL Mega-Refinery Complex (Industrial Scale)",
            "description": "Full refinery complex flowsheet: 5,000 variables × 2,500 constraints",
            "type": "scheduling",
            "params": {"n_vars": 5000, "n_constraints": 2500},
        },
        {
            "id": "national_grid_8k",
            "name": "National Pipeline & Refinery Grid",
            "description": "Inter-refinery distribution network: 8,000 variables × 4,000 constraints",
            "type": "resource_allocation",
            "params": {"n_vars": 8000, "n_constraints": 4000},
        },
        {
            "id": "qp_crude_risk",
            "name": "Crude Procurement Risk (QP)",
            "description": "Markowitz portfolio risk: 8 crudes with quadratic covariance matrix Q",
            "type": "QP",
            "params": {"n_crudes": 8, "risk_aversion": 0.5},
        },
        {
            "id": "milp_unit_commitment",
            "name": "Unit Commitment & Schedule (MILP)",
            "description": "Discrete startup/shutdown optimization: 36 variables with binary states z ∈ {0,1}",
            "type": "MILP",
            "params": {"n_units": 4, "n_periods": 5},
        },
        {
            "id": "blending_pilot",
            "name": "Single Unit Blending (Pilot / Small)",
            "description": "4 crudes × 3 products (Reference 12-variable baseline)",
            "type": "blending",
            "params": {"n_crudes": 4, "n_products": 3, "total_capacity": 15000},
        },
    ]
    return jsonify(presets)


@app.route("/api/solve-preset", methods=["POST"])
def solve_preset():
    """Solve a preset refinery problem."""
    try:
        data = request.json
        preset_id = data.get("preset_id")
        use_gpu = data.get("use_gpu", True)
        tol = data.get("tolerance", 1e-4)
        max_iter = data.get("max_iterations", 10000)

        # Generate the problem
        presets = {
            "iocl_bs6_refinery": lambda: generate_iocl_refinery_problem(),
            "haverly_pooling": lambda: generate_haverly_pooling_problem(case=1),
            "netlib_afiro": lambda: parse_mps(os.path.join(os.path.dirname(os.path.dirname(__file__)), "benchmarks", "mps", "afiro.mps")),
            "blending_pilot": lambda: generate_blending_problem(4, 3, 15000),
            "blending_industrial": lambda: generate_blending_problem(50, 20, 50000),
            "scheduling_multiunit": lambda: generate_scheduling_problem(60, 8, 4),
            "mega_refinery_5k": lambda: generate_random_lp(5000, 2500, density=0.1),
            "national_grid_8k": lambda: generate_random_lp(8000, 4000, density=0.05),
            "qp_crude_risk": lambda: generate_crude_risk_qp(8, 30000.0, 0.5),
            "milp_unit_commitment": lambda: generate_unit_commitment_milp(4, 5),
        }

        if preset_id not in presets:
            return jsonify({"error": f"Unknown preset: {preset_id}"}), 400

        problem = presets[preset_id]()

        # Solve according to problem class
        if problem.is_milp:
            solver = BranchAndBoundSolver(
                max_nodes=150,
                time_limit=30.0,
                use_gpu=use_gpu,
                node_lp_max_iter=min(max_iter, 2500),
                verbose=False,
            )
            result = solver.solve(problem)
            sol_dict = {
                "status": result.status,
                "obj_val": result.obj_val,
                "x": result.x.tolist(),
                "solve_time": result.solve_time,
                "n_iterations": result.nodes_explored,
                "primal_residual": 0.0,
                "duality_gap": result.mip_gap,
                "device": result.device,
                "nodes_explored": result.nodes_explored,
                "mip_gap": result.mip_gap,
                "convergence_log": [
                    {"iteration": h["node"], "primal_res": 0.0, "dual_res": 0.0, "gap": result.mip_gap, "primal_obj": h["obj"], "dual_obj": h["obj"]}
                    for h in result.incumbent_history
                ],
            }
        else:
            solver = PDHGSolver(
                max_iterations=max_iter,
                tol=tol,
                use_gpu=use_gpu,
                verbose=False,
            )
            result = solver.solve(problem)
            sol_dict = result.to_dict()

        return jsonify({
            "problem": problem.to_dict(),
            "solution": sol_dict,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/solve", methods=["POST"])
def solve_custom():
    """Solve a custom optimization problem (LP, QP, or MILP) from user input."""
    try:
        data = request.json
        problem = OptimizationProblem.from_dict(data["problem"])
        use_gpu = data.get("use_gpu", True)
        tol = data.get("tolerance", 1e-4)
        max_iter = data.get("max_iterations", 10000)

        if problem.is_milp:
            solver = BranchAndBoundSolver(
                max_nodes=150,
                time_limit=30.0,
                use_gpu=use_gpu,
                node_lp_max_iter=min(max_iter, 2500),
                verbose=False,
            )
            result = solver.solve(problem)
            sol_dict = {
                "status": result.status,
                "obj_val": result.obj_val,
                "x": result.x.tolist(),
                "solve_time": result.solve_time,
                "n_iterations": result.nodes_explored,
                "primal_residual": 0.0,
                "duality_gap": result.mip_gap,
                "device": result.device,
                "nodes_explored": result.nodes_explored,
                "mip_gap": result.mip_gap,
                "convergence_log": [
                    {"iteration": h["node"], "primal_res": 0.0, "dual_res": 0.0, "gap": result.mip_gap, "primal_obj": h["obj"], "dual_obj": h["obj"]}
                    for h in result.incumbent_history
                ],
            }
        else:
            solver = PDHGSolver(
                max_iterations=max_iter,
                tol=tol,
                use_gpu=use_gpu,
                verbose=False,
            )
            result = solver.solve(problem)
            sol_dict = result.to_dict()

        return jsonify({
            "problem": problem.to_dict(),
            "solution": sol_dict,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/benchmark", methods=["POST"])
def run_benchmark():
    """Run GPU vs CPU vs SciPy benchmarks."""
    try:
        data = request.json or {}
        # Use smaller sizes for quick web demo
        sizes = data.get("sizes", [
            [50, 30], [100, 60], [200, 120], [500, 300],
            [1000, 600], [2000, 1200],
        ])
        tol = data.get("tolerance", 1e-4)
        max_iter = data.get("max_iterations", 5000)

        sizes = [tuple(s) for s in sizes]
        results = run_scaling_benchmark(sizes=sizes, tol=tol, max_iter=max_iter)

        return jsonify({"benchmark_results": results})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/benchmark-preset", methods=["POST"])
def benchmark_preset():
    """Benchmark a specific preset on CPU, GPU, and SciPy."""
    try:
        data = request.json
        preset_id = data.get("preset_id")
        tol = data.get("tolerance", 1e-4)
        max_iter = data.get("max_iterations", 10000)

        presets = {
            "iocl_bs6_refinery": lambda: generate_iocl_refinery_problem(),
            "haverly_pooling": lambda: generate_haverly_pooling_problem(case=1),
            "netlib_afiro": lambda: parse_mps(os.path.join(os.path.dirname(os.path.dirname(__file__)), "benchmarks", "mps", "afiro.mps")),
            "blending_pilot": lambda: generate_blending_problem(4, 3, 15000),
            "blending_industrial": lambda: generate_blending_problem(50, 20, 50000),
            "scheduling_multiunit": lambda: generate_scheduling_problem(60, 8, 4),
            "mega_refinery_5k": lambda: generate_random_lp(5000, 2500, density=0.1),
            "national_grid_8k": lambda: generate_random_lp(8000, 4000, density=0.05),
            "qp_crude_risk": lambda: generate_crude_risk_qp(8, 30000.0, 0.5),
            "milp_unit_commitment": lambda: generate_unit_commitment_milp(4, 5),
        }

        if preset_id not in presets:
            return jsonify({"error": f"Unknown preset: {preset_id}"}), 400

        problem = presets[preset_id]()

        cpu_res = benchmark_solver(problem, use_gpu=False, tol=tol, max_iter=max_iter)
        try:
            gpu_res = benchmark_solver(problem, use_gpu=True, tol=tol, max_iter=max_iter)
        except Exception:
            gpu_res = {"device": "GPU", "time": 0, "status": "unavailable",
                       "obj_val": 0}
        scipy_res = benchmark_scipy(problem)

        speedup = cpu_res["time"] / gpu_res["time"] if gpu_res["time"] > 0 else 0

        return jsonify({
            "problem_name": problem.name,
            "n_vars": problem.n_vars,
            "n_constraints": problem.n_constraints,
            "cpu": cpu_res,
            "gpu": gpu_res,
            "scipy": scipy_res,
            "speedup": round(speedup, 2),
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/gpu-telemetry", methods=["GET"])
def get_gpu_telemetry():
    """Return live NVIDIA RTX GPU telemetry (VRAM, SMs, Cores, Temp, Power, Util)."""
    import subprocess
    try:
        import cupy as cp
        props = cp.cuda.runtime.getDeviceProperties(0)
        free_mem, total_mem = cp.cuda.runtime.memGetInfo()
        used_mem = total_mem - free_mem
        name = props["name"].decode() if isinstance(props["name"], bytes) else props["name"]
        major, minor = props["major"], props["minor"]
        sm_count = props["multiProcessorCount"]
        cuda_cores = sm_count * 128  # Ada Lovelace architecture (sm_89)

        temp, util, power = None, None, None
        try:
            cmd = ["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu,power.draw", "--format=csv,noheader,nounits"]
            out = subprocess.check_output(cmd, text=True, timeout=1).strip().split(",")
            if len(out) >= 3:
                temp = float(out[0].strip())
                util = float(out[1].strip())
                power = float(out[2].strip())
        except Exception:
            pass

        return jsonify({
            "available": True,
            "device_name": name,
            "arch": f"sm_{major}{minor} (Ada Lovelace)",
            "sm_count": sm_count,
            "cuda_cores": cuda_cores,
            "vram_used_gb": round(used_mem / (1024**3), 2),
            "vram_total_gb": round(total_mem / (1024**3), 2),
            "vram_pct": round((used_mem / total_mem) * 100, 1),
            "temperature_c": temp,
            "gpu_util_pct": util,
            "power_w": power,
        })
    except Exception as e:
        return jsonify({
            "available": False,
            "error": str(e),
        })


@app.route("/api/gpu-memory-limits", methods=["GET"])
def get_gpu_memory_limits():
    """Return theoretical and hardware memory limits for RTX 4070."""
    try:
        profiler = GPUMemoryProfiler()
        hw = profiler.get_hardware_info()
        cap = profiler.estimate_max_capacity()
        return jsonify({
            "hardware": hw,
            "capacity": cap,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/memory-stress-test", methods=["POST"])
def run_memory_stress():
    """Run empirical GPU memory stress test."""
    try:
        data = request.json or {}
        max_scale = data.get("max_scale", 10000)
        profiler = GPUMemoryProfiler()
        results = profiler.run_stress_test(max_scale=max_scale)
        return jsonify({
            "stress_results": results,
            "capacity": profiler.estimate_max_capacity(),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/upload-mps", methods=["POST"])
def upload_mps():
    """Parse an uploaded .mps file or load a bundled benchmark file."""
    try:
        if "file" in request.files:
            file = request.files["file"]
            temp_dir = os.path.join(os.path.dirname(__file__), "temp_uploads")
            os.makedirs(temp_dir, exist_ok=True)
            filepath = os.path.join(temp_dir, file.filename)
            file.save(filepath)
            problem = parse_mps(filepath)
        elif request.json and "preset_file" in request.json:
            fname = request.json["preset_file"]
            filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "benchmarks", "mps", fname)
            problem = parse_mps(filepath)
        else:
            return jsonify({"error": "No file or preset provided"}), 400

        return jsonify({
            "name": problem.name,
            "n_vars": problem.n_vars,
            "n_constraints": problem.n_constraints,
            "n_eq": problem.n_eq,
            "n_ub": problem.n_ub,
            "problem_class": problem.problem_class,
            "var_names": problem.var_names[:50],
            "constraint_names": problem.constraint_names[:50],
            "filepath": filepath,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/solve-mps", methods=["POST"])
def solve_mps():
    """Solve an MPS problem by path or bundled name."""
    try:
        data = request.json or {}
        filepath = data.get("filepath")
        if not filepath or not os.path.exists(filepath):
            fname = data.get("preset_file", "afiro.mps")
            filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "benchmarks", "mps", fname)

        problem = parse_mps(filepath)
        use_gpu = data.get("use_gpu", True)
        tol = data.get("tolerance", 1e-4)
        max_iter = data.get("max_iterations", 10000)

        if problem.is_milp:
            solver = BranchAndBoundSolver(
                max_nodes=150,
                time_limit=30.0,
                use_gpu=use_gpu,
                verbose=False,
            )
            res = solver.solve(problem)
            sol_dict = {
                "status": res.status,
                "obj_val": res.obj_val,
                "x": res.x.tolist() if res.x is not None else None,
                "solve_time": res.solve_time,
                "n_iterations": res.nodes_explored,
                "primal_residual": 0.0,
                "duality_gap": res.mip_gap,
                "device": res.device,
                "nodes_explored": res.nodes_explored,
                "mip_gap": res.mip_gap,
                "convergence_log": [
                    {"iteration": h["node"], "primal_res": 0.0, "dual_res": 0.0, "gap": res.mip_gap, "primal_obj": h["obj"], "dual_obj": h["obj"]}
                    for h in res.incumbent_history
                ],
                "shadow_prices": [],
                "binding_constraints": [],
            }
        else:
            solver = PDHGSolver(
                max_iterations=max_iter,
                tol=tol,
                use_gpu=use_gpu,
                verbose=False,
            )
            res = solver.solve(problem)
            sol_dict = res.to_dict()

        return jsonify({
            "problem": problem.to_dict(),
            "solution": sol_dict,
        })
    except Exception as e:
        traceback.print_exc()
@app.route("/download/presentation-pptx")
def download_pptx():
    """Download the presentation deck (.pptx)."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SIH26119_PDHG_GPU_Solver_Presentation.pptx")
    if os.path.exists(path):
        return send_file(path, as_attachment=True, download_name="SIH26119_PDHG_GPU_Solver_Presentation.pptx")
    return jsonify({"error": "Presentation file not found"}), 404


@app.route("/download/presentation-pdf")
def download_pdf():
    """Download the presentation deck (.pdf)."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "slides_export", "SIH26119_PDHG_GPU_Solver_Presentation.pdf")
    if os.path.exists(path):
        return send_file(path, as_attachment=True, download_name="SIH26119_PDHG_GPU_Solver_Presentation.pdf")
    return jsonify({"error": "PDF presentation file not found"}), 404


@app.route("/download/sample-afiro-mps")
def download_sample_afiro():
    """Download Netlib AFIRO sample MPS file."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_afiro.mps")
    if os.path.exists(path):
        return send_file(path, as_attachment=True, download_name="sample_afiro.mps")
    return jsonify({"error": "sample_afiro.mps not found"}), 404


@app.route("/download/sample-iocl-mps")
def download_sample_iocl():
    """Download IOCL Mathura sample MPS file."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "benchmarks", "mps", "iocl_refinery.mps")
    if os.path.exists(path):
        return send_file(path, as_attachment=True, download_name="iocl_refinery.mps")
    return jsonify({"error": "iocl_refinery.mps not found"}), 404


if __name__ == "__main__":
    print("=" * 60)
    print("  PDHG-GPU: Indigenous LP Solver for Refinery Optimization")
    print("  SIH Problem Statement: SIH26119")
    print("=" * 60)
    print("\n  Open http://localhost:5000 in your browser\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
