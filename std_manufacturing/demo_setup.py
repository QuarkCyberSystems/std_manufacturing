"""
End-to-end demo data setup matching SAP Costing Cycle.xlsx exactly.

Creates opening inventory, purchases, overhead JEs, process orders, power production,
and runs the full costing cycle to produce CPUs matching SAP results.

Run via: bench --site badia.localhost execute std_manufacturing.demo_setup.setup_all
"""

import frappe
from frappe.utils import flt


COMPANY = "Badia Cement PSJ"
COMPANY_ABBR = "BCP"
WAREHOUSE = f"Stores - {COMPANY_ABBR}"

# ─── CC Helper ───────────────────────────────────────────────────────────────

def cc(sap_code):
	"""Map SAP cost center code to Frappe CC name."""
	from std_manufacturing.patches.setup_costing_master_data import _cc_full_name
	return _cc_full_name(sap_code)


# ══════════════════════════════════════════════════════════════════════════════
# 1. OPENING INVENTORY — from "1-1-2020 - Summary" sheet
# Format: (item_code, item_name, item_group, stock_uom, opening_qty, opening_value, std_rate)
# ══════════════════════════════════════════════════════════════════════════════

OPENING_INVENTORY = [
	# Finished goods
	("100929", "CEM II Pouzzolana 32.5 N/silos", "Finished Goods", "Tonne", 12638, 243692402.52, 19282.51),
	("2000004", "CEM II Pouzzolana 32.5 N/Bags", "Finished Goods", "Tonne", 0, 0, 22704.99),
	("2000100", "CEM II 42,5 N/Bags", "Finished Goods", "Tonne", 0, 0, 24009.95),
	("2000101", "CEM II 42.5 N / Bulk", "Finished Goods", "Tonne", 26534, 557784187.04, 21021.49),

	# Semi-finished goods
	("120002", "Pouzzolana/ground Fine", "Raw Material", "Tonne", 556667, 4876673097.77, 8760.49),
	("120006", "Limestone/crushed", "Sub Assemblies", "Tonne", 15167, 18051408.12, 1190.18),
	("120036", "Limestone/mined", "Sub Assemblies", "Tonne", 1377086, 1280610489.08, 929.94),
	("120049", "Iron ore/high level", "Raw Material", "Tonne", 4017, 144339123.32, 35932.07),
	("120070", "Gypsum/dihydrate/mined", "Raw Material", "Tonne", 24893, 203541738.72, 8176.67),
	("120083", "Raw meal/grey/common", "Sub Assemblies", "Tonne", 7005.56, 19623743.05, 2801.17),
	("120097", "Clinker/grey/common", "Sub Assemblies", "Tonne", 648138, 11906684927.35, 18370.60),
	("120119", "Coal/BTZ/ground", "Raw Material", "Tonne", 57421, 4280034303.96, 74537.79),
	("120124", "Solid fuels blend/ground", "Sub Assemblies", "Tonne", 240, 19814145.42, 82558.94),
	("120238", "Silica sand", "Raw Material", "Tonne", 37524, 212399291.98, 5660.36),
	("120402", "Limestone/blasted", "Raw Material", "Tonne", 0, 0, 348.16),
	("120412", "Basalt/mined", "Sub Assemblies", "Tonne", 230755, 281364579.81, 1219.32),
	("120413", "Basalt/crushed", "Sub Assemblies", "Tonne", 36055, 65260013.61, 1810.01),
	("120417", "Basalt/blasted", "Raw Material", "Tonne", 2500, 1132648.08, 453.06),

	# Fuels
	("2000011", "LFO - Light Fuel Oil", "Raw Material", "Tonne", 116998, 44121038.91, 377.11),
	("2000012", "HFO - Heavy Fuel Oil", "Raw Material", "Tonne", 9009.90, 2102717121.02, 233378.52),
	("2000040", "Gasoline", "Raw Material", "Litre", 0, 0, 500.00),

	# Explosives & consumables
	("2000006", "Amonium Nitrate Explosive", "Raw Material", "Kg", 8.5, 2763.12, 325.07),
	("2000007", "Dynamite Explosive", "Raw Material", "Kg", 35, 119000, 3400.00),
	("2000008", "Corde Explosive", "Raw Material", "Kg", 1867, 453054.99, 242.66),
	("2000009", "Fues Explosive material", "Raw Material", "Kg", 6406, 746559.74, 116.54),
	("2000010", "CO2 Gas", "Raw Material", "Tonne", 9.91, 3614535.85, 364736.21),
	("2000060", "Slow Match Explosive", "Raw Material", "Kg", 4000, 80000, 20.00),
	("2000061", "Normal Fues Explosive", "Raw Material", "Kg", 4000, 120000, 30.00),
	("2000075", "Local Dynamite", "Raw Material", "Kg", 733, 3181438.52, 4340.30),
	("2000141", "Electrical Wire 0.5 M.M", "Raw Material", "Meter", 35896, 1550871.03, 43.20),
	("2000142", "Electrical Wire 0.9 M.M", "Raw Material", "Meter", 14355, 693452.78, 48.31),
	("2000150", "M.M.D.T Fitted Explosive", "Raw Material", "Kg", 0, 0, 700.00),

	# Packaging
	("3100051", "Bags CEM II 42.5N G=90 2 layers", "Raw Material", "Nos", 4982, 490022.72, 98.36),
	("3100061", "Bags CEM II 32.5N PolyPropylene", "Raw Material", "Nos", 987334, 84404445.78, 85.49),
	("3100070", "Bags CEM II 42.5N PolyPropylene", "Raw Material", "Nos", 1401368, 156706810.66, 111.82),
	("3100080", "Bags CEM II 42.5N Gray PP", "Raw Material", "Nos", 185427, 22819301.92, 123.06),
	("3100090", "Bags CEM II 32.5N Blue PP", "Raw Material", "Nos", 556479, 89393871.69, 160.64),
]


