"""
End-to-end demo data setup for the Standard Cost Module.
Based on source data from /home/frappe/frappe-bench/source_references/Costing Cycle.xlsx

Run via: bench --site badia.localhost execute std_manufacturing.demo_setup.setup_all
"""

import frappe
from frappe.utils import flt


# ── 1. Items ──────────────────────────────────────────────────────────────────
# Existing items: RM-120002, RM-120070, RM-120119, RM-120238, RM-120402,
#                 RM-2000011, RM-2000012, PK-3100061, PK-3100070, OPC Cement 42.5R

NEW_ITEMS = [
	# Quarry raw materials
	{"item_code": "RM-120417", "item_name": "Basalt/blasted", "item_group": "Raw Material", "stock_uom": "Tonne", "cost_category": "Purchased"},
	{"item_code": "RM-2000009", "item_name": "Fues Explosive material", "item_group": "Raw Material", "stock_uom": "Kg", "cost_category": "Purchased"},
	{"item_code": "RM-2000075", "item_name": "Local Dynamite", "item_group": "Raw Material", "stock_uom": "Kg", "cost_category": "Purchased"},
	{"item_code": "RM-2000141", "item_name": "Electrical Wire 0.5 M.M", "item_group": "Raw Material", "stock_uom": "Meter", "cost_category": "Purchased"},
	{"item_code": "RM-2000142", "item_name": "Electrical Wire 0.9 M.M", "item_group": "Raw Material", "stock_uom": "Meter", "cost_category": "Purchased"},
	{"item_code": "RM-2000150", "item_name": "M.M.D.T Fitted Explosive material", "item_group": "Raw Material", "stock_uom": "Kg", "cost_category": "Purchased"},
	{"item_code": "RM-2000010", "item_name": "CO2 Gas", "item_group": "Raw Material", "stock_uom": "Tonne", "cost_category": "Purchased"},
	{"item_code": "RM-2000040", "item_name": "Gasoline", "item_group": "Raw Material", "stock_uom": "Litre", "cost_category": "Purchased"},
	# Packaging
	{"item_code": "PK-3100080", "item_name": "Bags CEM II 42.5N Gray PP", "item_group": "Raw Material", "stock_uom": "Nos", "cost_category": "Purchased"},
	{"item_code": "PK-3100090", "item_name": "Bags CEM II 32.5N Blue PP", "item_group": "Raw Material", "stock_uom": "Nos", "cost_category": "Purchased"},
	# Semi-finished goods
	{"item_code": "SF-120036", "item_name": "Limestone/mined", "item_group": "Sub Assemblies", "stock_uom": "Tonne", "cost_category": "Semi-Finished"},
	{"item_code": "SF-120006", "item_name": "Limestone/crushed", "item_group": "Sub Assemblies", "stock_uom": "Tonne", "cost_category": "Semi-Finished"},
	{"item_code": "SF-120412", "item_name": "Basalt/mined", "item_group": "Sub Assemblies", "stock_uom": "Tonne", "cost_category": "Semi-Finished"},
	{"item_code": "SF-120413", "item_name": "Basalt/crushed", "item_group": "Sub Assemblies", "stock_uom": "Tonne", "cost_category": "Semi-Finished"},
	{"item_code": "SF-120124", "item_name": "Solid fuels blend/ground", "item_group": "Sub Assemblies", "stock_uom": "Tonne", "cost_category": "Semi-Finished"},
	{"item_code": "SF-120083", "item_name": "Raw meal/grey/common", "item_group": "Sub Assemblies", "stock_uom": "Tonne", "cost_category": "Semi-Finished"},
	{"item_code": "SF-120097", "item_name": "Clinker/grey/common", "item_group": "Sub Assemblies", "stock_uom": "Tonne", "cost_category": "Semi-Finished"},
	# Finished goods - bulk
	{"item_code": "FG-2000101", "item_name": "CEM II 42.5 N / Bulk", "item_group": "Finished Goods", "stock_uom": "Tonne", "cost_category": "Finished"},
	{"item_code": "FG-100929", "item_name": "CEM II Pouzzolana 32.5 N/silos", "item_group": "Finished Goods", "stock_uom": "Tonne", "cost_category": "Finished"},
	# Finished goods - bagged
	{"item_code": "FG-2000100", "item_name": "CEM II 42.5 N/Bags", "item_group": "Finished Goods", "stock_uom": "Tonne", "cost_category": "Finished"},
	{"item_code": "FG-2000004", "item_name": "CEM II Pouzzolana 32.5 N/Bags", "item_group": "Finished Goods", "stock_uom": "Tonne", "cost_category": "Finished"},
]


def create_items():
	"""Create missing items for the production chain."""
	# Ensure item groups exist
	for group in ["Sub Assemblies", "Finished Goods"]:
		if not frappe.db.exists("Item Group", group):
			frappe.get_doc({"doctype": "Item Group", "item_group_name": group, "parent_item_group": "All Item Groups"}).insert(ignore_permissions=True)

	created = 0
	for item_data in NEW_ITEMS:
		if frappe.db.exists("Item", item_data["item_code"]):
			continue
		doc = frappe.get_doc({
			"doctype": "Item",
			"item_code": item_data["item_code"],
			"item_name": item_data["item_name"],
			"item_group": item_data["item_group"],
			"stock_uom": item_data["stock_uom"],
			"is_stock_item": 1,
			"custom_valuation_method": "Standard Cost",
			"custom_cost_category": item_data["cost_category"],
			"custom_include_in_plcv": 1,
		})
		doc.insert(ignore_permissions=True)
		created += 1

	# Update existing items with cost category if missing
	for item_code, cat in [
		("RM-120002", "Purchased"), ("RM-120070", "Purchased"), ("RM-120119", "Purchased"),
		("RM-120238", "Purchased"), ("RM-120402", "Purchased"), ("RM-2000011", "Purchased"),
		("RM-2000012", "Purchased"), ("PK-3100061", "Purchased"), ("PK-3100070", "Purchased"),
	]:
		if frappe.db.exists("Item", item_code):
			frappe.db.set_value("Item", item_code, {
				"custom_cost_category": cat,
				"custom_include_in_plcv": 1,
				"custom_valuation_method": "Standard Cost",
			})

	frappe.db.commit()
	print(f"Items: {created} created")


# ── 2. Production Phases ─────────────────────────────────────────────────────

PHASES = [
	{"phase_name": "Quarry", "sequence": 10, "description": "Blasting and mining of raw stone"},
	{"phase_name": "Crusher", "sequence": 20, "description": "Primary and secondary crushing"},
	{"phase_name": "Coal Mill", "sequence": 25, "description": "Solid fuel grinding"},
	{"phase_name": "Raw Mill", "sequence": 30, "description": "Raw meal grinding and blending"},
	{"phase_name": "Kiln", "sequence": 40, "description": "Clinker burning (pyroprocessing)"},
	{"phase_name": "Cement Mill", "sequence": 50, "description": "Cement grinding and blending"},
	{"phase_name": "Packing", "sequence": 60, "description": "Bagging and bulk loading"},
]


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


# ── 3. Production Recipes ─────────────────────────────────────────────────────

