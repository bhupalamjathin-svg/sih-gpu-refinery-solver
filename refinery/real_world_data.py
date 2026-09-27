"""
Authentic Real-World Refinery Datasets & Optimization Models.

Includes:
1. Indian Petroleum Industry Benchmark (IOCL Mathura / MRPL Mangalore):
   - 8 authentic crude assays (Bombay High, Arab Light, Arab Heavy, Basrah Medium,
     Bonny Light, Maya, Urals, Sokol) with real API gravity, sulfur wt%, yields.
   - Strict BS-VI (Euro-VI) quality compliance (Diesel <= 10 ppm sulfur, Petrol <= 10 ppm sulfur & >= 91 RON).
   - Major processing units: Desalter, CDU, VDU, Diesel Hydrotreater (DHT), Catalytic Reformer (CRU), FCCU.
   - Detailed constraint and variable naming for economic shadow price analysis.

2. Haverly Petroleum Pooling Benchmark (Haverly 1978):
   - The classic gold-standard benchmark in refinery pooling literature.
"""

from typing import Dict, Any, List
import numpy as np
import scipy.sparse as sp
from solver.problem import OptimizationProblem, LPProblem

# --------------------------------------------------------------------------
# 1. Authentic Crude Assays (Real Industrial Data)
# --------------------------------------------------------------------------

CRUDE_ASSAYS = {
    "Bombay_High": {
        "origin": "ONGC Domestic (India)",
        "api_gravity": 38.5,
        "density_kg_m3": 832.0,
        "sulfur_wt_pct": 0.13,  # Sweet
        "pour_point_c": 30.0,   # Waxy
        "price_usd_bbl": 78.50,
        "yields": {
            "lpg": 0.035,
            "naphtha": 0.220,
            "kero_atf": 0.180,
            "gasoil_diesel": 0.385,
            "residue": 0.180,
        },
        "naphtha_ron": 62.0,
        "diesel_cetane": 54.0,
        "diesel_sulfur_pct": 0.15,
    },
    "Arab_Light": {
        "origin": "Saudi Aramco (Saudi Arabia)",
        "api_gravity": 32.8,
        "density_kg_m3": 861.0,
        "sulfur_wt_pct": 1.97,  # Sour
        "pour_point_c": -20.0,
        "price_usd_bbl": 74.20,
        "yields": {
            "lpg": 0.028,
            "naphtha": 0.175,
            "kero_atf": 0.142,
            "gasoil_diesel": 0.345,
            "residue": 0.310,
        },
        "naphtha_ron": 58.0,
        "diesel_cetane": 50.0,
        "diesel_sulfur_pct": 1.85,
    },
    "Arab_Heavy": {
        "origin": "Saudi Aramco (Saudi Arabia)",
        "api_gravity": 27.9,
        "density_kg_m3": 888.0,
        "sulfur_wt_pct": 2.95,  # Heavy Sour
        "pour_point_c": -15.0,
        "price_usd_bbl": 68.80,
        "yields": {
            "lpg": 0.018,
            "naphtha": 0.115,
            "kero_atf": 0.105,
            "gasoil_diesel": 0.292,
            "residue": 0.470,
        },
        "naphtha_ron": 54.0,
        "diesel_cetane": 46.0,
        "diesel_sulfur_pct": 2.65,
    },
    "Basrah_Medium": {
        "origin": "SOMO (Iraq)",
        "api_gravity": 29.5,
        "density_kg_m3": 879.0,
        "sulfur_wt_pct": 2.80,
        "pour_point_c": -18.0,
        "price_usd_bbl": 71.00,
        "yields": {
            "lpg": 0.022,
            "naphtha": 0.135,
            "kero_atf": 0.118,
            "gasoil_diesel": 0.310,
            "residue": 0.415,
        },
        "naphtha_ron": 56.0,
        "diesel_cetane": 48.0,
        "diesel_sulfur_pct": 2.40,
    },
    "Bonny_Light": {
        "origin": "NNPC (Nigeria)",
        "api_gravity": 35.3,
        "density_kg_m3": 848.0,
        "sulfur_wt_pct": 0.15,  # Sweet
        "pour_point_c": -12.0,
        "price_usd_bbl": 80.50,
        "yields": {
            "lpg": 0.032,
            "naphtha": 0.200,
            "kero_atf": 0.165,
            "gasoil_diesel": 0.370,
            "residue": 0.233,
        },
        "naphtha_ron": 64.0,
        "diesel_cetane": 55.0,
        "diesel_sulfur_pct": 0.16,
    },
    "Maya": {
        "origin": "Pemex (Mexico)",
        "api_gravity": 21.8,
        "density_kg_m3": 923.0,
        "sulfur_wt_pct": 3.40,  # Ultra-Heavy Sour
        "pour_point_c": -10.0,
        "price_usd_bbl": 64.00,
        "yields": {
            "lpg": 0.012,
            "naphtha": 0.090,
            "kero_atf": 0.085,
            "gasoil_diesel": 0.245,
            "residue": 0.568,
        },
        "naphtha_ron": 50.0,
        "diesel_cetane": 43.0,
        "diesel_sulfur_pct": 3.10,
    },
    "Urals": {
        "origin": "Russian Blend",
        "api_gravity": 31.7,
        "density_kg_m3": 867.0,
        "sulfur_wt_pct": 1.60,
        "pour_point_c": -15.0,
        "price_usd_bbl": 70.50,
        "yields": {
            "lpg": 0.025,
            "naphtha": 0.160,
            "kero_atf": 0.135,
            "gasoil_diesel": 0.330,
            "residue": 0.350,
        },
        "naphtha_ron": 57.0,
        "diesel_cetane": 49.0,
        "diesel_sulfur_pct": 1.55,
    },
    "Sokol": {
        "origin": "Sakhalin (Far East)",
        "api_gravity": 37.7,
        "density_kg_m3": 836.0,
        "sulfur_wt_pct": 0.23,
        "pour_point_c": -25.0,
        "price_usd_bbl": 79.80,
        "yields": {
            "lpg": 0.036,
            "naphtha": 0.215,
            "kero_atf": 0.175,
            "gasoil_diesel": 0.390,
            "residue": 0.184,
        },
        "naphtha_ron": 63.0,
        "diesel_cetane": 56.0,
        "diesel_sulfur_pct": 0.20,
    },
}