# ══════════════════════════════════════════════════════════════════════════════
# 2. PURCHASED MATERIALS — from "Purchased Materials YTD CPU" sheet
# Format: (item_code, jan_qty, jan_value, feb_qty, feb_value)
# ══════════════════════════════════════════════════════════════════════════════

PURCHASES = [
	("120002", 130266.73, 1172400570, 58123.80, 523114200),
	("120070", 20995.92, 174266136, 3019.85, 25064755),
	("120119", 0, 0, 7520.83, 965674572),
	("120238", 0, 0, 21867.60, 130768248),
	("120402", 23362.98, 8133966.99, 329466.17, 44068932.87),
	("2000011", 83773.00, 25040884.00, 224463.00, 102084929.00),
	("2000012", 3679.00, 812027721.93, 3229.85, 713346410.28),
	("2000040", 300, 150000, 24014, 16449590),
	("2000141", 0, 0, 18000, 905400.00),
	("2000150", 0, 0, 48750, 34125000),
	("3100061", 910000, 161700000, 732399, 131400000),
	("3100070", 1010000, 171700000, 1011051, 181800000),
	("3100080", 1240000, 212130000, 490000, 88200000),
	("3100090", 440000, 79200000, 50479, 9000000),
]


# ══════════════════════════════════════════════════════════════════════════════
# 3. OVERHEAD COSTS — from "OH CC" sheet (exact SAP amounts per CC per month)
# Format: {cc_sap_code: (jan_amount, feb_amount)}
# ══════════════════════════════════════════════════════════════════════════════

OH_CC = {
	"R10100900M": (15490975.79, 23762478.38),
	"R10100900P": (9509342.84, 8896717.79),
	"R10100930N": (54286998.05, 84842232.46),
	"R10100A10S": (228557205.71, 230871015.20),
	"R10100A20S": (2548408.39, 2564944.96),
	"R10100A30S": (9047615.91, 22001920.89),
	"R10100A40S": (2476247.42, 4852635.79),
	"R10100A50S": (5923095.75, 11874286.19),
	"R101P0300C": (10364224.23, 9695564.62),
	"R101P0310C": (20019004.01, 21841158.00),
	"R101P0400D": (4531007.14, 4281033.81),
	"R101P0410D": (2296533.96, 2148370.47),
	"R101P0610F": (13655174.26, 12956220.09),
	"R101P0700P": (1352704.70, 1265433.40),
	"R101P0800P": (4843208.91, 4530743.81),
	"R101P0810P": (1475200.96, 1380026.71),
	"R101P4100A": (34015871.41, 96423665.89),
	"R101P4110A": (8457764.05, 24173183.99),
	"R101P4700A": (1656431.28, 1549564.75),
	"R101P4710A": (1441184.15, 1348204.53),
	"R101P5110A": (4675601.17, 57826272.08),
	"R101P5120A": (201619.80, 39352089.75),
	"R101P5190A": (10193516.25, 9535870.05),
	"R101P6100A": (761636.55, 16466110.69),
	"R101P6190A": (4181108.04, 3911359.13),
	"R101P6200A": (0.00, 17668229.11),
}


# ══════════════════════════════════════════════════════════════════════════════
# 4. MAINTENANCE COSTS — from "Maintenance Orders CC" sheet
# Format: {cc_sap_code: (jan_amount, feb_amount)}
# ══════════════════════════════════════════════════════════════════════════════

MAINTENANCE_CC = {
	"R10100900P": (82194990.90, 151705143.03),
	"R10100A10S": (11386726.69, 15079083.36),
	"R101P0300C": (2092052.91, 4496195.93),
	"R101P0400D": (11760630.94, 30487653.45),
	"R101P0410D": (0.00, 185829.29),
	"R101P0610F": (4630374.39, 17406229.68),
	"R101P0700P": (1826683.85, 1105809.72),
	"R101P0800P": (119182069.68, 29347284.70),
	"R101P4100A": (772236.46, 10015373.91),
	"R101P4110A": (4048808.16, 13265543.93),
	"R101P4120A": (0.00, 201045.88),
	"R101P4130A": (0.00, 341554.99),
	"R101P4710A": (0.00, 4315.00),
}


# ══════════════════════════════════════════════════════════════════════════════
# 5. KWH DATA — from "Cycle 5 Exercise" sheet (YTD totals)
# Map resource codes to SAP CC codes and KWH consumed
# ══════════════════════════════════════════════════════════════════════════════

# Jan KWH (from KWH Transactions aggregated)
JAN_KWH = {
	"R101P4100A": 202208,      # CRUSHR01 = Limestone crusher
	"R101P4110A": 140757,      # CRUSHR02 = Basalt crusher
	"R101P0700P": 1039428,     # COAMIV01 = Coal mill
	"R101P0800P": 4704309,     # RMILLV01 = Raw mill
	"R101P0300C": 5130598,     # KILN01 = Kiln
	"R101P0400D": 1226418,     # FINMIB01 = Cement mill (= FEB_YTD 4,708,863 - FEB 3,482,445)
	"R101P0610F": 2706227,     # PACKER01+02+03 = Bag pack (= FEB_YTD 2,804,584 - FEB 98,357)
	"R101P0310C": 0,           # Clinker bins
	"R10100A10S": 524795,      # General services (balance = generated - sum of others)
}
JAN_KWH_GENERATED = 15674740  # = FEB_YTD 29,894,950 - FEB 14,220,210

# Feb KWH (from KWH Transactions aggregated)
FEB_KWH = {
	"R101P4100A": 188747,
	"R101P4110A": 130415,
	"R101P0700P": 978952,
	"R101P0800P": 4198511,
	"R101P0300C": 4776975,
	"R101P0400D": 3482445,
	"R101P0610F": 98357,       # PACKER01+02+03
	"R101P0310C": 93534,       # Clinker bins
	"R10100A10S": 272274,      # General services (= FEB_YTD 797,069 - JAN 524,795)
}
FEB_KWH_GENERATED = 14220210