RECIPES = [
	{
		"recipe_code": "LIME-BLAST",
		"recipe_name": "Limestone Blasting",
		"production_phase": "Quarry",
		"phase_sequence": 10,
		"cost_center": "Quarry Operations - BCP",
		"output_item": "RM-120402",
		"input_items": [
			{"item_code": "RM-2000009", "qty_per_unit": 0.009, "source_warehouse": "Stores - BCP"},
			{"item_code": "RM-2000075", "qty_per_unit": 0.005, "source_warehouse": "Stores - BCP"},
			{"item_code": "RM-2000141", "qty_per_unit": 0.060, "source_warehouse": "Stores - BCP"},
			{"item_code": "RM-2000142", "qty_per_unit": 0.009, "source_warehouse": "Stores - BCP"},
			{"item_code": "RM-2000150", "qty_per_unit": 0.140, "source_warehouse": "Stores - BCP"},
		],
		"successor_recipes": ["LIME-MINE", "LIME-CRUSH"],
	},
	{
		"recipe_code": "BASALT-BLAST",
		"recipe_name": "Basalt Blasting",
		"production_phase": "Quarry",
		"phase_sequence": 11,
		"cost_center": "Quarry Operations - BCP",
		"output_item": "RM-120417",
		"input_items": [
			{"item_code": "RM-2000009", "qty_per_unit": 0.004, "source_warehouse": "Stores - BCP"},
			{"item_code": "RM-2000075", "qty_per_unit": 0.003, "source_warehouse": "Stores - BCP"},
			{"item_code": "RM-2000141", "qty_per_unit": 0.045, "source_warehouse": "Stores - BCP"},
			{"item_code": "RM-2000142", "qty_per_unit": 0.023, "source_warehouse": "Stores - BCP"},
			{"item_code": "RM-2000150", "qty_per_unit": 0.200, "source_warehouse": "Stores - BCP"},
		],
		"successor_recipes": ["BASALT-MINE", "BASALT-CRUSH"],
	},
	{
		"recipe_code": "LIME-MINE",
		"recipe_name": "Limestone Mining",
		"production_phase": "Quarry",
		"phase_sequence": 12,
		"cost_center": "Quarry Operations - BCP",
		"output_item": "SF-120036",
		"input_items": [
			{"item_code": "RM-120402", "qty_per_unit": 0.446, "source_warehouse": "Stores - BCP"},
		],
		"predecessor_recipes": ["LIME-BLAST"],
		"successor_recipes": ["LIME-CRUSH"],
	},
	{
		"recipe_code": "BASALT-MINE",
		"recipe_name": "Basalt Mining",
		"production_phase": "Quarry",
		"phase_sequence": 13,
		"cost_center": "Quarry Operations - BCP",
		"output_item": "SF-120412",
		"input_items": [
			{"item_code": "RM-120417", "qty_per_unit": 0.437, "source_warehouse": "Stores - BCP"},
		],
		"predecessor_recipes": ["BASALT-BLAST"],
		"successor_recipes": ["BASALT-CRUSH"],
	},
	{
		"recipe_code": "LIME-CRUSH",
		"recipe_name": "Limestone Crushing",
		"production_phase": "Crusher",
		"phase_sequence": 20,
		"cost_center": "Crusher - BCP",
		"output_item": "SF-120006",
		"input_items": [
			{"item_code": "RM-120402", "qty_per_unit": 0.103, "source_warehouse": "Stores - BCP"},
			{"item_code": "SF-120036", "qty_per_unit": 0.897, "source_warehouse": "Work In Progress - BCP"},
		],
		"predecessor_recipes": ["LIME-BLAST", "LIME-MINE"],
		"successor_recipes": ["RAW-MEAL"],
	},
	{
		"recipe_code": "BASALT-CRUSH",
		"recipe_name": "Basalt Crushing",
		"production_phase": "Crusher",
		"phase_sequence": 21,
		"cost_center": "Crusher - BCP",
		"output_item": "SF-120413",
		"input_items": [
			{"item_code": "RM-120417", "qty_per_unit": 0.300, "source_warehouse": "Stores - BCP"},
			{"item_code": "SF-120412", "qty_per_unit": 0.700, "source_warehouse": "Work In Progress - BCP"},
		],
		"predecessor_recipes": ["BASALT-BLAST", "BASALT-MINE"],
		"successor_recipes": ["RAW-MEAL"],
	},
	{
		"recipe_code": "COAL-GRIND",
		"recipe_name": "Solid Fuel Grinding",
		"production_phase": "Coal Mill",
		"phase_sequence": 25,
		"cost_center": "Coal Mill - BCP",
		"output_item": "SF-120124",
		"input_items": [
			{"item_code": "RM-120119", "qty_per_unit": 1.026, "source_warehouse": "Stores - BCP"},
		],
		"successor_recipes": ["CLINKER"],
	},
	{
		"recipe_code": "RAW-MEAL",
		"recipe_name": "Raw Meal Production",
		"production_phase": "Raw Mill",
		"phase_sequence": 30,
		"cost_center": "Raw Mill - BCP",
		"output_item": "SF-120083",
		"input_items": [
			{"item_code": "SF-120006", "qty_per_unit": 0.819, "source_warehouse": "Work In Progress - BCP"},
			{"item_code": "SF-120413", "qty_per_unit": 0.110, "source_warehouse": "Work In Progress - BCP"},
			{"item_code": "RM-120070", "qty_per_unit": 0.007, "source_warehouse": "Stores - BCP"},
			{"item_code": "RM-120238", "qty_per_unit": 0.030, "source_warehouse": "Stores - BCP"},
		],
		"predecessor_recipes": ["LIME-CRUSH", "BASALT-CRUSH"],
		"successor_recipes": ["CLINKER"],
	},
	{
		"recipe_code": "CLINKER",
		"recipe_name": "Clinker Production",
		"production_phase": "Kiln",
		"phase_sequence": 40,
		"cost_center": "Kiln - BCP",
		"output_item": "SF-120097",
		"input_items": [
			{"item_code": "SF-120083", "qty_per_unit": 1.585, "source_warehouse": "Work In Progress - BCP"},
			{"item_code": "SF-120124", "qty_per_unit": 0.119, "source_warehouse": "Work In Progress - BCP"},
			{"item_code": "RM-2000010", "qty_per_unit": 0.000008, "source_warehouse": "Stores - BCP", "is_optional": 1},
		],
		"predecessor_recipes": ["RAW-MEAL", "COAL-GRIND"],
		"successor_recipes": ["CEM-425", "CEM-325"],
	},
	{
		"recipe_code": "CEM-425",
		"recipe_name": "CEM II 42.5N Grinding",
		"production_phase": "Cement Mill",
		"phase_sequence": 50,
		"cost_center": "Cement Mill - BCP",
		"output_item": "FG-2000101",
		"input_items": [
			{"item_code": "SF-120097", "qty_per_unit": 0.817, "source_warehouse": "Work In Progress - BCP"},
			{"item_code": "RM-120002", "qty_per_unit": 0.157, "source_warehouse": "Stores - BCP"},
			{"item_code": "RM-120070", "qty_per_unit": 0.046, "source_warehouse": "Stores - BCP"},
			{"item_code": "RM-2000011", "qty_per_unit": 0.403, "source_warehouse": "Stores - BCP"},
			{"item_code": "RM-2000012", "qty_per_unit": 0.001, "source_warehouse": "Stores - BCP"},
		],
		"predecessor_recipes": ["CLINKER"],
		"successor_recipes": ["PACK-425"],
	},
	{
		"recipe_code": "CEM-325",
		"recipe_name": "CEM II 32.5N Grinding",
		"production_phase": "Cement Mill",
		"phase_sequence": 51,
		"cost_center": "Cement Mill - BCP",
		"output_item": "FG-100929",
		"input_items": [
			{"item_code": "SF-120097", "qty_per_unit": 0.698, "source_warehouse": "Work In Progress - BCP"},
			{"item_code": "RM-120002", "qty_per_unit": 0.289, "source_warehouse": "Stores - BCP"},
			{"item_code": "RM-120070", "qty_per_unit": 0.046, "source_warehouse": "Stores - BCP"},
			{"item_code": "RM-2000011", "qty_per_unit": 0.635, "source_warehouse": "Stores - BCP"},
			{"item_code": "RM-2000012", "qty_per_unit": 0.001, "source_warehouse": "Stores - BCP"},
		],
		"predecessor_recipes": ["CLINKER"],
		"successor_recipes": ["PACK-325"],
	},
	{
		"recipe_code": "PACK-425",
		"recipe_name": "CEM II 42.5N Bagging",
		"production_phase": "Packing",
		"phase_sequence": 60,
		"cost_center": "Packing - BCP",
		"output_item": "FG-2000100",
		"input_items": [
			{"item_code": "FG-2000101", "qty_per_unit": 1.000, "source_warehouse": "Finished Goods - BCP"},
			{"item_code": "PK-3100070", "qty_per_unit": 19.94, "source_warehouse": "Stores - BCP"},
			{"item_code": "PK-3100080", "qty_per_unit": 11.24, "source_warehouse": "Stores - BCP"},
		],
		"predecessor_recipes": ["CEM-425"],
	},
	{
		"recipe_code": "PACK-325",
		"recipe_name": "CEM II 32.5N Bagging",
		"production_phase": "Packing",
		"phase_sequence": 61,
		"cost_center": "Packing - BCP",
		"output_item": "FG-2000004",
		"input_items": [
			{"item_code": "FG-100929", "qty_per_unit": 1.002, "source_warehouse": "Finished Goods - BCP"},
			{"item_code": "PK-3100061", "qty_per_unit": 13.42, "source_warehouse": "Stores - BCP"},
			{"item_code": "PK-3100090", "qty_per_unit": 5.91, "source_warehouse": "Stores - BCP"},
		],
		"predecessor_recipes": ["CEM-325"],
	},
]


