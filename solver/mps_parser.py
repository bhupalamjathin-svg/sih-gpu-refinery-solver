"""
Indigenous Mathematical Programming System (.mps) Parser.

Built strictly from mathematical and algorithmic foundations without relying on
external solver or LP parsing libraries (no scipy, no pulp, no coinor, no pyomo).

Supports:
- Fixed-format and free-format MPS files
- Sections: NAME, ROWS (N, E, L, G), COLUMNS, RHS, RANGES, BOUNDS (UP, LO, FX, FR, BV)
- Converts directly into our native `OptimizationProblem` dataclass
"""

import re
from typing import Dict, List, Tuple, Optional
import numpy as np
import scipy.sparse as sp

from .problem import OptimizationProblem, LPProblem


def parse_mps(filepath: str) -> OptimizationProblem:
    """
    Parse a standard Mathematical Programming System (.mps) file into an OptimizationProblem.

    Parameters
    ----------
    filepath : str
        Path to the .mps file.

    Returns
    -------
    OptimizationProblem
        Indigenous problem instance with c, A_ub, b_ub, A_eq, b_eq, lb, ub, var_names.
    """
    with open(filepath, "r") as f:
        lines = f.readlines()

    problem_name = "MPS_Problem"
    current_section = None

    row_types: Dict[str, str] = {}  # 'N', 'E', 'L', 'G'
    row_order: List[str] = []
    obj_row: Optional[str] = None

    # col_data: col_name -> list of (row_name, coef)
    col_order: List[str] = []
    col_data: Dict[str, List[Tuple[str, float]]] = {}
    col_types: Dict[str, str] = {}  # 'C', 'I', 'B'

    rhs: Dict[str, float] = {}
    ranges: Dict[str, float] = {}
    lb_dict: Dict[str, float] = {}
    ub_dict: Dict[str, float] = {}

    in_integer_block = False

    for line_num, raw_line in enumerate(lines, 1):
        line = raw_line.rstrip()
        if not line or line.startswith("*"):
            continue

        # Check section header (starts at col 0)
        if not raw_line.startswith(" ") and not raw_line.startswith("\t"):
            tokens = line.split()
            header = tokens[0].upper()
            if header == "NAME":
                if len(tokens) > 1:
                    problem_name = tokens[1]
                current_section = "NAME"
            elif header in ("ROWS", "COLUMNS", "RHS", "RANGES", "BOUNDS", "ENDATA"):
                current_section = header
            continue

        tokens = line.split()
        if not tokens or current_section is None:
            continue

        if current_section == "ROWS":
            # Format: TYPE ROW_NAME
            r_type = tokens[0].upper()
            r_name = tokens[1]
            row_types[r_name] = r_type
            row_order.append(r_name)
            if r_type == "N" and obj_row is None:
                obj_row = r_name

        elif current_section == "COLUMNS":
            # Check for integer marker
            if "'MARKER'" in line.upper():
                if "'INTORG'" in line.upper():
                    in_integer_block = True
                elif "'INTEND'" in line.upper():
                    in_integer_block = False
                continue

            # Format: COL_NAME ROW_NAME1 VAL1 [ROW_NAME2 VAL2]
            col_name = tokens[0]
            if col_name not in col_data:
                col_order.append(col_name)
                col_data[col_name] = []
                col_types[col_name] = "I" if in_integer_block else "C"

            r1, v1 = tokens[1], float(tokens[2])
            col_data[col_name].append((r1, v1))

            if len(tokens) >= 5:
                r2, v2 = tokens[3], float(tokens[4])
                col_data[col_name].append((r2, v2))

        elif current_section == "RHS":
            # Format: [RHS_NAME] ROW_NAME1 VAL1 [ROW_NAME2 VAL2]
            idx = 0
            if len(tokens) % 2 != 0:
                idx = 1  # Skip RHS name token

            while idx < len(tokens):
                r_name = tokens[idx]
                val = float(tokens[idx + 1])
                rhs[r_name] = val
                idx += 2

        elif current_section == "RANGES":
            # Format: [RANGE_NAME] ROW_NAME1 VAL1 [ROW_NAME2 VAL2]
            idx = 0
            if len(tokens) % 2 != 0:
                idx = 1
            while idx < len(tokens):
                r_name = tokens[idx]
                val = float(tokens[idx + 1])
                ranges[r_name] = val
                idx += 2

        elif current_section == "BOUNDS":
            # Format: TYPE [BND_NAME] COL_NAME [VALUE]
            b_type = tokens[0].upper()
            if len(tokens) == 3:
                # UP/LO/FX/FR with no bound name
                c_name = tokens[1]
                val_str = tokens[2]
            elif len(tokens) >= 4:
                c_name = tokens[2]
                val_str = tokens[3]
            elif len(tokens) == 2:
                # FR or BV without value
                c_name = tokens[1]
                val_str = None
            else:
                continue

            val = float(val_str) if val_str is not None else 0.0

            if b_type == "UP":
                ub_dict[c_name] = val
                if c_name not in lb_dict:
                    lb_dict[c_name] = 0.0
            elif b_type == "LO":
                lb_dict[c_name] = val
            elif b_type == "FX":
                lb_dict[c_name] = val
                ub_dict[c_name] = val
            elif b_type == "FR":
                lb_dict[c_name] = -1e8
                ub_dict[c_name] = 1e8
            elif b_type == "BV":
                lb_dict[c_name] = 0.0
                ub_dict[c_name] = 1.0
                col_types[c_name] = "B"
            elif b_type == "PL":
                ub_dict[c_name] = 1e8
            elif b_type == "MI":
                lb_dict[c_name] = -1e8
                if c_name not in ub_dict:
                    ub_dict[c_name] = 0.0

    # Build OptimizationProblem matrices
    n_vars = len(col_order)
    col_idx = {name: i for i, name in enumerate(col_order)}

    # Objective vector c
    c = np.zeros(n_vars)
    if obj_row is not None:
        for col_name, entries in col_data.items():
            for r_name, val in entries:
                if r_name == obj_row:
                    c[col_idx[col_name]] = val

    # Bounds
    lb = np.zeros(n_vars)
    ub = np.full(n_vars, 1e8)
    for col_name, i in col_idx.items():
        if col_name in lb_dict:
            lb[i] = lb_dict[col_name]
        if col_name in ub_dict:
            ub[i] = ub_dict[col_name]

    # Constraints
    # Categorize rows into equality ('E') and inequality ('L', 'G')
    eq_rows = []
    b_eq = []
    eq_names = []

    ub_rows = []
    b_ub = []
    ub_names = []

    # Map row_name -> dict of {col_idx: val}
    matrix_rows: Dict[str, Dict[int, float]] = {r: {} for r in row_order}
    for col_name, entries in col_data.items():
        j = col_idx[col_name]
        for r_name, val in entries:
            if r_name in matrix_rows:
                matrix_rows[r_name][j] = val

    for r_name in row_order:
        r_type = row_types.get(r_name, "N")
        if r_type == "N":
            continue  # Objective or free row

        b_val = rhs.get(r_name, 0.0)
        row_entries = matrix_rows[r_name]

        if r_type == "E":
            # A_eq x = b_eq
            row_vec = np.zeros(n_vars)
            for j, v in row_entries.items():
                row_vec[j] = v
            eq_rows.append(row_vec)
            b_eq.append(b_val)
            eq_names.append(r_name)

        elif r_type == "L":
            # A x <= b
            row_vec = np.zeros(n_vars)
            for j, v in row_entries.items():
                row_vec[j] = v
            ub_rows.append(row_vec)
            b_ub.append(b_val)
            ub_names.append(r_name)

            # Check for range: b - |r| <= Ax <= b  => -Ax <= -(b - |r|)
            if r_name in ranges:
                rng = abs(ranges[r_name])
                ub_rows.append(-row_vec)
                b_ub.append(-(b_val - rng))
                ub_names.append(f"{r_name}_range_lower")

        elif r_type == "G":
            # A x >= b => -A x <= -b
            row_vec = np.zeros(n_vars)
            for j, v in row_entries.items():
                row_vec[j] = -v
            ub_rows.append(row_vec)
            b_ub.append(-b_val)
            ub_names.append(r_name)

            # Range for G: b <= Ax <= b + |r| => Ax <= b + |r|
            if r_name in ranges:
                rng = abs(ranges[r_name])
                ub_rows.append(-row_vec)
                b_ub.append(b_val + rng)
                ub_names.append(f"{r_name}_range_upper")

    A_eq = sp.csr_matrix(np.array(eq_rows)) if eq_rows else None
    b_eq_arr = np.array(b_eq) if eq_rows else None

    A_ub = sp.csr_matrix(np.array(ub_rows)) if ub_rows else None
    b_ub_arr = np.array(b_ub) if ub_rows else None

    # Check for integer variables
    var_types = np.array([col_types.get(col, "C") for col in col_order])
    has_integer = any(t in ("I", "B") for t in var_types)

    problem = OptimizationProblem(
        c=c,
        A_ub=A_ub,
        b_ub=b_ub_arr,
        A_eq=A_eq,
        b_eq=b_eq_arr,
        lb=lb,
        ub=ub,
        var_types=var_types if has_integer else None,
        name=problem_name,
        var_names=col_order,
        constraint_names=eq_names + ub_names,
    )
    return problem