# Feb YTD (from Cycle 5 Exercise - authoritative)
FEB_YTD_KWH = {
	"R101P4100A": 390955,
	"R101P4110A": 271172,
	"R101P0700P": 2018380,
	"R101P0800P": 8902820,
	"R101P0300C": 9907573,
	"R101P0400D": 4708863,
	"R101P0610F": 2804584,
	"R101P0310C": 93534,
	"R10100A10S": 797069,
}
FEB_YTD_KWH_GENERATED = 29894950


# ══════════════════════════════════════════════════════════════════════════════
# 6. PROCESS ORDER TRANSACTIONS — from "Process Orders Transactions" sheet
# Net quantities: production (101-102), consumption (abs(261-262))
# Format per order: { "output": {material: (jan_qty, feb_qty)},
#                     "input":  {material: (jan_qty, feb_qty)} }
# ══════════════════════════════════════════════════════════════════════════════

# SAP Process Order to CC mapping (from References sheet)
ORDER_CC_MAP = {
	1001998: "R101P5110A",   # Limestone/blasted → Blasted Lim Quarry
	1001999: "R101P6100A",   # Basalt/blasted → Blasted Bas Quarry
	1002000: "R101P5120A",   # Limestone/mined → Limestone Mined
	1002003: "R101P4100A",   # Limestone crushed → Limestone Crusher
	1002004: "R101P4110A",   # Basalt crushed → Basalt Crusher
	1002005: "R101P0700P",   # Solid fuels/blend/ground → Coal Mill
	1002006: "R101P0800P",   # Raw meal/grey/common → Raw Mill
	1002007: "R101P0300C",   # Clinker/grey/common → Kiln
	1002008: "R101P0400D",   # CEM II 42.5 N/silos → Cement Mill
	1002009: "R101P0400D",   # CEM II 32.5 N/silos → Cement Mill
	1002010: "R101P0610F",   # CEM II 42.5 N/Bags → Bag Pack
	1002011: "R101P0610F",   # CEM I 32.5 N/bags → Bag Pack
	# Power generation orders → Power HFO & LFO CC
	1002012: "R10100900P",
	1002013: "R10100900P",
	1002014: "R10100900P",
	1002015: "R10100900P",
	1002016: "R10100900P",
	1002017: "R10100900P",
	# Feb orders (same materials, new SAP order numbers)
	1002018: "R101P5110A",
	1002019: "R101P6100A",
	1002020: "R101P5120A",
	1002021: "R101P6200A",
	1002022: "R101P4100A",
	1002023: "R101P4110A",
	1002024: "R101P0700P",
	1002025: "R101P0800P",
	1002026: "R101P0300C",
	1002027: "R101P0400D",
	1002028: "R101P0400D",
	1002029: "R101P0610F",
	1002030: "R101P0610F",
	1002031: "R10100900P",
	1002032: "R10100900P",
	1002033: "R10100900P",
	1002034: "R10100900P",
	1002035: "R10100900P",
	1002036: "R10100900P",
}

# Production output quantities (net 101 - 102)
# {material: (jan_total, feb_total)}
PRODUCTION_OUTPUT = {
	"120402": (6220.54, 225777.00),       # Limestone/blasted
	"120417": (3711.86, 81285.40),        # Basalt/blasted
	"120036": (390.32, 169507.45),        # Limestone/mined
	"120006": (222541.60, 226697.05),     # Limestone/crushed
	"120412": (0, 56799.82),              # Basalt/mined
	"120413": (42848.26, 48297.06),       # Basalt/crushed
	"120124": (20556.84, 18826.09),       # Solid fuels/ground
	"120083": (259550.16, 283076.16),     # Raw meal
	"120097": (162740.95, 172427.32),     # Clinker
	"2000101": (70507.97, 54460.21),      # CEM II 42.5N/bulk
	"100929": (32666.82, 36254.05),       # CEM II 32.5N/silos
	"2000100": (59873.00, 33038.00),      # CEM II 42.5N/bags
	"2000004": (31850.00, 29404.00),      # CEM II 32.5N/bags
}

# Consumption input quantities — by process order, material, month
# Fuel consumed in power generation (needed for fuel revaluation)
POWER_FUEL_CONSUMPTION = {
	# (material, jan_qty, feb_qty)
	"2000012": (3373.61, 3045.92),   # HFO total across power orders
	"2000011": (55126.00, 57671.40), # LFO total across power orders
}

# Fuel consumed in cement production (CEM orders 1002008/1002009 + 1002027/1002028)
CEMENT_FUEL_CONSUMPTION = {
	"2000011": (51557.00, 21836.00),  # LFO in cement mill
	"2000012": (132.85, 116.20),      # HFO in cement mill
}


# ══════════════════════════════════════════════════════════════════════════════
# 7. PRODUCTION RECIPES — map output items to cost centers and recipes
# ══════════════════════════════════════════════════════════════════════════════