def create_recipes():
	"""Create production recipes with inputs and chain links."""
	created = 0
	for r in RECIPES:
		recipe_name = f"RECIPE-{r['recipe_code']}"
		if frappe.db.exists("Production Recipe", recipe_name):
			continue

		# Fetch output UOM
		output_uom = frappe.db.get_value("Item", r["output_item"], "stock_uom") or "Tonne"

		doc = frappe.get_doc({
			"doctype": "Production Recipe",
			"recipe_code": r["recipe_code"],
			"recipe_name": r["recipe_name"],
			"company": "Badia Cement PSJ",
			"production_phase": r["production_phase"],
			"phase_sequence": r["phase_sequence"],
			"cost_center": r["cost_center"],
			"output_item": r["output_item"],
			"output_uom": output_uom,
			"is_active": 1,
			"input_items": [
				{
					"item_code": inp["item_code"],
					"qty_per_unit": inp["qty_per_unit"],
					"source_warehouse": inp.get("source_warehouse", "Stores - BCP"),
					"is_optional": inp.get("is_optional", 0),
				}
				for inp in r["input_items"]
			],
		})
		doc.insert(ignore_permissions=True)
		created += 1

	# Second pass: add predecessor/successor links
	for r in RECIPES:
		recipe_name = f"RECIPE-{r['recipe_code']}"
		doc = frappe.get_doc("Production Recipe", recipe_name)
		changed = False

		for pred_code in r.get("predecessor_recipes", []):
			pred_name = f"RECIPE-{pred_code}"
			if not any(row.recipe == pred_name for row in doc.predecessor_recipes):
				pred_doc = frappe.get_doc("Production Recipe", pred_name)
				link_item = pred_doc.output_item
				doc.append("predecessor_recipes", {
					"recipe": pred_name,
					"recipe_name": pred_doc.recipe_name,
					"link_item": link_item,
				})
				changed = True

		for succ_code in r.get("successor_recipes", []):
			succ_name = f"RECIPE-{succ_code}"
			if frappe.db.exists("Production Recipe", succ_name):
				if not any(row.recipe == succ_name for row in doc.successor_recipes):
					succ_doc = frappe.get_doc("Production Recipe", succ_name)
					doc.append("successor_recipes", {
						"recipe": succ_name,
						"recipe_name": succ_doc.recipe_name,
						"link_item": doc.output_item,
					})
					changed = True

		if changed:
			doc.save(ignore_permissions=True)

	# Link items to their default production recipe
	for r in RECIPES:
		recipe_name = f"RECIPE-{r['recipe_code']}"
		frappe.db.set_value("Item", r["output_item"], "custom_production_recipe", recipe_name)

	frappe.db.commit()
	print(f"Production Recipes: {created} created, links updated")


# ── 4. Process Orders for Jan 2020 ───────────────────────────────────────────
# SAP Order → Recipe mapping for Jan 2020 (orders 1001998-1002011)
# Data aggregated from Process Orders Transactions sheet

