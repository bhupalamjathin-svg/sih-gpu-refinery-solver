"""
LP Preprocessing and Preconditioning for PDHG.

Implements:
  1. Ruiz Equilibration (diagonal preconditioning)
     - Iteratively rescale rows and columns of K so norms are ~1
     - This is THE critical optimization for PDHG convergence
  2. Step size computation via power iteration for ||K||
  3. Backend detection (CuPy GPU vs NumPy CPU)
"""

import numpy as np
import scipy.sparse as sp


def get_backend(use_gpu: bool = True):
    """
    Return the array module (cupy or numpy) and sparse module.
    Falls back to numpy if cupy is unavailable.
    """
    if use_gpu:
        try:
            import cupy
            import cupyx.scipy.sparse as cusp
            return cupy, cusp, True
        except ImportError:
            pass
    return np, sp, False


def to_device(arr, xp, xsp, is_gpu: bool):
    """Transfer a numpy array or scipy sparse matrix to the target device."""
    if arr is None:
        return None
    if is_gpu:
        import cupy
        if sp.issparse(arr):
            return xsp.csr_matrix(arr)
        return cupy.asarray(arr)
    else:
        if sp.issparse(arr):
            return arr
        return np.asarray(arr)


def from_device(arr, is_gpu: bool):
    """Transfer an array back to numpy (CPU)."""
    if arr is None:
        return None
    if is_gpu:
        import cupy
        if hasattr(arr, 'get'):
            return arr.get()
        return np.asarray(arr)
    return np.asarray(arr)


def ruiz_rescaling(K, c, q, n_iterations: int = 10, xp=np, xsp=sp):
    """
    Ruiz equilibration for the constraint matrix K.

    Iteratively rescale rows and columns so that the infinity-norms
    of each row and column are approximately 1. This dramatically
    improves PDHG convergence.

    Parameters
    ----------
    K : sparse matrix (m, n) — constraint matrix
    c : array (n,) — objective
    q : array (m,) — RHS
    n_iterations : int — number of Ruiz iterations (10 is standard)
    xp : array module (numpy or cupy)
    xsp : sparse module

    Returns
    -------
    K_scaled, c_scaled, q_scaled, row_scale, col_scale
    """
    m, n = K.shape
    if m == 0:
        return K, c, q, xp.ones(0), xp.ones(n)

    row_scale = xp.ones(m)
    col_scale = xp.ones(n)

    K_work = K.copy()

    for _ in range(n_iterations):
        # Row norms (infinity norm)
        if xsp.issparse(K_work):
            abs_K = K_work.copy()
            abs_K.data = xp.abs(abs_K.data)
            row_norms = xp.array(abs_K.max(axis=1).toarray()).ravel()
            col_norms = xp.array(abs_K.max(axis=0).toarray()).ravel()
        else:
            row_norms = xp.max(xp.abs(K_work), axis=1)
            col_norms = xp.max(xp.abs(K_work), axis=0)

        # Avoid division by zero
        row_norms = xp.maximum(row_norms, 1e-12)
        col_norms = xp.maximum(col_norms, 1e-12)

        # Sqrt for symmetric treatment
        d_r = 1.0 / xp.sqrt(row_norms)
        d_c = 1.0 / xp.sqrt(col_norms)

        # Apply scaling: K = diag(d_r) @ K @ diag(d_c)
        if xsp.issparse(K_work):
            # Efficient sparse row/col scaling
            K_work = xsp.diags(d_r) @ K_work @ xsp.diags(d_c)
        else:
            K_work = d_r[:, None] * K_work * d_c[None, :]

        row_scale = row_scale * d_r
        col_scale = col_scale * d_c

    # Scale objective and RHS
    c_scaled = c * col_scale
    q_scaled = q * row_scale if len(q) > 0 else q

    return K_work, c_scaled, q_scaled, row_scale, col_scale


def estimate_operator_norm(K, n_iterations: int = 20, xp=np, xsp=sp):
    """
    Estimate ||K|| (largest singular value) via power iteration.
    Used to set PDHG step sizes: τ = σ = 1/||K||.

    Parameters
    ----------
    K : sparse matrix (m, n)
    n_iterations : number of power iterations

    Returns
    -------
    sigma_max : float — estimated operator norm
    """
    m, n = K.shape
    if m == 0 or n == 0:
        return 1.0

    # Random initial vector
    x = xp.random.randn(n).astype(xp.float64)
    x = x / xp.linalg.norm(x)

    K_T = K.T

    sigma = 1.0
    for _ in range(n_iterations):
        # y = K @ x
        y = K @ x
        # x = K^T @ y
        x = K_T @ y
        # Rayleigh quotient
        norm_x = xp.linalg.norm(x)
        if norm_x < 1e-15:
            break
        sigma = float(xp.sqrt(norm_x))
        x = x / norm_x

    return sigma


def compute_step_sizes(K, xp=np, xsp=sp):
    """
    Compute primal/dual step sizes for PDHG.

    Uses the Pock-Chambolle rule: τ * σ * ||K||^2 < 1
    We set τ = σ = 0.99 / ||K|| for safety margin.

    Returns
    -------
    tau, sigma : float — primal and dual step sizes
    """
    norm_K = estimate_operator_norm(K, xp=xp, xsp=xsp)
    norm_K = max(norm_K, 1e-10)

    # Safety factor 0.99 to ensure convergence
    step = 0.99 / norm_K
    return step, step