RECIPES = [
	{
		"recipe_code": "LIME-BLAST",
		"recipe_name": "Limestone Blasting",
		"production_phase": "Quarry",
		"phase_sequence": 10,
		"cost_center": "R101P5110A",
		"output_item": "120402",
		"input_items": [],  # No RM inputs — explosives are in CC overhead
	},
	{
		"recipe_code": "BASALT-BLAST",
		"recipe_name": "Basalt Blasting",
		"production_phase": "Quarry",
		"phase_sequence": 11,
		"cost_center": "R101P6100A",
		"output_item": "120417",
		"input_items": [],  # No RM inputs — explosives are in CC overhead
	},
	{
		"recipe_code": "LIME-MINE",
		"recipe_name": "Limestone Mining",
		"production_phase": "Quarry",
		"phase_sequence": 12,
		"cost_center": "R101P5120A",
		"output_item": "120036",
		"input_items": [
			{"item_code": "120402", "qty_per_unit": 1.0},
		],
	},
	{
		"recipe_code": "BASALT-MINE",
		"recipe_name": "Basalt Mining",
		"production_phase": "Quarry",
		"phase_sequence": 13,
		"cost_center": "R101P6200A",
		"output_item": "120412",
		"input_items": [
			{"item_code": "120417", "qty_per_unit": 0.437},
		],
	},
	{
		"recipe_code": "LIME-CRUSH",
		"recipe_name": "Limestone Crushing",
		"production_phase": "Crusher",
		"phase_sequence": 20,
		"cost_center": "R101P4100A",
		"output_item": "120006",
		"input_items": [
			{"item_code": "120402", "qty_per_unit": 0.103},
			{"item_code": "120036", "qty_per_unit": 0.897},
		],
	},
	{
		"recipe_code": "BASALT-CRUSH",
		"recipe_name": "Basalt Crushing",
		"production_phase": "Crusher",
		"phase_sequence": 21,
		"cost_center": "R101P4110A",
		"output_item": "120413",
		"input_items": [
			{"item_code": "120417", "qty_per_unit": 0.300},
			{"item_code": "120412", "qty_per_unit": 0.700},
		],
	},
	{
		"recipe_code": "COAL-GRIND",
		"recipe_name": "Solid Fuel Grinding",
		"production_phase": "Coal Mill",
		"phase_sequence": 25,
		"cost_center": "R101P0700P",
		"output_item": "120124",
		"input_items": [
			{"item_code": "120119", "qty_per_unit": 1.026},
		],
	},
	{
		"recipe_code": "RAW-MEAL",
		"recipe_name": "Raw Meal Production",
		"production_phase": "Raw Mill",
		"phase_sequence": 30,
		"cost_center": "R101P0800P",
		"output_item": "120083",
		"input_items": [
			{"item_code": "120006", "qty_per_unit": 0.819},
			{"item_code": "120413", "qty_per_unit": 0.110},
			{"item_code": "120070", "qty_per_unit": 0.007},
			{"item_code": "120238", "qty_per_unit": 0.030},
		],
	},
	{
		"recipe_code": "CLINKER",
		"recipe_name": "Clinker Production",
		"production_phase": "Kiln",
		"phase_sequence": 40,
		"cost_center": "R101P0300C",
		"output_item": "120097",
		"input_items": [
			{"item_code": "120083", "qty_per_unit": 1.585},
			{"item_code": "120124", "qty_per_unit": 0.119},
			{"item_code": "2000010", "qty_per_unit": 0.000008},
		],
	},
	{
		"recipe_code": "CEM-425",
		"recipe_name": "CEM II 42.5N Grinding",
		"production_phase": "Cement Mill",
		"phase_sequence": 50,
		"cost_center": "R101P0400D",
		"output_item": "2000101",
		"input_items": [
			{"item_code": "120097", "qty_per_unit": 0.817},
			{"item_code": "120002", "qty_per_unit": 0.157},
			{"item_code": "120070", "qty_per_unit": 0.046},
			{"item_code": "2000011", "qty_per_unit": 0.403},
			{"item_code": "2000012", "qty_per_unit": 0.001},
		],
	},
	{
		"recipe_code": "CEM-325",
		"recipe_name": "CEM II 32.5N Grinding",
		"production_phase": "Cement Mill",
		"phase_sequence": 51,
		"cost_center": "R101P0400D",
		"output_item": "100929",
		"input_items": [
			{"item_code": "120097", "qty_per_unit": 0.698},
			{"item_code": "120002", "qty_per_unit": 0.289},
			{"item_code": "120070", "qty_per_unit": 0.046},
			{"item_code": "2000011", "qty_per_unit": 0.635},
			{"item_code": "2000012", "qty_per_unit": 0.001},
		],
	},
	{
		"recipe_code": "PACK-425",
		"recipe_name": "CEM II 42.5N Bagging",
		"production_phase": "Packing",
		"phase_sequence": 60,
		"cost_center": "R101P0610F",
		"output_item": "2000100",
		"input_items": [
			{"item_code": "2000101", "qty_per_unit": 1.000},
			{"item_code": "3100070", "qty_per_unit": 19.94},
			{"item_code": "3100080", "qty_per_unit": 11.24},
		],
	},
	{
		"recipe_code": "PACK-325",
		"recipe_name": "CEM II 32.5N Bagging",
		"production_phase": "Packing",
		"phase_sequence": 61,
		"cost_center": "R101P0610F",
		"output_item": "2000004",
		"input_items": [
			{"item_code": "100929", "qty_per_unit": 1.002},
			{"item_code": "3100061", "qty_per_unit": 13.42},
			{"item_code": "3100090", "qty_per_unit": 5.91},
		],
	},
]

# Production Phases
PHASES = [
	{"phase_name": "Quarry", "sequence": 10, "description": "Blasting and mining of raw stone"},
	{"phase_name": "Crusher", "sequence": 20, "description": "Primary and secondary crushing"},
	{"phase_name": "Coal Mill", "sequence": 25, "description": "Solid fuel grinding"},
	{"phase_name": "Raw Mill", "sequence": 30, "description": "Raw meal grinding and blending"},
	{"phase_name": "Kiln", "sequence": 40, "description": "Clinker burning (pyroprocessing)"},
	{"phase_name": "Cement Mill", "sequence": 50, "description": "Cement grinding and blending"},
	{"phase_name": "Packing", "sequence": 60, "description": "Bagging and bulk loading"},
]