JAN_PROCESS_ORDERS = [
	{
		"recipe_code": "LIME-BLAST",
		"outputs": [{"item_code": "RM-120402", "qty": 6220.54, "movement_type": "Production"}],
		"inputs": [],  # Quarry blasting has no material inputs in Jan data
	},
	{
		"recipe_code": "BASALT-BLAST",
		"outputs": [{"item_code": "RM-120417", "qty": 3711.86, "movement_type": "Production"}],
		"inputs": [],
	},
	{
		"recipe_code": "LIME-MINE",
		"outputs": [{"item_code": "SF-120036", "qty": 390.32, "movement_type": "Production"}],
		"inputs": [{"item_code": "RM-120402", "qty": 390.32, "movement_type": "Consumption"}],
	},
	{
		"recipe_code": "LIME-CRUSH",
		"outputs": [{"item_code": "SF-120006", "qty": 222541.60, "movement_type": "Production"}],
		"inputs": [
			{"item_code": "SF-120036", "qty": 199568.94, "movement_type": "Consumption"},
			{"item_code": "RM-120402", "qty": 22972.66, "movement_type": "Consumption"},
		],
	},
	{
		"recipe_code": "BASALT-CRUSH",
		"outputs": [{"item_code": "SF-120413", "qty": 42848.26, "movement_type": "Production"}],
		"inputs": [
			{"item_code": "RM-120417", "qty": 3711.86, "movement_type": "Consumption"},
			{"item_code": "SF-120412", "qty": 39136.40, "movement_type": "Consumption"},
		],
	},
	{
		"recipe_code": "COAL-GRIND",
		"outputs": [{"item_code": "SF-120124", "qty": 38876.11, "movement_type": "Production"}],
		"inputs": [
			{"item_code": "RM-120119", "qty": 39896.99, "movement_type": "Consumption"},
		],
	},
	{
		"recipe_code": "RAW-MEAL",
		"outputs": [{"item_code": "SF-120083", "qty": 479472.59, "movement_type": "Production"}],
		"inputs": [
			{"item_code": "SF-120006", "qty": 391403.51, "movement_type": "Consumption"},
			{"item_code": "SF-120413", "qty": 83556.06, "movement_type": "Consumption"},
			{"item_code": "RM-120070", "qty": 3444.37, "movement_type": "Consumption"},
			{"item_code": "RM-120238", "qty": 14335.20, "movement_type": "Consumption"},
		],
	},
	{
		"recipe_code": "CLINKER",
		"outputs": [{"item_code": "SF-120097", "qty": 300140.62, "movement_type": "Production"}],
		"inputs": [
			{"item_code": "SF-120083", "qty": 477223.61, "movement_type": "Consumption"},
			{"item_code": "SF-120124", "qty": 36024.07, "movement_type": "Consumption"},
			{"item_code": "RM-2000010", "qty": 2.41, "movement_type": "Consumption"},
		],
	},
	{
		"recipe_code": "CEM-425",
		"outputs": [{"item_code": "FG-2000101", "qty": 70507.97, "movement_type": "Production"}],
		"inputs": [
			{"item_code": "SF-120097", "qty": 57603.90, "movement_type": "Consumption"},
			{"item_code": "RM-120002", "qty": 11099.65, "movement_type": "Consumption"},
			{"item_code": "RM-120070", "qty": 3269.97, "movement_type": "Consumption"},
			{"item_code": "RM-2000011", "qty": 28453.00, "movement_type": "Consumption"},
			{"item_code": "RM-2000012", "qty": 83.08, "movement_type": "Consumption"},
		],
	},
	{
		"recipe_code": "CEM-325",
		"outputs": [{"item_code": "FG-100929", "qty": 36353.54, "movement_type": "Production"}],
		"inputs": [
			{"item_code": "SF-120097", "qty": 25386.04, "movement_type": "Consumption"},
			{"item_code": "RM-120002", "qty": 10526.58, "movement_type": "Consumption"},
			{"item_code": "RM-120070", "qty": 1677.92, "movement_type": "Consumption"},
			{"item_code": "RM-2000011", "qty": 23104.00, "movement_type": "Consumption"},
			{"item_code": "RM-2000012", "qty": 53.62, "movement_type": "Consumption"},
		],
	},
	{
		"recipe_code": "PACK-425",
		"outputs": [{"item_code": "FG-2000100", "qty": 65926.00, "movement_type": "Production"}],
		"inputs": [
			{"item_code": "FG-2000101", "qty": 65926.00, "movement_type": "Consumption"},
			{"item_code": "PK-3100070", "qty": 576103.00, "movement_type": "Consumption"},
			{"item_code": "PK-3100080", "qty": 740983.00, "movement_type": "Consumption"},
		],
	},
	{
		"recipe_code": "PACK-325",
		"outputs": [{"item_code": "FG-2000004", "qty": 36428.00, "movement_type": "Production"}],
		"inputs": [
			{"item_code": "FG-100929", "qty": 36428.00, "movement_type": "Consumption"},
			{"item_code": "PK-3100061", "qty": 488790.00, "movement_type": "Consumption"},
			{"item_code": "PK-3100090", "qty": 215347.00, "movement_type": "Consumption"},
		],
	},
]


def create_process_orders():
	"""Create and populate Process Orders for Jan 2020 costing period."""
	costing_period = "CP-BCP-2020-01-01"

	if not frappe.db.exists("Costing Period", costing_period):
		print(f"ERROR: Costing Period {costing_period} does not exist")
		return

	created = 0
	for po_data in JAN_PROCESS_ORDERS:
		recipe_name = f"RECIPE-{po_data['recipe_code']}"
		po_name = f"PO-{po_data['recipe_code']}-{costing_period}"

		if frappe.db.exists("Process Order", po_name):
			print(f"  Skipping {po_name} (already exists)")
			continue

		recipe_doc = frappe.get_doc("Production Recipe", recipe_name)

		doc = frappe.get_doc({
			"doctype": "Process Order",
			"costing_period": costing_period,
			"production_recipe": recipe_name,
			"cost_center": recipe_doc.cost_center,
			"output_entries": [
				{
					"item_code": out["item_code"],
					"qty": out["qty"],
					"posting_date": "2020-01-31",
					"movement_type": out["movement_type"],
					"target_warehouse": "Work In Progress - BCP" if out["item_code"].startswith("SF-") else "Finished Goods - BCP" if out["item_code"].startswith("FG-") else "Stores - BCP",
				}
				for out in po_data["outputs"]
			],
			"input_entries": [
				{
					"item_code": inp["item_code"],
					"qty": inp["qty"],
					"posting_date": "2020-01-31",
					"movement_type": inp["movement_type"],
					"source_warehouse": "Work In Progress - BCP" if inp["item_code"].startswith("SF-") or inp["item_code"].startswith("FG-") else "Stores - BCP",
				}
				for inp in po_data["inputs"]
			],
			"remarks": f"Demo data from SAP Process Orders Transactions (Jan 2020)",
		})
		doc.insert(ignore_permissions=True)
		created += 1
		print(f"  Created {po_name}: output={po_data['outputs'][0]['qty']:.2f} {po_data['outputs'][0]['item_code']}")

	frappe.db.commit()
	print(f"Process Orders: {created} created for {costing_period}")


def submit_process_orders():
	"""Submit all draft Process Orders for Jan 2020."""
	costing_period = "CP-BCP-2020-01-01"
	draft_pos = frappe.get_all(
		"Process Order",
		filters={"costing_period": costing_period, "docstatus": 0},
		pluck="name",
	)

	submitted = 0
	for po_name in draft_pos:
		try:
			doc = frappe.get_doc("Process Order", po_name)
			doc.submit()
			submitted += 1
			print(f"  Submitted {po_name}")
		except Exception as e:
			print(f"  ERROR submitting {po_name}: {e}")

	frappe.db.commit()
	# Update costing period status
	frappe.db.set_value("Costing Period", costing_period, "process_order_status", "Created")
	frappe.db.commit()
	print(f"Process Orders: {submitted} submitted")


def run_production_costing():
	"""Calculate unit costs for all submitted Process Orders."""
	from std_manufacturing.api.process_order import calculate_unit_costs

	costing_period = "CP-BCP-2020-01-01"
	pos = frappe.get_all(
		"Process Order",
		filters={"costing_period": costing_period, "docstatus": 1, "status": "Open"},
		pluck="name",
	)

	calculated = 0
	for po_name in pos:
		try:
			calculate_unit_costs(po_name)
			calculated += 1
			doc = frappe.get_doc("Process Order", po_name)
			print(f"  {po_name}: output={doc.total_output_qty:.2f}, cc_balance={doc.cc_balance:.2f}, unit_cost={doc.unit_cost:.2f}")
		except Exception as e:
			print(f"  ERROR calculating {po_name}: {e}")

	frappe.db.set_value("Costing Period", costing_period, "production_cost_status", "Calculated")
	frappe.db.commit()
	print(f"Production Costing: {calculated} Process Orders calculated")


