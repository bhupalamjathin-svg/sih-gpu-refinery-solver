"""
Optimization Problem Data Structure.

Unified representation for:
  1. Linear Programming (LP):
         minimize    c^T x
         subject to  A_ub x <= b_ub,  A_eq x = b_eq,  lb <= x <= ub

  2. Quadratic Programming (QP):
         minimize    1/2 x^T Q x + c^T x
         subject to  A_ub x <= b_ub,  A_eq x = b_eq,  lb <= x <= ub
         where Q >= 0 (positive semi-definite)

  3. Mixed-Integer Linear Programming (MILP):
         minimize    c^T x
         subject to  A_ub x <= b_ub,  A_eq x = b_eq,  lb <= x <= ub
                     x_j in Z for j in IntegralitySet
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import numpy as np
import scipy.sparse as sp


@dataclass
class OptimizationProblem:
    """
    Unified Optimization Problem supporting LP, QP, and MILP.

    Parameters
    ----------
    c : array (n,)
        Linear objective coefficients.
    Q : array (n, n), optional
        Quadratic objective matrix (symmetric positive semi-definite).
        If provided and non-zero, classifies problem as QP.
    A_ub : array (m1, n), optional
        Inequality constraint matrix (A_ub x <= b_ub).
    b_ub : array (m1,), optional
        Inequality right-hand side.
    A_eq : array (m2, n), optional
        Equality constraint matrix (A_eq x = b_eq).
    b_eq : array (m2,), optional
        Equality right-hand side.
    lb : array (n,), optional
        Lower bounds on variables (default: 0).
    ub : array (n,), optional
        Upper bounds on variables (default: +inf).
    var_types : list[str], optional
        Variable types: 'C' (Continuous), 'I' (Integer), 'B' (Binary).
        If any 'I' or 'B' are present, classifies problem as MILP.
    var_names : list[str], optional
        Display names for decision variables.
    constraint_names : list[str], optional
        Display names for constraints.
    name : str
        Human-readable problem name.
    metadata : dict
        Additional user-specified attributes.
    """

    c: np.ndarray
    Q: Optional[np.ndarray] = None
    A_ub: Optional[np.ndarray] = None
    b_ub: Optional[np.ndarray] = None
    A_eq: Optional[np.ndarray] = None
    b_eq: Optional[np.ndarray] = None
    lb: Optional[np.ndarray] = None
    ub: Optional[np.ndarray] = None
    var_types: Optional[List[str]] = None
    var_names: Optional[list] = None
    constraint_names: Optional[list] = None
    name: str = "Optimization Problem"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        n = len(self.c)
        if self.lb is None:
            self.lb = np.zeros(n)
        if self.ub is None:
            self.ub = np.full(n, np.inf)
        if self.var_names is None:
            self.var_names = [f"x{i}" for i in range(n)]
        if self.var_types is None:
            self.var_types = ["C"] * n
        else:
            # Enforce binary bounds
            for i, vt in enumerate(self.var_types):
                if vt == "B":
                    self.lb[i] = max(self.lb[i], 0.0)
                    self.ub[i] = min(self.ub[i], 1.0)

    @property
    def n_vars(self) -> int:
        return len(self.c)

    @property
    def n_eq(self) -> int:
        return self.A_eq.shape[0] if self.A_eq is not None else 0

    @property
    def n_ub(self) -> int:
        return self.A_ub.shape[0] if self.A_ub is not None else 0

    @property
    def n_constraints(self) -> int:
        return self.n_eq + self.n_ub

    @property
    def is_qp(self) -> bool:
        """Returns True if objective contains non-zero quadratic term."""
        if self.Q is None:
            return False
        if sp.issparse(self.Q):
            return self.Q.nnz > 0
        return bool(np.any(self.Q != 0))

    @property
    def is_milp(self) -> bool:
        """Returns True if any variable is restricted to Integer or Binary."""
        if self.var_types is None:
            return False
        return any(vt in ("I", "B") for vt in self.var_types)

    @property
    def is_lp(self) -> bool:
        """Returns True if strictly a Linear Program (no Q, all continuous)."""
        return not self.is_qp and not self.is_milp

    @property
    def problem_class(self) -> str:
        """Categorize into LP, QP, or MILP."""
        if self.is_milp and self.is_qp:
            return "MIQP"
        if self.is_milp:
            return "MILP"
        if self.is_qp:
            return "QP"
        return "LP"

    @property
    def integer_indices(self) -> List[int]:
        """Indices of integer or binary variables."""
        if self.var_types is None:
            return []
        return [i for i, vt in enumerate(self.var_types) if vt in ("I", "B")]

    def to_saddle_point(self):
        """
        Convert to unified constraint matrix form for PDHG:
            K = [A_eq; A_ub]   (vertically stacked CSR matrix)
            q = [b_eq; b_ub]
            constraint_types = ['eq'] * m_eq + ['ub'] * m_ub

        Returns: K (sparse CSR), q (dense 1D array), constraint_types list
        """
        blocks = []
        q_parts = []
        types = []

        if self.A_eq is not None and self.A_eq.shape[0] > 0:
            A_eq_sp = sp.csr_matrix(self.A_eq) if not sp.issparse(self.A_eq) else self.A_eq
            blocks.append(A_eq_sp)
            q_parts.append(np.asarray(self.b_eq).ravel())
            types.extend(["eq"] * self.n_eq)

        if self.A_ub is not None and self.A_ub.shape[0] > 0:
            A_ub_sp = sp.csr_matrix(self.A_ub) if not sp.issparse(self.A_ub) else self.A_ub
            blocks.append(A_ub_sp)
            q_parts.append(np.asarray(self.b_ub).ravel())
            types.extend(["ub"] * self.n_ub)

        if len(blocks) == 0:
            K = sp.csr_matrix((0, self.n_vars))
            q = np.array([])
        elif len(blocks) == 1:
            K = blocks[0]
            q = q_parts[0]
        else:
            K = sp.vstack(blocks, format="csr")
            q = np.concatenate(q_parts)

        return K, q, types

    def summary(self) -> str:
        """Human-readable problem summary."""
        n_int = len(self.integer_indices)
        lines = [
            f"=== {self.name} [{self.problem_class}] ===",
            f"  Variables:              {self.n_vars} (Continuous: {self.n_vars - n_int}, Discrete: {n_int})",
            f"  Equality constraints:   {self.n_eq}",
            f"  Inequality constraints: {self.n_ub}",
            f"  Total constraints:      {self.n_constraints}",
            f"  Quadratic Term (Q):     {'Yes' if self.is_qp else 'None'}",
        ]
        bounded = np.sum(np.isfinite(self.ub))
        lines.append(f"  Bounded variables:      {bounded}/{self.n_vars}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize for JSON transport across web API."""
        def arr_to_list(a):
            if a is None:
                return None
            if sp.issparse(a):
                return a.toarray().tolist()
            return np.asarray(a).tolist()

        return {
            "name": self.name,
            "problem_class": self.problem_class,
            "c": arr_to_list(self.c),
            "Q": arr_to_list(self.Q),
            "A_ub": arr_to_list(self.A_ub),
            "b_ub": arr_to_list(self.b_ub),
            "A_eq": arr_to_list(self.A_eq),
            "b_eq": arr_to_list(self.b_eq),
            "lb": arr_to_list(self.lb),
            "ub": arr_to_list(self.ub),
            "var_types": self.var_types,
            "var_names": self.var_names,
            "n_vars": self.n_vars,
            "n_constraints": self.n_constraints,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "OptimizationProblem":
        """Deserialize from JSON dict."""
        def to_arr(v):
            if v is None:
                return None
            return np.array(v, dtype=np.float64)

        return cls(
            c=to_arr(d["c"]),
            Q=to_arr(d.get("Q")),
            A_ub=to_arr(d.get("A_ub")),
            b_ub=to_arr(d.get("b_ub")),
            A_eq=to_arr(d.get("A_eq")),
            b_eq=to_arr(d.get("b_eq")),
            lb=to_arr(d.get("lb")),
            ub=to_arr(d.get("ub")),
            var_types=d.get("var_types"),
            var_names=d.get("var_names"),
            name=d.get("name", "Optimization Problem"),
        )


# Backward compatibility alias
LPProblem = OptimizationProblem