# ══════════════════════════════════════════════════════════════════════════════
# OVERHEAD ACCOUNT MAPPING
# ══════════════════════════════════════════════════════════════════════════════

OVERHEAD_ACCOUNTS = {
	"depreciation": "Depreciation - BCP",
	"maintenance": "Office Maintenance Expenses - BCP",
	"utilities": "Utility Expenses - BCP",
	"labor": "Salary - BCP",
	"admin": "Administrative Expenses - BCP",
	"misc": "Miscellaneous Expenses - BCP",
}


# ══════════════════════════════════════════════════════════════════════════════
# SETUP FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def create_items():
	"""Create all items from opening inventory with SAP item codes."""
	for group in ["Sub Assemblies", "Finished Goods", "Raw Material"]:
		if not frappe.db.exists("Item Group", group):
			frappe.get_doc({"doctype": "Item Group", "item_group_name": group,
				"parent_item_group": "All Item Groups"}).insert(ignore_permissions=True)

	created = 0
	for item_code, item_name, item_group, stock_uom, qty, value, std_rate in OPENING_INVENTORY:
		if frappe.db.exists("Item", item_code):
			frappe.db.set_value("Item", item_code, {
				"custom_cost_category": "Purchased" if item_group == "Raw Material" else ("Semi-Finished" if item_group == "Sub Assemblies" else "Finished"),
				"custom_include_in_plcv": 1,
				"custom_valuation_method": "Standard Cost",
			})
			continue

		cost_cat = "Purchased" if item_group == "Raw Material" else ("Semi-Finished" if item_group == "Sub Assemblies" else "Finished")
		doc = frappe.get_doc({
			"doctype": "Item",
			"item_code": item_code,
			"item_name": item_name,
			"item_group": item_group,
			"stock_uom": stock_uom,
			"is_stock_item": 1,
			"custom_valuation_method": "Standard Cost",
			"custom_cost_category": cost_cat,
			"custom_include_in_plcv": 1,
			"standard_rate": std_rate,
		})
		doc.insert(ignore_permissions=True)
		created += 1

	frappe.db.commit()
	print(f"Items: {created} created")


def create_phases():
	"""Create production phases."""
	created = 0
	for phase in PHASES:
		if frappe.db.exists("Production Phase", phase["phase_name"]):
			continue
		frappe.get_doc({"doctype": "Production Phase", **phase}).insert(ignore_permissions=True)
		created += 1
	frappe.db.commit()
	print(f"Production Phases: {created} created")


def create_recipes():
	"""Create production recipes with inputs."""
	created = 0
	for r in RECIPES:
		recipe_name = f"RECIPE-{r['recipe_code']}"
		if frappe.db.exists("Production Recipe", recipe_name):
			continue

		output_uom = frappe.db.get_value("Item", r["output_item"], "stock_uom") or "Tonne"
		doc = frappe.get_doc({
			"doctype": "Production Recipe",
			"recipe_code": r["recipe_code"],
			"recipe_name": r["recipe_name"],
			"company": COMPANY,
			"production_phase": r["production_phase"],
			"phase_sequence": r["phase_sequence"],
			"cost_center": cc(r["cost_center"]),
			"output_item": r["output_item"],
			"output_uom": output_uom,
			"is_active": 1,
			"input_items": [
				{"item_code": inp["item_code"], "qty_per_unit": inp["qty_per_unit"],
				 "source_warehouse": WAREHOUSE}
				for inp in r["input_items"]
			],
		})
		doc.insert(ignore_permissions=True)
		created += 1

	# Link items to recipes
	for r in RECIPES:
		recipe_name = f"RECIPE-{r['recipe_code']}"
		frappe.db.set_value("Item", r["output_item"], "custom_production_recipe", recipe_name)

	frappe.db.commit()
	print(f"Production Recipes: {created} created")


def create_standard_cost_rates():
	"""Create Standard Cost Rate records for all items with opening values."""
	created = 0
	for item_code, _, _, _, _, _, std_rate in OPENING_INVENTORY:
		if std_rate <= 0:
			continue
		scr_name = f"SCR-{item_code}-2020-01-01"
		if frappe.db.exists("Standard Cost Rate", scr_name):
			continue
		if not frappe.db.exists("Item", item_code):
			continue

		doc = frappe.get_doc({
			"doctype": "Standard Cost Rate",
			"item_code": item_code,
			"standard_rate": std_rate,
			"effective_from": "2020-01-01",
			"fiscal_year": "2020",
			"rate_basis": "Budget",
			"status": "Active",
		})
		doc.insert(ignore_permissions=True)
		doc.submit()
		created += 1

	frappe.db.commit()
	print(f"Standard Cost Rates: {created} created")


def create_opening_stock():
	"""Create opening stock via Material Receipt Stock Entries dated Dec 31, 2019."""
	created = 0
	for item_code, _, _, _, qty, value, std_rate in OPENING_INVENTORY:
		if flt(qty) <= 0:
			continue

		se = frappe.get_doc({
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": COMPANY,
			"set_posting_time": 1,
			"posting_date": "2019-12-31",
			"items": [{
				"item_code": item_code,
				"qty": qty,
				"basic_rate": std_rate,
				"t_warehouse": WAREHOUSE,
			}],
		})
		se.insert(ignore_permissions=True)
		se.submit()
		created += 1

	frappe.db.commit()
	print(f"Opening Stock Entries: {created} created")