def create_standard_cost_rates_for_produced():
	"""Create Standard Cost Rates for semi-finished and finished items."""
	# These are approximate standard rates based on the source data
	rates = [
		("RM-120417", 12.94, "Tonne"),
		("SF-120036", 500.00, "Tonne"),
		("SF-120006", 700.00, "Tonne"),
		("SF-120412", 1000.00, "Tonne"),
		("SF-120413", 1700.00, "Tonne"),
		("SF-120124", 75000.00, "Tonne"),
		("SF-120083", 1500.00, "Tonne"),
		("SF-120097", 3500.00, "Tonne"),
		("FG-2000101", 8000.00, "Tonne"),
		("FG-100929", 7000.00, "Tonne"),
		("FG-2000100", 12000.00, "Tonne"),
		("FG-2000004", 10000.00, "Tonne"),
		# Explosives/consumables
		("RM-2000009", 116.54, "Kg"),
		("RM-2000075", 4340.30, "Kg"),
		("RM-2000141", 45.57, "Meter"),
		("RM-2000142", 48.31, "Meter"),
		("RM-2000150", 700.00, "Kg"),
		("RM-2000010", 1000.00, "Tonne"),
		("RM-2000040", 500.00, "Litre"),
		("PK-3100080", 164.83, "Nos"),
		("PK-3100090", 169.19, "Nos"),
	]

	created = 0
	for item_code, rate, uom in rates:
		scr_name = f"SCR-{item_code}-2020-01-01"
		if frappe.db.exists("Standard Cost Rate", scr_name):
			continue
		if not frappe.db.exists("Item", item_code):
			continue

		doc = frappe.get_doc({
			"doctype": "Standard Cost Rate",
			"item_code": item_code,
			"standard_rate": rate,
			"effective_from": "2020-01-01",
			"fiscal_year": "2020",
			"rate_basis": "Budget",
			"status": "Active",
		})
		doc.insert(ignore_permissions=True)
		doc.submit()
		created += 1

	frappe.db.commit()
	print(f"Standard Cost Rates: {created} created for produced items")


def create_co_documents_for_production_ccs():
	"""Create CO Documents for production cost centers based on SAP OH CC data (Jan 2020).

	Source: OH CC sheet + Maintenance Orders CC sheet from Costing Cycle.xlsx
	Maps SAP cost centers to ERPNext cost centers.
	"""
	costing_period = "CP-BCP-2020-01-01"

	# Combined OH CC + Maintenance Orders CC amounts for Jan 2020
	# Mapped from SAP CC codes to ERPNext CC names
	cc_amounts = {
		"Quarry Operations - BCP": 4_675_601.17 + 0,  # R101P5110A OH only (no maint)
		"Crusher - BCP": 34_015_871.41 + 772_236.46,  # R101P4100A OH + maint
		"Raw Mill - BCP": 4_843_208.91 + 119_182_069.68,  # R101P0800P OH + maint
		"Kiln - BCP": 10_364_224.23 + 2_092_052.91,  # R101P0300C OH + maint
		"Cement Mill - BCP": 4_531_007.14 + 11_760_630.94,  # R101P0400D OH + maint
		# Coal Mill and Packing already have balances from existing CO docs
		# But add the source amounts minus existing balance
		# Coal Mill existing: 1,769,671.66, source: 1,352,704.70 + 1,826,683.85 = 3,179,388.55
		# Packing existing: 26,980,328.34, source: 13,655,174.26 + 4,630,374.39 = 18,285,548.65
	}

	# Get the clearing cost center
	clearing_cc = "Main - BCP"

	# Find a primary cost element
	primary_ce = frappe.db.get_value("Cost Element", {"cost_element_type": "Primary"}, "name")
	if not primary_ce:
		print("  ERROR: No primary cost element found")
		return

	created = 0
	for cc, amount in cc_amounts.items():
		if amount <= 0:
			continue

		# Check if we already created a demo CO doc for this CC
		existing = frappe.get_all("CO Document", filters={
			"period": costing_period,
			"remarks": ["like", f"%Demo OH CC%{cc}%"],
			"docstatus": 1,
		})
		if existing:
			continue

		doc = frappe.get_doc({
			"doctype": "CO Document",
			"co_document_type": "Primary Mirror",
			"company": "Badia Cement PSJ",
			"cost_element": primary_ce,
			"period": costing_period,
			"posting_date": "2020-01-31",
			"remarks": f"Demo OH CC + Maintenance for {cc}",
			"lines": [
				{"cost_center": cc, "debit_amount": amount, "credit_amount": 0},
				{"cost_center": clearing_cc, "debit_amount": 0, "credit_amount": amount},
			],
		})
		doc.insert(ignore_permissions=True)
		doc.submit()
		created += 1
		print(f"  Created CO Doc for {cc}: {amount:,.2f}")

	frappe.db.commit()
	print(f"CO Documents: {created} created for production cost centers")


def print_summary():
	"""Print a summary of the demo data."""
	costing_period = "CP-BCP-2020-01-01"
	print("\n" + "=" * 80)
	print("DEMO DATA SUMMARY - Standard Cost Module End-to-End")
	print("=" * 80)

	print(f"\nCosting Period: {costing_period}")
	cp = frappe.get_doc("Costing Period", costing_period)
	print(f"  Status: {cp.status}")
	print(f"  Primary Mirror: {cp.primary_mirror_status}")
	print(f"  Process Orders: {cp.process_order_status}")
	print(f"  Allocation: {cp.allocation_status}")
	print(f"  Production Costing: {cp.production_cost_status}")

	print(f"\nMaster Data:")
	print(f"  Items: {frappe.db.count('Item')}")
	print(f"  Production Phases: {frappe.db.count('Production Phase')}")
	print(f"  Production Recipes: {frappe.db.count('Production Recipe')}")
	print(f"  Standard Cost Rates: {frappe.db.count('Standard Cost Rate')}")
	print(f"  Cost Elements: {frappe.db.count('Cost Element')}")
	print(f"  Allocation Cycles: {frappe.db.count('Allocation Cycle')}")
	print(f"  Statistical Key Figures: {frappe.db.count('Statistical Key Figure')}")

	print(f"\nTransactional Data:")
	print(f"  CO Documents: {frappe.db.count('CO Document')}")
	print(f"  SKF Entries: {frappe.db.count('SKF Entry')}")
	print(f"  Process Orders: {frappe.db.count('Process Order')}")
	print(f"  PLCV Entries: {frappe.db.count('PLCV Entry')}")
	print(f"  Power Production Records: {frappe.db.count('Power Production Record')}")

	# Show process order results
	pos = frappe.get_all(
		"Process Order",
		filters={"costing_period": costing_period, "docstatus": 1},
		fields=["name", "recipe_name", "total_output_qty", "cc_balance", "unit_cost", "standard_rate", "cost_variance"],
		order_by="name",
	)

	if pos:
		print(f"\nProcess Order Results (Jan 2020):")
		print(f"  {'Recipe':<30} {'Output Qty':>12} {'CC Balance':>15} {'Unit Cost':>12} {'Std Rate':>12} {'Variance':>12}")
		print(f"  {'-'*30} {'-'*12} {'-'*15} {'-'*12} {'-'*12} {'-'*12}")
		for po in pos:
			print(f"  {po.recipe_name or '':<30} {flt(po.total_output_qty):>12.2f} {flt(po.cc_balance):>15.2f} {flt(po.unit_cost):>12.2f} {flt(po.standard_rate):>12.2f} {flt(po.cost_variance):>12.2f}")

	# Production chain
	print(f"\nProduction Chain:")
	print(f"  Quarry → Crusher → Raw Mill → Kiln → Cement Mill → Packing")
	print(f"             Coal Mill ↗")

	print("\n" + "=" * 80)


