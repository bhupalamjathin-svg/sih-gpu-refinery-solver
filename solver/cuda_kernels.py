"""
Custom CUDA C++ Kernels for PDHG Linear Programming Solver.

Implements fused GPU kernels via CuPy RawKernel to execute
the core iterative optimization math directly on NVIDIA GPU Streaming Multiprocessors (SMs).

Fusing operations reduces global memory round-trips and maximizes memory bandwidth
on architectures like NVIDIA Ada Lovelace (RTX 4070).
"""

import cupy as cp

# -------------------------------------------------------------------------
# CUDA C++ Kernel 1: Fused Dual Step + Inequality Projection
# Computes:
#   y[i] = y[i] + sigma * (Kx_bar[i] - q[i])
#   if i >= n_eq: y[i] = max(y[i], 0.0)  [Projection for inequality constraints]
# -------------------------------------------------------------------------
DUAL_UPDATE_CLAMP_CUDA_CODE = r'''
extern "C" __global__
void dual_update_clamp_kernel(
    const double* __restrict__ Kx_bar,
    const double* __restrict__ q,
    double* __restrict__ y,
    const double sigma,
    const int n_eq,
    const int m
) {
    int idx = blockDim.x * blockIdx.x + threadIdx.x;
    if (idx < m) {
        double val = y[idx] + sigma * (Kx_bar[idx] - q[idx]);
        if (idx >= n_eq && val < 0.0) {
            val = 0.0;
        }
        y[idx] = val;
    }
}
'''

# -------------------------------------------------------------------------
# CUDA C++ Kernel 2: Fused Primal Step + Bound Projection + Over-relaxation
# Computes:
#   x_old = x[j]
#   x_new = x_old - tau * (c[j] + KTy[j])
#   x_new = clamp(x_new, lb[j], ub[j])
#   x[j] = x_new
#   x_bar[j] = x_new + theta * (x_new - x_old)
# -------------------------------------------------------------------------
PRIMAL_UPDATE_PROJECT_OVERRELAX_CUDA_CODE = r'''
extern "C" __global__
void primal_step_project_overrelax_kernel(
    const double* __restrict__ c,
    const double* __restrict__ KTy,
    const double* __restrict__ Qx,
    const double* __restrict__ lb,
    const double* __restrict__ ub,
    double* __restrict__ x,
    double* __restrict__ x_bar,
    const double tau,
    const double theta,
    const int n
) {
    int idx = blockDim.x * blockIdx.x + threadIdx.x;
    if (idx < n) {
        double x_old = x[idx];
        double grad = c[idx];
        if (Qx != nullptr) grad += Qx[idx];
        if (KTy != nullptr) grad += KTy[idx];
        double new_x = x_old - tau * grad;
        
        // Clamp to variable bounds [lb, ub]
        double l = lb[idx];
        double u = ub[idx];
        if (new_x < l) new_x = l;
        if (new_x > u) new_x = u;
        
        x[idx] = new_x;
        // Over-relaxation extrapolation for Chambolle-Pock acceleration
        x_bar[idx] = new_x + theta * (new_x - x_old);
    }
}
'''

# -------------------------------------------------------------------------
# CUDA C++ Kernel 3: Fused KKT Residual & Stationarity Violation Checker
# Computes dual gradient violations and primal violations in parallel
# -------------------------------------------------------------------------
KKT_VIOLATION_CUDA_CODE = r'''
extern "C" __global__
void kkt_violation_kernel(
    const double* __restrict__ grad,
    const double* __restrict__ x,
    const double* __restrict__ lb,
    const double* __restrict__ ub,
    double* __restrict__ dual_viol,
    const int n
) {
    int idx = blockDim.x * blockIdx.x + threadIdx.x;
    if (idx < n) {
        double g = grad[idx];
        double xi = x[idx];
        double li = lb[idx];
        double ui = ub[idx];
        
        double tol = 1e-8 * (1.0 + fabs(li));
        bool at_lb = fabs(xi - li) <= tol;
        bool at_ub = fabs(xi - ui) <= tol;
        
        double v = 0.0;
        if (at_lb) {
            if (g < 0.0) v = g; // violation: reduced cost should be >= 0
        } else if (at_ub) {
            if (g > 0.0) v = g; // violation: reduced cost should be <= 0
        } else {
            v = g; // interior: reduced cost must be 0
        }
        dual_viol[idx] = v;
    }
}
'''

class CUDASolverKernels:
    """Compiled CUDA C++ kernels via CuPy NVRTC for RTX 4070 execution."""
    
    def __init__(self):
        self.dual_kernel = cp.RawKernel(DUAL_UPDATE_CLAMP_CUDA_CODE, 'dual_update_clamp_kernel')
        self.primal_kernel = cp.RawKernel(PRIMAL_UPDATE_PROJECT_OVERRELAX_CUDA_CODE, 'primal_step_project_overrelax_kernel')
        self.kkt_kernel = cp.RawKernel(KKT_VIOLATION_CUDA_CODE, 'kkt_violation_kernel')
        
    def launch_dual_update(self, Kx_bar, q, y, sigma: float, n_eq: int, m: int):
        threads_per_block = 256
        blocks = (m + threads_per_block - 1) // threads_per_block
        self.dual_kernel((blocks,), (threads_per_block,), (Kx_bar, q, y, cp.float64(sigma), cp.int32(n_eq), cp.int32(m)))
        
    def launch_primal_update(self, c, KTy, Qx, lb, ub, x, x_bar, tau: float, theta: float, n: int):
        threads_per_block = 256
        blocks = (n + threads_per_block - 1) // threads_per_block
        self.primal_kernel((blocks,), (threads_per_block,), (c, KTy, Qx, lb, ub, x, x_bar, cp.float64(tau), cp.float64(theta), cp.int32(n)))

    def launch_kkt_violation(self, grad, x, lb, ub, dual_viol, n: int):
        threads_per_block = 256
        blocks = (n + threads_per_block - 1) // threads_per_block
        self.kkt_kernel((blocks,), (threads_per_block,), (grad, x, lb, ub, dual_viol, cp.int32(n)))