def create_purchase_receipts(month_idx):
	"""Create purchase receipts for a month (0=Jan, 1=Feb)."""
	month_name = "January" if month_idx == 0 else "February"
	posting_date = "2020-01-15" if month_idx == 0 else "2020-02-15"

	supplier = _get_or_create_supplier()
	created = 0

	for item_code, jan_qty, jan_val, feb_qty, feb_val in PURCHASES:
		qty = jan_qty if month_idx == 0 else feb_qty
		val = jan_val if month_idx == 0 else feb_val
		if flt(qty) <= 0:
			continue

		actual_rate = flt(val) / flt(qty)

		pr = frappe.get_doc({
			"doctype": "Purchase Receipt",
			"supplier": supplier,
			"company": COMPANY,
			"set_posting_time": 1,
			"posting_date": posting_date,
			"items": [{
				"item_code": item_code,
				"qty": qty,
				"rate": actual_rate,
				"warehouse": WAREHOUSE,
			}],
		})
		pr.insert(ignore_permissions=True)
		pr.submit()
		created += 1

	frappe.db.commit()
	print(f"  {month_name} Purchase Receipts: {created} created")


def create_overhead_jes(month_idx):
	"""Create Journal Entries for overhead costs posting exact SAP amounts per CC."""
	month_name = "January" if month_idx == 0 else "February"
	posting_date = "2020-01-31" if month_idx == 0 else "2020-02-29"

	# OH CC entries
	oh_created = 0
	for sap_code, (jan_amt, feb_amt) in OH_CC.items():
		amt = jan_amt if month_idx == 0 else feb_amt
		if amt <= 0:
			continue

		cc_name = cc(sap_code)
		je = frappe.get_doc({
			"doctype": "Journal Entry",
			"company": COMPANY,
			"posting_date": posting_date,
			"user_remark": f"OH CC {sap_code} - {month_name} 2020",
			"accounts": [
				{
					"account": "Miscellaneous Expenses - BCP",
					"debit_in_account_currency": amt,
					"cost_center": cc_name,
				},
				{
					"account": "Salary - BCP",
					"credit_in_account_currency": amt,
				},
			],
		})
		je.insert(ignore_permissions=True)
		je.submit()
		oh_created += 1

	# Maintenance entries
	maint_created = 0
	for sap_code, (jan_amt, feb_amt) in MAINTENANCE_CC.items():
		amt = jan_amt if month_idx == 0 else feb_amt
		if amt <= 0:
			continue

		cc_name = cc(sap_code)
		je = frappe.get_doc({
			"doctype": "Journal Entry",
			"company": COMPANY,
			"posting_date": posting_date,
			"user_remark": f"Maintenance {sap_code} - {month_name} 2020",
			"accounts": [
				{
					"account": "Office Maintenance Expenses - BCP",
					"debit_in_account_currency": amt,
					"cost_center": cc_name,
				},
				{
					"account": "Salary - BCP",
					"credit_in_account_currency": amt,
				},
			],
		})
		je.insert(ignore_permissions=True)
		je.submit()
		maint_created += 1

	frappe.db.commit()
	print(f"  {month_name} JEs: {oh_created} overhead + {maint_created} maintenance")


def create_process_orders(costing_period, month_idx):
	"""Create Process Orders with production quantities for a month."""
	from std_manufacturing.api.process_order import create_process_orders_for_period

	# Auto-create process orders from recipes
	create_process_orders_for_period(costing_period)

	# Populate output quantities
	orders = frappe.get_all("Process Order",
		filters={"costing_period": costing_period, "docstatus": 0},
		fields=["name", "output_item", "production_recipe"],
	)

	for order in orders:
		item = order.output_item
		if item not in PRODUCTION_OUTPUT:
			continue

		jan_qty, feb_qty = PRODUCTION_OUTPUT[item]
		qty = jan_qty if month_idx == 0 else feb_qty
		if qty <= 0:
			continue

		doc = frappe.get_doc("Process Order", order.name)
		posting_date = "2020-01-31" if month_idx == 0 else "2020-02-29"

		# Add output entry
		doc.append("output_entries", {
			"item_code": item,
			"qty": qty,
			"posting_date": posting_date,
			"movement_type": "Production",
		})

		# Add input entries from recipe
		recipe = frappe.get_doc("Production Recipe", order.production_recipe)
		for inp in recipe.input_items:
			inp_qty = qty * inp.qty_per_unit
			doc.append("input_entries", {
				"item_code": inp.item_code,
				"qty": inp_qty,
				"posting_date": posting_date,
				"movement_type": "Consumption",
			})

		doc.save(ignore_permissions=True)
		doc.submit()

	frappe.db.commit()
	month_name = "January" if month_idx == 0 else "February"
	submitted = frappe.db.count("Process Order", {"costing_period": costing_period, "docstatus": 1})
	print(f"  {month_name} Process Orders: {submitted} submitted")


def create_power_production(costing_period, month_idx):
	"""Create Power Production Record with KWH data."""
	kwh_data = JAN_KWH if month_idx == 0 else FEB_KWH
	kwh_generated = JAN_KWH_GENERATED if month_idx == 0 else FEB_KWH_GENERATED

	ppr_name = f"PWR-{costing_period}"
	if frappe.db.exists("Power Production Record", ppr_name):
		print(f"  {ppr_name} already exists")
		return

	doc = frappe.get_doc({
		"doctype": "Power Production Record",
		"costing_period": costing_period,
		"total_kwh_generated": kwh_generated,
		"dewa_kwh_purchased": 0,
		"general_service_cc": cc("R10100A10S"),
		"kwh_consumption_table": [
			{"cost_center": cc(sap_code), "kwh_consumed": kwh}
			for sap_code, kwh in kwh_data.items()
			if kwh > 0
		],
		"remarks": f"SAP KWH Transactions ({costing_period})",
	})
	doc.insert(ignore_permissions=True)
	doc.submit()
	frappe.db.set_value("Costing Period", costing_period, "power_status", "KWH Posted")
	frappe.db.commit()
	month_name = "January" if month_idx == 0 else "February"
	print(f"  {month_name} Power Production: {kwh_generated:,.0f} KWH generated")


