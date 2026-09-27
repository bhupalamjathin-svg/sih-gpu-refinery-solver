"""
PDHG-GPU: Indigenous GPU-Accelerated Optimization Solver
Supporting Linear Programming (LP), Quadratic Programming (QP), and Mixed-Integer LP (MILP).
"""

import os
import sys

# 1. Ensure Windows discovers CUDA runtime libraries (cublas, cusparse, etc.)
if sys.platform == "win32":
    try:
        import torch
        torch_lib = os.path.join(os.path.dirname(torch.__file__), "lib")
        if os.path.exists(torch_lib):
            os.add_dll_directory(torch_lib)
    except Exception:
        pass

# 2. Patch CuPy NVRTC compiler options to filter out incompatible system CUDA 13.x headers
# (e.g. cuda_fp8.hpp / cuda_fp6.hpp deprecation macro errors on Windows)
try:
    import cupy.cuda.compiler as _comp
    if not hasattr(_comp, "_cuda_sanitized"):
        _orig_compile = _comp._compile_using_nvrtc_no_warning

        def _sanitized_nvrtc_compile(source, options=(), *args, **kwargs):
            cleaned_opts = tuple(
                opt for opt in options
                if "CUDA\\v13" not in opt and "CUDA/v13" not in opt
            )
            return _orig_compile(source, cleaned_opts, *args, **kwargs)

        _comp._compile_using_nvrtc_no_warning = _sanitized_nvrtc_compile
        _comp._cuda_sanitized = True
except Exception:
    pass

from .problem import OptimizationProblem, LPProblem
from .pdhg import PDHGSolver
from .preprocess import ruiz_rescaling

__all__ = ["OptimizationProblem", "LPProblem", "PDHGSolver", "ruiz_rescaling"]