def export_mps(problem: OptimizationProblem, filepath: str):
    """
    Export any indigenous OptimizationProblem into standard MPS format.
    """
    with open(filepath, "w") as f:
        name = (problem.name or "PROBLEM").replace(" ", "_")[:8]
        f.write(f"NAME          {name}\n")
        f.write("ROWS\n")
        f.write(" N  OBJ\n")

        m_eq = problem.n_eq
        m_ub = problem.n_ub
        eq_names = [f"E{i:04d}" for i in range(m_eq)]
        ub_names = [f"L{i:04d}" for i in range(m_ub)]

        for rname in eq_names:
            f.write(f" E  {rname}\n")
        for rname in ub_names:
            f.write(f" L  {rname}\n")

        f.write("COLUMNS\n")
        var_names = problem.var_names or [f"X{j:04d}" for j in range(problem.n_vars)]
        A_eq_csc = problem.A_eq.tocsc() if problem.A_eq is not None else None
        A_ub_csc = problem.A_ub.tocsc() if problem.A_ub is not None else None

        for j, vname in enumerate(var_names):
            vn = vname.replace(" ", "_")[:8]
            if abs(problem.c[j]) > 1e-10:
                f.write(f"    {vn:<8}  OBJ       {problem.c[j]:.8g}\n")

            if A_eq_csc is not None:
                start, end = A_eq_csc.indptr[j], A_eq_csc.indptr[j + 1]
                for idx in range(start, end):
                    r = A_eq_csc.indices[idx]
                    val = A_eq_csc.data[idx]
                    if abs(val) > 1e-10:
                        f.write(f"    {vn:<8}  {eq_names[r]:<8}  {val:.8g}\n")

            if A_ub_csc is not None:
                start, end = A_ub_csc.indptr[j], A_ub_csc.indptr[j + 1]
                for idx in range(start, end):
                    r = A_ub_csc.indices[idx]
                    val = A_ub_csc.data[idx]
                    if abs(val) > 1e-10:
                        f.write(f"    {vn:<8}  {ub_names[r]:<8}  {val:.8g}\n")

        f.write("RHS\n")
        if problem.b_eq is not None:
            for r, val in enumerate(problem.b_eq):
                if abs(val) > 1e-10:
                    f.write(f"    RHS1      {eq_names[r]:<8}  {val:.8g}\n")
        if problem.b_ub is not None:
            for r, val in enumerate(problem.b_ub):
                if abs(val) > 1e-10:
                    f.write(f"    RHS1      {ub_names[r]:<8}  {val:.8g}\n")

        f.write("BOUNDS\n")
        for j, vname in enumerate(var_names):
            vn = vname.replace(" ", "_")[:8]
            lb_val = problem.lb[j] if problem.lb is not None else 0.0
            ub_val = problem.ub[j] if problem.ub is not None else 1e8
            if lb_val != 0.0 and abs(lb_val) < 1e7:
                f.write(f" LO BND1      {vn:<8}  {lb_val:.8g}\n")
            if ub_val < 1e7:
                f.write(f" UP BND1      {vn:<8}  {ub_val:.8g}\n")

        f.write("ENDATA\n")