def create_costing_period(month_idx):
	"""Create and submit a costing period."""
	if month_idx == 0:
		name = "January 2020"
		start = "2020-01-01"
		end = "2020-01-31"
	else:
		name = "February 2020"
		start = "2020-02-01"
		end = "2020-02-29"

	existing = frappe.db.get_value("Costing Period",
		{"company": COMPANY, "period_start": start}, "name")
	if existing:
		print(f"  Costing Period {existing} already exists")
		return existing

	cp = frappe.get_doc({
		"doctype": "Costing Period",
		"period_name": name,
		"company": COMPANY,
		"fiscal_year": "2020",
		"period_start": start,
		"period_end": end,
	})
	cp.insert(ignore_permissions=True)
	cp.submit()
	frappe.db.commit()
	print(f"  Costing Period created: {cp.name}")
	return cp.name


# ══════════════════════════════════════════════════════════════════════════════
# CLEANUP
# ══════════════════════════════════════════════════════════════════════════════

def cleanup_all():
	"""Delete all transactional data in reverse dependency order."""
	print("\n═══ Cleanup ═══")
	frappe.flags.in_import = True

	# 1. Allocation Runs
	for dt in ["Allocation Run Cycle", "Allocation Run"]:
		deleted = frappe.db.sql(f"DELETE FROM `tab{dt}`")
	print("  Cleared: Allocation Runs")

	# 2. CO Documents
	for dt in ["CO Document Line", "CO Document"]:
		frappe.db.sql(f"DELETE FROM `tab{dt}`")
	print("  Cleared: CO Documents")

	# 3. SKF Entries
	frappe.db.sql("DELETE FROM `tabSKF Entry`")
	print("  Cleared: SKF Entries")

	# 4. Power Production Records
	for dt in ["Power Production CC Detail", "Power Production Record"]:
		frappe.db.sql(f"DELETE FROM `tab{dt}`")
	print("  Cleared: Power Production Records")

	# 5. Process Orders
	for dt in ["Process Order Input", "Process Order Output", "Process Order Chain Link", "Process Order"]:
		frappe.db.sql(f"DELETE FROM `tab{dt}`")
	print("  Cleared: Process Orders")

	# 6. PLCV and Standard Cost Revaluation
	frappe.db.sql("DELETE FROM `tabPLCV Entry`")
	for dt in ["Standard Cost Revaluation"]:
		for name in frappe.get_all(dt, pluck="name"):
			try:
				doc = frappe.get_doc(dt, name)
				if doc.docstatus == 1:
					doc.cancel()
				doc.delete()
			except Exception:
				frappe.db.sql(f"DELETE FROM `tab{dt}` WHERE name=%s", name)
	print("  Cleared: PLCV + Standard Cost Revaluation")

	# 7. Stock Entries and related GL/SLE
	for name in frappe.get_all("Stock Entry", pluck="name", order_by="creation desc"):
		try:
			doc = frappe.get_doc("Stock Entry", name)
			if doc.docstatus == 1:
				doc.cancel()
			doc.delete()
		except Exception:
			pass
	print("  Cleared: Stock Entries")

	# 8. Purchase Receipts
	for name in frappe.get_all("Purchase Receipt", filters={"company": COMPANY}, pluck="name", order_by="creation desc"):
		try:
			doc = frappe.get_doc("Purchase Receipt", name)
			if doc.docstatus == 1:
				doc.cancel()
			doc.delete()
		except Exception:
			pass
	print("  Cleared: Purchase Receipts")

	# 9. Stock Reconciliations
	for name in frappe.get_all("Stock Reconciliation", filters={"company": COMPANY}, pluck="name", order_by="creation desc"):
		try:
			doc = frappe.get_doc("Stock Reconciliation", name)
			if doc.docstatus == 1:
				doc.cancel()
			doc.delete()
		except Exception:
			pass
	print("  Cleared: Stock Reconciliations")

	# 10. Journal Entries (demo overhead/maintenance)
	for name in frappe.get_all("Journal Entry",
		filters={"company": COMPANY, "posting_date": (">=", "2019-12-01")},
		pluck="name", order_by="creation desc"):
		try:
			doc = frappe.get_doc("Journal Entry", name)
			if doc.docstatus == 1:
				doc.cancel()
			doc.delete()
		except Exception:
			pass
	print("  Cleared: Journal Entries")

	# 11. Production Recipes
	for name in frappe.get_all("Production Recipe", pluck="name"):
		frappe.delete_doc("Production Recipe", name, force=True)
	print("  Cleared: Production Recipes")

	# 11b. Standard Cost Rates
	for name in frappe.get_all("Standard Cost Rate", pluck="name"):
		try:
			doc = frappe.get_doc("Standard Cost Rate", name)
			if doc.docstatus == 1:
				doc.cancel()
			doc.delete()
		except Exception:
			pass
	print("  Cleared: Standard Cost Rates")

	# 12. Costing Periods
	for name in frappe.get_all("Costing Period", filters={"company": COMPANY}, pluck="name"):
		try:
			doc = frappe.get_doc("Costing Period", name)
			if doc.docstatus == 1:
				frappe.db.set_value("Costing Period", name, "docstatus", 2)
			doc.reload()
			doc.delete()
		except Exception:
			frappe.db.sql("DELETE FROM `tabCosting Period` WHERE name=%s", name)
	print("  Cleared: Costing Periods")

	# 13. Reset Bins
	frappe.db.sql("UPDATE `tabBin` SET actual_qty=0, stock_value=0, valuation_rate=0")

	# 14. Clear remaining GL entries
	frappe.db.sql("DELETE FROM `tabGL Entry` WHERE company=%s AND posting_date >= '2019-12-01'", COMPANY)
	frappe.db.sql("DELETE FROM `tabStock Ledger Entry` WHERE company=%s", COMPANY)

	frappe.flags.in_import = False
	frappe.db.commit()
	print("  Cleanup complete.")