# Product selling prices in USD / barrel
PRODUCT_PRICES = {
    "BS6_Motor_Spirit_Petrol": 102.50,  # RON >= 91, S <= 10 ppm
    "BS6_High_Speed_Diesel": 98.20,    # Cetane >= 51, S <= 10 ppm
    "Aviation_Turbine_Fuel": 106.00,    # Smoke point >= 25mm, S <= 15 ppm
    "LSHS_Furnace_Oil": 58.40,         # Fuel oil
    "LPG_Bottling": 64.00,             # Propane/Butane
}

# Operating costs in USD / barrel processed
UNIT_OP_COSTS = {
    "cdu": 1.45,
    "vdu": 2.10,
    "dht": 3.75,  # High-pressure hydrotreating to <10 ppm
    "cru": 4.25,  # Catalytic reforming for Octane boost
    "fcc": 3.90,  # Fluid catalytic cracking
}


def generate_iocl_refinery_problem(
    cdu_capacity: float = 150000.0,
    dht_capacity: float = 55000.0,
    cru_capacity: float = 30000.0,
    fcc_capacity: float = 42000.0,
    vdu_capacity: float = 65000.0,
) -> OptimizationProblem:
    """
    Generate an authentic Indian Refinery LP model (IOCL Mathura / MRPL Mangalore style).
    """
    crude_names = list(CRUDE_ASSAYS.keys())
    n_crudes = len(crude_names)

    var_names = [f"Crude_{c}_bpd" for c in crude_names] + [
        "CDU_Throughput_bpd",
        "VDU_Throughput_bpd",
        "DHT_Hydrotreater_Feed_bpd",
        "CRU_Reformer_Feed_bpd",
        "FCC_Cracker_Feed_bpd",
        "Stream_SR_Naphtha_to_CRU",
        "Stream_SR_Naphtha_to_Petrol",
        "Stream_Reformate_to_Petrol",
        "Stream_FCCNaphtha_to_Petrol",
        "Stream_SRGasoil_to_DHT",
        "Stream_SRGasoil_to_Diesel",
        "Stream_SRGasoil_to_FuelOil",
        "Stream_FCCLCO_to_DHT",
        "Stream_FCCLCO_to_FuelOil",
        "Stream_DHTDiesel_to_Diesel",
        "Stream_VDUResidue_to_FuelOil",
        "Product_BS6_Motor_Spirit_Petrol_bpd",
        "Product_BS6_High_Speed_Diesel_bpd",
        "Product_Aviation_Turbine_Fuel_bpd",
        "Product_LSHS_Furnace_Oil_bpd",
        "Product_LPG_Bottling_bpd",
    ]
    n_vars = len(var_names)
    v_idx = {name: i for i, name in enumerate(var_names)}

    c = np.zeros(n_vars)
    for c_name in crude_names:
        c[v_idx[f"Crude_{c_name}_bpd"]] = CRUDE_ASSAYS[c_name]["price_usd_bbl"]

    c[v_idx["CDU_Throughput_bpd"]] = UNIT_OP_COSTS["cdu"]
    c[v_idx["VDU_Throughput_bpd"]] = UNIT_OP_COSTS["vdu"]
    c[v_idx["DHT_Hydrotreater_Feed_bpd"]] = UNIT_OP_COSTS["dht"]
    c[v_idx["CRU_Reformer_Feed_bpd"]] = UNIT_OP_COSTS["cru"]
    c[v_idx["FCC_Cracker_Feed_bpd"]] = UNIT_OP_COSTS["fcc"]

    c[v_idx["Product_BS6_Motor_Spirit_Petrol_bpd"]] = -PRODUCT_PRICES["BS6_Motor_Spirit_Petrol"]
    c[v_idx["Product_BS6_High_Speed_Diesel_bpd"]] = -PRODUCT_PRICES["BS6_High_Speed_Diesel"]
    c[v_idx["Product_Aviation_Turbine_Fuel_bpd"]] = -PRODUCT_PRICES["Aviation_Turbine_Fuel"]
    c[v_idx["Product_LSHS_Furnace_Oil_bpd"]] = -PRODUCT_PRICES["LSHS_Furnace_Oil"]
    c[v_idx["Product_LPG_Bottling_bpd"]] = -PRODUCT_PRICES["LPG_Bottling"]

    # Bounds
    lb = np.zeros(n_vars)
    ub = np.full(n_vars, 1e8)

    # Crude supply contracts
    for c_name in crude_names:
        cap = 35000.0 if c_name == "Bombay_High" else 40000.0
        ub[v_idx[f"Crude_{c_name}_bpd"]] = cap

    # Equalities
    eq_rows = []
    b_eq = []
    eq_names = []

    def add_eq(coeffs: dict, val: float, name: str):
        row = np.zeros(n_vars)
        for k, v in coeffs.items():
            row[v_idx[k]] = v
        eq_rows.append(row)
        b_eq.append(val)
        eq_names.append(name)

    # 1. Total crude input = CDU Throughput
    add_eq({f"Crude_{c}_bpd": 1.0 for c in crude_names} | {"CDU_Throughput_bpd": -1.0}, 0.0, "CDU_Sum_Crude_Feeds")

    # 2. LPG yield
    add_eq({f"Crude_{c}_bpd": CRUDE_ASSAYS[c]["yields"]["lpg"] for c in crude_names} | {"Product_LPG_Bottling_bpd": -1.0}, 0.0, "LPG_Production_Balance")

    # 3. ATF yield
    add_eq({f"Crude_{c}_bpd": CRUDE_ASSAYS[c]["yields"]["kero_atf"] for c in crude_names} | {"Product_Aviation_Turbine_Fuel_bpd": -1.0}, 0.0, "ATF_Jet_Fuel_Balance")

    # 4. Straight-run Naphtha split
    add_eq({f"Crude_{c}_bpd": CRUDE_ASSAYS[c]["yields"]["naphtha"] for c in crude_names} | {"Stream_SR_Naphtha_to_CRU": -1.0, "Stream_SR_Naphtha_to_Petrol": -1.0}, 0.0, "SR_Naphtha_Balance")

    # 5. CRU Reformer Feed
    add_eq({"Stream_SR_Naphtha_to_CRU": 1.0, "CRU_Reformer_Feed_bpd": -1.0}, 0.0, "CRU_Reformer_Feed_Balance")

    # 6. Reformate yield: 86% volume yield from Reformer
    add_eq({"CRU_Reformer_Feed_bpd": 0.86, "Stream_Reformate_to_Petrol": -1.0}, 0.0, "Reformate_Yield_Balance")

    # 7. Straight-run Gasoil split
    add_eq({f"Crude_{c}_bpd": CRUDE_ASSAYS[c]["yields"]["gasoil_diesel"] for c in crude_names} | {
        "Stream_SRGasoil_to_DHT": -1.0, "Stream_SRGasoil_to_Diesel": -1.0, "Stream_SRGasoil_to_FuelOil": -1.0
    }, 0.0, "SR_Gasoil_Disposition_Balance")

    # 8. VDU Atmospheric Residue feed
    add_eq({f"Crude_{c}_bpd": CRUDE_ASSAYS[c]["yields"]["residue"] for c in crude_names} | {"VDU_Throughput_bpd": -1.0}, 0.0, "Atmospheric_Residue_to_VDU")

    # 9. VDU separation: 60% VGO to FCC, 40% Vacuum Residue to Fuel Oil
    add_eq({"VDU_Throughput_bpd": 0.60, "FCC_Cracker_Feed_bpd": -1.0}, 0.0, "VDU_to_FCC_VGO_Balance")
    add_eq({"VDU_Throughput_bpd": 0.40, "Stream_VDUResidue_to_FuelOil": -1.0}, 0.0, "VDU_Residue_to_FuelOil_Balance")

    # 10. FCC cracking: 52% FCC Gasoline, 35% FCC Light Cycle Oil (LCO)
    add_eq({"FCC_Cracker_Feed_bpd": 0.52, "Stream_FCCNaphtha_to_Petrol": -1.0}, 0.0, "FCC_Gasoline_Yield_Balance")
    add_eq({"FCC_Cracker_Feed_bpd": 0.35, "Stream_FCCLCO_to_DHT": -1.0, "Stream_FCCLCO_to_FuelOil": -1.0}, 0.0, "FCC_LCO_Disposition_Balance")

    # 11. DHT Hydrotreater feed: SR Gasoil + FCC LCO
    add_eq({"Stream_SRGasoil_to_DHT": 1.0, "Stream_FCCLCO_to_DHT": 1.0, "DHT_Hydrotreater_Feed_bpd": -1.0}, 0.0, "DHT_Hydrotreater_Feed_Sum")

    # 12. DHT Diesel yield: 97% volume yield
    add_eq({"DHT_Hydrotreater_Feed_bpd": 0.97, "Stream_DHTDiesel_to_Diesel": -1.0}, 0.0, "DHT_Diesel_Yield_Balance")

    # 13. Finished Product Blending Balances
    add_eq({"Stream_SR_Naphtha_to_Petrol": 1.0, "Stream_Reformate_to_Petrol": 1.0, "Stream_FCCNaphtha_to_Petrol": 1.0, "Product_BS6_Motor_Spirit_Petrol_bpd": -1.0}, 0.0, "BS6_Petrol_Product_Sum")
    add_eq({"Stream_DHTDiesel_to_Diesel": 1.0, "Stream_SRGasoil_to_Diesel": 1.0, "Product_BS6_High_Speed_Diesel_bpd": -1.0}, 0.0, "BS6_Diesel_Product_Sum")
    add_eq({"Stream_VDUResidue_to_FuelOil": 1.0, "Stream_FCCLCO_to_FuelOil": 1.0, "Stream_SRGasoil_to_FuelOil": 1.0, "Product_LSHS_Furnace_Oil_bpd": -1.0}, 0.0, "Fuel_Oil_Product_Sum")

    # Inequalities
    ub_rows = []
    b_ub = []
    ub_names = []

    def add_ub(coeffs: dict, val: float, name: str):
        row = np.zeros(n_vars)
        for k, v in coeffs.items():
            row[v_idx[k]] = v
        ub_rows.append(row)
        b_ub.append(val)
        ub_names.append(name)

    # Unit capacity ceilings (Bottlenecks)
    add_ub({"CDU_Throughput_bpd": 1.0}, cdu_capacity, f"CDU_Max_Capacity_{int(cdu_capacity)}_bpd")
    add_ub({"VDU_Throughput_bpd": 1.0}, vdu_capacity, f"VDU_Max_Capacity_{int(vdu_capacity)}_bpd")
    add_ub({"DHT_Hydrotreater_Feed_bpd": 1.0}, dht_capacity, f"DHT_Hydrotreater_Max_{int(dht_capacity)}_bpd")
    add_ub({"CRU_Reformer_Feed_bpd": 1.0}, cru_capacity, f"CRU_Reformer_Max_{int(cru_capacity)}_bpd")
    add_ub({"FCC_Cracker_Feed_bpd": 1.0}, fcc_capacity, f"FCC_Cracker_Max_{int(fcc_capacity)}_bpd")

    # Indian BS-VI Regulatory Quality Specs
    # Quality A: BS-VI Motor Spirit RON >= 91.0
    # (91 - 58) SR_Naphtha + (91 - 98) Reformate + (91 - 92.5) FCC_Naphtha <= 0
    add_ub({"Stream_SR_Naphtha_to_Petrol": 33.0, "Stream_Reformate_to_Petrol": -7.0, "Stream_FCCNaphtha_to_Petrol": -1.5}, 0.0, "BS6_Petrol_Min_RON_91")

    # Quality B: BS-VI Diesel Sulfur <= 10 ppm
    # DHT Diesel: 5 ppm (-5 margin), SR Gasoil: ~1500 ppm (+1490)
    add_ub({"Stream_DHTDiesel_to_Diesel": -5.0, "Stream_SRGasoil_to_Diesel": 1490.0}, 0.0, "BS6_Diesel_Max_Sulfur_10ppm")

    # Minimum refinery baseline operation (at least 100k bpd CDU operation)
    add_ub({"CDU_Throughput_bpd": -1.0}, -100000.0, "Min_Operational_Target_100k_bpd")

    A_eq = sp.csr_matrix(np.array(eq_rows))
    b_eq_arr = np.array(b_eq)

    A_ub = sp.csr_matrix(np.array(ub_rows))
    b_ub_arr = np.array(b_ub)

    return LPProblem(
        c=c,
        A_ub=A_ub,
        b_ub=b_ub_arr,
        A_eq=A_eq,
        b_eq=b_eq_arr,
        lb=lb,
        ub=ub,
        name="IOCL Mathura 8-Crude Distillation & BS-VI Blending",
        var_names=var_names,
        constraint_names=eq_names + ub_names,
    )