# ── 5. Feb 2020 ──────────────────────────────────────────────────────────────

FEB_PROCESS_ORDERS = [
	{
		"recipe_code": "LIME-BLAST",
		"outputs": [{"item_code": "RM-120402", "qty": 225777.00, "movement_type": "Production"}],
		"inputs": [
			{"item_code": "RM-2000009", "qty": 646.00, "movement_type": "Consumption"},
			{"item_code": "RM-2000075", "qty": 318.00, "movement_type": "Consumption"},
			{"item_code": "RM-2000141", "qty": 13484.00, "movement_type": "Consumption"},
			{"item_code": "RM-2000142", "qty": 2090.00, "movement_type": "Consumption"},
			{"item_code": "RM-2000150", "qty": 31600.00, "movement_type": "Consumption"},
		],
	},
	{
		"recipe_code": "BASALT-BLAST",
		"outputs": [{"item_code": "RM-120417", "qty": 81285.40, "movement_type": "Production"}],
		"inputs": [
			{"item_code": "RM-2000009", "qty": 330.00, "movement_type": "Consumption"},
			{"item_code": "RM-2000075", "qty": 240.00, "movement_type": "Consumption"},
			{"item_code": "RM-2000141", "qty": 3815.00, "movement_type": "Consumption"},
			{"item_code": "RM-2000142", "qty": 1952.00, "movement_type": "Consumption"},
			{"item_code": "RM-2000150", "qty": 17150.00, "movement_type": "Consumption"},
		],
	},
	{
		"recipe_code": "LIME-MINE",
		"outputs": [{"item_code": "SF-120036", "qty": 169990.87, "movement_type": "Production"}],
		"inputs": [{"item_code": "RM-120402", "qty": 75859.45, "movement_type": "Consumption"}],
	},
	{
		"recipe_code": "BASALT-MINE",
		"outputs": [{"item_code": "SF-120412", "qty": 56799.82, "movement_type": "Production"}],
		"inputs": [{"item_code": "RM-120417", "qty": 24814.82, "movement_type": "Consumption"}],
	},
	{
		"recipe_code": "LIME-CRUSH",
		"outputs": [{"item_code": "SF-120006", "qty": 251577.95, "movement_type": "Production"}],
		"inputs": [
			{"item_code": "SF-120036", "qty": 94262.44, "movement_type": "Consumption"},
			{"item_code": "RM-120402", "qty": 170323.75, "movement_type": "Consumption"},
		],
	},
	{
		"recipe_code": "BASALT-CRUSH",
		"outputs": [{"item_code": "SF-120413", "qty": 52111.26, "movement_type": "Production"}],
		"inputs": [
			{"item_code": "RM-120417", "qty": 25041.36, "movement_type": "Consumption"},
			{"item_code": "SF-120412", "qty": 35255.90, "movement_type": "Consumption"},
		],
	},
	{
		"recipe_code": "COAL-GRIND",
		"outputs": [{"item_code": "SF-120124", "qty": 18826.09, "movement_type": "Production"}],
		"inputs": [{"item_code": "RM-120119", "qty": 19652.20, "movement_type": "Consumption"}],
	},
	{
		"recipe_code": "RAW-MEAL",
		"outputs": [{"item_code": "SF-120083", "qty": 283076.16, "movement_type": "Production"}],
		"inputs": [
			{"item_code": "SF-120006", "qty": 233281.00, "movement_type": "Consumption"},
			{"item_code": "SF-120413", "qty": 45398.38, "movement_type": "Consumption"},
			{"item_code": "RM-120070", "qty": 1551.24, "movement_type": "Consumption"},
			{"item_code": "RM-120238", "qty": 8881.39, "movement_type": "Consumption"},
		],
	},
	{
		"recipe_code": "CLINKER",
		"outputs": [{"item_code": "SF-120097", "qty": 172427.32, "movement_type": "Production"}],
		"inputs": [
			{"item_code": "SF-120083", "qty": 272390.09, "movement_type": "Consumption"},
			{"item_code": "SF-120124", "qty": 19998.08, "movement_type": "Consumption"},
			{"item_code": "RM-2000010", "qty": 1.45, "movement_type": "Consumption"},
		],
	},
	{
		"recipe_code": "CEM-425",
		"outputs": [{"item_code": "FG-2000101", "qty": 57001.75, "movement_type": "Production"}],
		"inputs": [
			{"item_code": "SF-120097", "qty": 46381.90, "movement_type": "Consumption"},
			{"item_code": "RM-120002", "qty": 8965.12, "movement_type": "Consumption"},
			{"item_code": "RM-120070", "qty": 2802.48, "movement_type": "Consumption"},
			{"item_code": "RM-2000011", "qty": 11104.00, "movement_type": "Consumption"},
			{"item_code": "RM-2000012", "qty": 68.98, "movement_type": "Consumption"},
		],
	},
	{
		"recipe_code": "CEM-325",
		"outputs": [{"item_code": "FG-100929", "qty": 38649.59, "movement_type": "Production"}],
		"inputs": [
			{"item_code": "SF-120097", "qty": 26896.72, "movement_type": "Consumption"},
			{"item_code": "RM-120002", "qty": 11168.79, "movement_type": "Consumption"},
			{"item_code": "RM-120070", "qty": 1887.49, "movement_type": "Consumption"},
			{"item_code": "RM-2000011", "qty": 10732.00, "movement_type": "Consumption"},
			{"item_code": "RM-2000012", "qty": 53.86, "movement_type": "Consumption"},
		],
	},
	{
		"recipe_code": "PACK-425",
		"outputs": [{"item_code": "FG-2000100", "qty": 35971.00, "movement_type": "Production"}],
		"inputs": [
			{"item_code": "FG-2000101", "qty": 35971.00, "movement_type": "Consumption"},
			{"item_code": "PK-3100070", "qty": 559908.00, "movement_type": "Consumption"},
			{"item_code": "PK-3100080", "qty": 163512.00, "movement_type": "Consumption"},
		],
	},
	{
		"recipe_code": "PACK-325",
		"outputs": [{"item_code": "FG-2000004", "qty": 32734.00, "movement_type": "Production"}],
		"inputs": [
			{"item_code": "FG-100929", "qty": 32739.00, "movement_type": "Consumption"},
			{"item_code": "PK-3100061", "qty": 530364.00, "movement_type": "Consumption"},
			{"item_code": "PK-3100090", "qty": 126214.00, "movement_type": "Consumption"},
		],
	},
]