# ══════════════════════════════════════════════════════════════════════════════
# HELPER
# ══════════════════════════════════════════════════════════════════════════════

def _get_or_create_supplier():
	name = "SAP Test Supplier"
	if not frappe.db.exists("Supplier", name):
		sg = frappe.db.get_value("Supplier Group", {}, "name")
		frappe.get_doc({
			"doctype": "Supplier",
			"supplier_name": name,
			"supplier_group": sg,
		}).insert(ignore_permissions=True)
		frappe.db.commit()
	return name


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINTS
# ══════════════════════════════════════════════════════════════════════════════

def setup_master_data():
	"""Step 1: Create all master data (items, recipes, standard cost rates)."""
	print("\n═══ Master Data Setup ═══")
	create_items()
	create_phases()
	create_recipes()
	create_standard_cost_rates()
	create_opening_stock()


def setup_jan():
	"""Step 2: January 2020 transactions."""
	print("\n═══ January 2020 ═══")
	create_purchase_receipts(0)
	create_overhead_jes(0)
	cp = create_costing_period(0)
	create_power_production(cp, 0)
	create_process_orders(cp, 0)
	return cp


def setup_feb():
	"""Step 3: February 2020 transactions."""
	print("\n═══ February 2020 ═══")
	create_purchase_receipts(1)
	create_overhead_jes(1)
	cp = create_costing_period(1)
	create_power_production(cp, 1)
	create_process_orders(cp, 1)
	return cp


def run_costing_cycle(costing_period):
	"""Step 4: Run the full costing cycle for a period."""
	print(f"\n═══ Costing Cycle: {costing_period} ═══")

	# Primary Mirror: GL → CO Documents
	from std_manufacturing.api.co_balance import run_primary_co_mirror, run_fuel_revaluation
	run_primary_co_mirror(costing_period)
	co_count = frappe.db.count("CO Document", {"period": costing_period, "co_document_type": "Primary Mirror"})
	print(f"  Primary Mirror: {co_count} CO Documents")

	# Fuel Revaluation: HFO/LFO consumed in power → revalue to YTD CPU
	run_fuel_revaluation(costing_period)
	reval_count = frappe.db.count("CO Document", {
		"period": costing_period,
		"remarks": ("like", "%Fuel Cost%"),
	})
	print(f"  Fuel Revaluation: {reval_count} CO Documents")

	# Allocation Cycles: redistribute costs between CCs
	from std_manufacturing.api.allocation_engine import execute_allocation_run
	execute_allocation_run(costing_period)
	alloc_count = frappe.db.count("CO Document", {
		"period": costing_period,
		"co_document_type": ("in", ["Assessment", "Distribution"]),
	})
	print(f"  Allocation: {alloc_count} allocation CO Documents")

	# Update statuses after mirror + revaluation + allocation
	frappe.db.set_value("Costing Period", costing_period, {
		"primary_mirror_status": "Completed",
		"revaluation_status": "Submitted",
		"allocation_status": "Completed",
		"current_step": 4,
	})

	# Calculate unit costs in production chain order
	from std_manufacturing.api.process_order import calculate_all_unit_costs
	results = calculate_all_unit_costs(costing_period)
	print(f"  Unit Costs: {len(results)} items calculated")

	# Update remaining statuses
	frappe.db.set_value("Costing Period", costing_period, {
		"process_order_status": "Closed",
		"production_cost_status": "Calculated",
		"purchased_cpu_status": "Calculated",
		"produced_cpu_status": "Calculated",
		"plcv_status": "Completed",
		"status": "Completed",
		"current_step": 6,
	})
	frappe.db.commit()


def setup_all():
	"""Full setup: cleanup → master data → Jan → Feb → costing cycles."""
	frappe.set_user("Administrator")

	cleanup_all()
	setup_master_data()

	jan_cp = setup_jan()
	run_costing_cycle(jan_cp)

	feb_cp = setup_feb()
	run_costing_cycle(feb_cp)

	print("\n═══ Setup Complete ═══")
	print("Run verify_cpus() to compare CPUs against SAP targets.")


# ══════════════════════════════════════════════════════════════════════════════
# VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════

EXPECTED_CPU_JAN = {
	"120402": 984.60,
	"120036": 930.10,
	"120006": 1149.16,
	"120417": 978.03,
	"120412": 1219.32,
	"120413": 1743.02,
	"120119": 74537.79,
	"120124": 81149.64,
	"120083": 3024.14,
	"120097": 18256.44,
	"100929": 19570.23,
	"2000101": 20662.04,
	"2000100": 24009.95,
	"2000004": 22704.99,
}


def verify_cpus():
	"""Compare calculated CPUs against SAP targets."""
	print("\n═══ CPU Verification ═══")
	print(f"{'Item':<12} {'SAP CPU':>14} {'Our CPU':>14} {'Diff':>10} {'Status':<6}")
	print("─" * 60)

	jan_period = frappe.db.get_value("Costing Period",
		{"company": COMPANY, "period_start": "2020-01-01"}, "name")

	from std_manufacturing.api.process_order import get_item_ytd_cpu

	period_doc = frappe.get_doc("Costing Period", jan_period) if jan_period else None

	for item_code, expected in EXPECTED_CPU_JAN.items():
		# Get YTD unit cost from Process Order, or fall back to purchased item CPU
		actual = frappe.db.get_value(
			"Process Order",
			{"output_item": item_code, "costing_period": jan_period, "docstatus": 1},
			"ytd_unit_cost",
		) or 0
		actual = flt(actual)
		if not actual and period_doc:
			actual = flt(get_item_ytd_cpu(item_code, period_doc))
		diff = actual - expected
		status = "OK" if abs(diff) < 0.02 else "FAIL"
		print(f"{item_code:<12} {expected:>14,.2f} {actual:>14,.2f} {diff:>10,.2f} {status:<6}")