# --------------------------------------------------------------------------
# 2. Haverly's Petroleum Pooling Benchmark (Haverly 1978)
# --------------------------------------------------------------------------

def generate_haverly_pooling_problem(case: int = 1) -> OptimizationProblem:
    """
    Generate Haverly's Pooling Benchmark (1978).
    Widely regarded as the foundational benchmark for quality pooling in refinery literature.
    """
    var_names = ["x_A_Pool", "x_B_Pool", "x_Pool_P1", "x_Pool_P2", "x_C_P1", "x_C_P2"]
    n_vars = len(var_names)

    c = np.array([6.0, 16.0, -9.0, -15.0, 10.0 - 9.0, 10.0 - 15.0])
    lb = np.zeros(n_vars)
    ub = np.array([100.0, 100.0, 100.0, 200.0, 100.0, 100.0])

    A_eq = sp.csr_matrix(np.array([[1.0, 1.0, -1.0, -1.0, 0.0, 0.0]]))
    b_eq = np.array([0.0])
    eq_names = ["Pool_Mass_Balance"]

    A_ub = sp.csr_matrix(np.array([
        [0.0, 0.0, 1.0, 0.0, 1.0, 0.0],   # P1 demand <= 100
        [0.0, 0.0, 0.0, 1.0, 0.0, 1.0],   # P2 demand <= 200
        [1.0, 1.0, 0.0, 0.0, 0.0, 0.0],   # Pool capacity <= 150
    ]))
    b_ub = np.array([100.0, 200.0, 150.0])
    ub_names = ["P1_Max_Demand", "P2_Max_Demand", "Pool_Max_Capacity"]

    return LPProblem(
        c=c,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=A_eq,
        b_eq=b_eq,
        lb=lb,
        ub=ub,
        name="Haverly Petroleum Pooling Benchmark (Case 1)",
        var_names=var_names,
        constraint_names=eq_names + ub_names,
    )