# Feb 2020 OH CC + Maintenance Orders amounts (mapped to ERPNext CCs)
FEB_CC_AMOUNTS = {
	# Production CCs: OH CC + Maintenance Orders
	"Quarry Operations - BCP": 57_826_272.08 + 39_352_089.75,  # Blasted Lim + Lim Mined
	"Crusher - BCP": 96_423_665.89 + 24_173_183.99 + 10_015_373.91 + 13_265_543.93,  # Lim+Bas crusher OH + maint
	"Raw Mill - BCP": 4_530_743.81 + 29_347_284.70,  # Raw Mill OH + maint
	"Kiln - BCP": 9_695_564.62 + 21_841_158.00 + 4_496_195.93,  # Kiln + Clinker Silo OH + maint
	"Cement Mill - BCP": 4_281_033.81 + 2_148_370.47 + 30_487_653.45 + 185_829.29,  # CemMill + CemSilos OH + maint
	"Coal Mill - BCP": 1_265_433.40 + 1_549_564.75 + 1_348_204.53 + 1_105_809.72 + 4_315.00,  # Coal + Petcoke + Circ + maint
	"Packing - BCP": 12_956_220.09 + 17_406_229.68,  # Packing OH + maint
	# Support CCs
	"Power Plant - BCP": 8_896_717.79 + 84_842_232.46 + 151_705_143.03,  # Power OH + Wartsila + maint
	# General/Admin (for allocation)
	"Safety - BCP": 2_564_944.96,  # HSE
	"Laboratory - BCP": 11_874_286.19,
}

# Feb 2020 KWH consumption by cost center
FEB_KWH = {
	"Crusher - BCP": 188747 + 130415,  # CRUSHR01 + CRUSHR02
	"Raw Mill - BCP": 4198511,  # RMILLV01
	"Coal Mill - BCP": 978952,  # COAMIV01
	"Kiln - BCP": 4776975,  # KILN01
	"Cement Mill - BCP": 3482445,  # FINMIB01
	"Packing - BCP": 32654 + 39414 + 26289,  # PACKER01+02+03
}
FEB_KWH_GENERATED = 14180150


def create_feb_costing_period():
	"""Create Feb 2020 Costing Period."""
	cp_name = "CP-BCP-2020-02-01"
	if frappe.db.exists("Costing Period", cp_name):
		print(f"  {cp_name} already exists")
		return cp_name

	doc = frappe.get_doc({
		"doctype": "Costing Period",
		"period_name": "Feb 2020",
		"company": "Badia Cement PSJ",
		"fiscal_year": "2020",
		"period_start": "2020-02-01",
		"period_end": "2020-02-29",
		"previous_period": "CP-BCP-2020-01-01",
	})
	doc.insert(ignore_permissions=True)
	doc.submit()
	frappe.db.commit()
	print(f"  Created and submitted {cp_name}")
	return cp_name


def create_feb_co_documents():
	"""Create CO Documents for Feb 2020 production cost centers."""
	costing_period = "CP-BCP-2020-02-01"
	clearing_cc = "Main - BCP"
	primary_ce = frappe.db.get_value("Cost Element", {"cost_element_type": "Primary"}, "name")

	created = 0
	for cc, amount in FEB_CC_AMOUNTS.items():
		if amount <= 0:
			continue

		existing = frappe.get_all("CO Document", filters={
			"period": costing_period,
			"remarks": ["like", f"%Demo OH CC%{cc}%"],
			"docstatus": 1,
		})
		if existing:
			continue

		doc = frappe.get_doc({
			"doctype": "CO Document",
			"co_document_type": "Primary Mirror",
			"company": "Badia Cement PSJ",
			"cost_element": primary_ce,
			"period": costing_period,
			"posting_date": "2020-02-29",
			"remarks": f"Demo OH CC + Maintenance for {cc}",
			"lines": [
				{"cost_center": cc, "debit_amount": amount, "credit_amount": 0},
				{"cost_center": clearing_cc, "debit_amount": 0, "credit_amount": amount},
			],
		})
		doc.insert(ignore_permissions=True)
		doc.submit()
		created += 1
		print(f"  Created CO Doc for {cc}: {amount:,.2f}")

	frappe.db.set_value("Costing Period", costing_period, "primary_mirror_status", "Completed")
	frappe.db.commit()
	print(f"  CO Documents: {created} created")


def create_feb_power_production():
	"""Create Power Production Record for Feb 2020."""
	costing_period = "CP-BCP-2020-02-01"
	ppr_name = f"PWR-{costing_period}"

	if frappe.db.exists("Power Production Record", ppr_name):
		print(f"  {ppr_name} already exists")
		return

	doc = frappe.get_doc({
		"doctype": "Power Production Record",
		"costing_period": costing_period,
		"total_kwh_generated": FEB_KWH_GENERATED,
		"dewa_kwh_purchased": 0,
		"general_service_cc": "Plant Administration - BCP",
		"kwh_consumption_table": [
			{"cost_center": cc, "kwh_consumed": kwh}
			for cc, kwh in FEB_KWH.items()
		],
		"remarks": "Demo data from SAP KWH Transactions (Feb 2020)",
	})
	doc.insert(ignore_permissions=True)
	doc.submit()
	frappe.db.set_value("Costing Period", costing_period, "power_status", "KWH Posted")
	frappe.db.commit()
	print(f"  Created and submitted {ppr_name}")
	print(f"    Generated: {FEB_KWH_GENERATED:,.0f} KWH")
	print(f"    Consumed: {sum(FEB_KWH.values()):,.0f} KWH across {len(FEB_KWH)} CCs")


def create_feb_process_orders():
	"""Create Process Orders for Feb 2020."""
	costing_period = "CP-BCP-2020-02-01"
	created = 0
	for po_data in FEB_PROCESS_ORDERS:
		recipe_name = f"RECIPE-{po_data['recipe_code']}"
		po_name = f"PO-{po_data['recipe_code']}-{costing_period}"

		if frappe.db.exists("Process Order", po_name):
			continue

		recipe_doc = frappe.get_doc("Production Recipe", recipe_name)
		doc = frappe.get_doc({
			"doctype": "Process Order",
			"costing_period": costing_period,
			"production_recipe": recipe_name,
			"cost_center": recipe_doc.cost_center,
			"output_entries": [
				{
					"item_code": out["item_code"],
					"qty": out["qty"],
					"posting_date": "2020-02-29",
					"movement_type": out["movement_type"],
					"target_warehouse": "Work In Progress - BCP" if out["item_code"].startswith("SF-") else "Finished Goods - BCP" if out["item_code"].startswith("FG-") else "Stores - BCP",
				}
				for out in po_data["outputs"]
			],
			"input_entries": [
				{
					"item_code": inp["item_code"],
					"qty": inp["qty"],
					"posting_date": "2020-02-29",
					"movement_type": inp["movement_type"],
					"source_warehouse": "Work In Progress - BCP" if inp["item_code"].startswith("SF-") or inp["item_code"].startswith("FG-") else "Stores - BCP",
				}
				for inp in po_data["inputs"]
			],
			"remarks": "Demo data from SAP Process Orders Transactions (Feb 2020)",
		})
		doc.insert(ignore_permissions=True)
		created += 1
		print(f"  Created {po_name}: output={po_data['outputs'][0]['qty']:.2f}")

	frappe.db.commit()
	print(f"  Process Orders: {created} created")


def submit_feb_process_orders():
	"""Submit all draft Process Orders for Feb 2020."""
	costing_period = "CP-BCP-2020-02-01"
	draft_pos = frappe.get_all(
		"Process Order",
		filters={"costing_period": costing_period, "docstatus": 0},
		pluck="name",
	)
	submitted = 0
	for po_name in draft_pos:
		try:
			doc = frappe.get_doc("Process Order", po_name)
			doc.submit()
			submitted += 1
		except Exception as e:
			print(f"  ERROR submitting {po_name}: {e}")

	frappe.db.set_value("Costing Period", costing_period, "process_order_status", "Created")
	frappe.db.commit()
	print(f"  Process Orders: {submitted} submitted")


def run_feb_allocation():
	"""Run allocation cycles for Feb 2020."""
	from std_manufacturing.api.allocation_engine import execute_allocation_run

	costing_period = "CP-BCP-2020-02-01"
	try:
		result = execute_allocation_run(costing_period)
		frappe.db.set_value("Costing Period", costing_period, "allocation_status", "Completed")
		frappe.db.commit()
		print(f"  Allocation Run completed: {result}")
	except Exception as e:
		print(f"  ERROR running allocation: {e}")
		import traceback
		traceback.print_exc()


def run_feb_production_costing():
	"""Calculate unit costs for Feb 2020 Process Orders."""
	from std_manufacturing.api.process_order import calculate_unit_costs

	costing_period = "CP-BCP-2020-02-01"
	pos = frappe.get_all(
		"Process Order",
		filters={"costing_period": costing_period, "docstatus": 1, "status": "Open"},
		pluck="name",
	)
	calculated = 0
	for po_name in pos:
		try:
			calculate_unit_costs(po_name)
			calculated += 1
			doc = frappe.get_doc("Process Order", po_name)
			print(f"  {po_name}: output={doc.total_output_qty:.2f}, cc_balance={doc.cc_balance:.2f}, unit_cost={doc.unit_cost:.2f}, ytd_unit_cost={doc.ytd_unit_cost:.2f}")
		except Exception as e:
			print(f"  ERROR {po_name}: {e}")

	frappe.db.set_value("Costing Period", costing_period, "production_cost_status", "Calculated")
	frappe.db.commit()
	print(f"  Production Costing: {calculated} calculated")


def print_feb_summary():
	"""Print Feb 2020 results with YTD comparison."""
	costing_period = "CP-BCP-2020-02-01"
	print("\n" + "=" * 100)
	print("FEB 2020 RESULTS (with YTD Jan+Feb)")
	print("=" * 100)

	pos = frappe.get_all(
		"Process Order",
		filters={"costing_period": costing_period, "docstatus": 1},
		fields=["name", "recipe_name", "total_output_qty", "cc_balance", "unit_cost",
				"ytd_output_qty", "ytd_cc_balance", "ytd_unit_cost",
				"standard_rate", "cost_variance"],
		order_by="name",
	)

	if pos:
		print(f"\n  {'Recipe':<25} {'Feb Qty':>10} {'Feb CC Bal':>14} {'Feb CPU':>10} {'YTD Qty':>12} {'YTD CC Bal':>15} {'YTD CPU':>10} {'Std Rate':>10} {'Var':>10}")
		print(f"  {'-'*25} {'-'*10} {'-'*14} {'-'*10} {'-'*12} {'-'*15} {'-'*10} {'-'*10} {'-'*10}")
		for po in pos:
			print(f"  {po.recipe_name or '':<25} {flt(po.total_output_qty):>10.0f} {flt(po.cc_balance):>14.0f} {flt(po.unit_cost):>10.2f} {flt(po.ytd_output_qty):>12.0f} {flt(po.ytd_cc_balance):>15.0f} {flt(po.ytd_unit_cost):>10.2f} {flt(po.standard_rate):>10.2f} {flt(po.cost_variance):>10.2f}")

	# Compare with Jan
	jan_pos = frappe.get_all(
		"Process Order",
		filters={"costing_period": "CP-BCP-2020-01-01", "docstatus": 1},
		fields=["recipe_name", "unit_cost"],
		order_by="name",
	)
	jan_map = {p.recipe_name: p.unit_cost for p in jan_pos}

	print(f"\n  Unit Cost Trend (Jan → Feb → YTD):")
	for po in pos:
		jan_cpu = flt(jan_map.get(po.recipe_name, 0))
		feb_cpu = flt(po.unit_cost)
		ytd_cpu = flt(po.ytd_unit_cost)
		trend = "↑" if feb_cpu > jan_cpu else "↓" if feb_cpu < jan_cpu else "="
		print(f"    {po.recipe_name or '':<25} Jan={jan_cpu:>10.2f} → Feb={feb_cpu:>10.2f} {trend} → YTD={ytd_cpu:>10.2f}")

	print("\n" + "=" * 100)


def setup_feb():
	"""Run all Feb 2020 setup steps."""
	print("Setting up Feb 2020 Costing Period...")
	print()

	print("Step 1: Creating Costing Period...")
	create_feb_costing_period()
	print()

	print("Step 2: Creating CO Documents (Primary Mirror)...")
	create_feb_co_documents()
	print()

	print("Step 3: Creating Power Production Record...")
	create_feb_power_production()
	print()

	print("Step 4: Creating Process Orders...")
	create_feb_process_orders()
	print()

	print("Step 5: Submitting Process Orders...")
	submit_feb_process_orders()
	print()

	print("Step 6: Running Allocation...")
	run_feb_allocation()
	print()

	print("Step 7: Running Production Costing...")
	run_feb_production_costing()
	print()

	print_feb_summary()


def setup_all():
	"""Run all demo setup steps in order."""
	print("Starting demo data setup...")
	print()

	print("Step 1: Creating Items...")
	create_items()
	print()

	print("Step 2: Creating Production Phases...")
	create_phases()
	print()

	print("Step 3: Creating Standard Cost Rates for new items...")
	create_standard_cost_rates_for_produced()
	print()

	print("Step 4: Creating Production Recipes...")
	create_recipes()
	print()

	print("Step 5: Creating CO Documents for production cost centers...")
	create_co_documents_for_production_ccs()
	print()

	print("Step 6: Creating Process Orders (Jan 2020)...")
	create_process_orders()
	print()

	print("Step 7: Submitting Process Orders...")
	submit_process_orders()
	print()

	print("Step 8: Running Production Costing...")
	run_production_costing()
	print()

	print_summary()

	# Feb 2020
	print("\n\n")
	setup_feb()
