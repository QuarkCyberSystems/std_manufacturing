"""Setup master data for the costing module.

Creates cost centers, cost elements, allocation cycles, SKF masters,
and overhead rates based on SAP Costing Cycle.xlsx reference data.

Cost center codes match SAP exactly (e.g., R101P5110A, R10100900P).
Allocation cycles match SAP's 12 cycles (multi-sender cycles split into sub-cycles).

Run with: bench --site <site> execute std_manufacturing.patches.setup_costing_master_data.execute
"""

import frappe

COMPANY = "Badia Cement PSJ"
COMPANY_ABBR = "BCP"

# ─── Cost Centers ────────────────────────────────────────────────────────────
# SAP codes from Costing Cycle.xlsx "References" sheet.
# Format: (sap_code, description, parent_group, is_group)

COST_CENTERS = [
	# Groups
	("0000", "Production", None, 1),
	("0001", "Support Services", None, 1),
	("0002", "Quarry", "Production", 1),
	("0003", "Crusher", "Production", 1),
	("0004", "Mill", "Production", 1),
	("0005", "Kiln Area", "Production", 1),
	("0006", "Cement Area", "Production", 1),
	("0007", "Packing Area", "Production", 1),
	("0008", "Power", "Support Services", 1),
	("0009", "General", "Support Services", 1),
	("0010", "Commercial", None, 1),

	# ── Quarry CCs ──
	("R101P5110A", "Blasted Lim Quarry", "Quarry", 0),
	("R101P5120A", "Limestone Mined", "Quarry", 0),
	("R101P5190A", "Gen Serv Lim Quarry", "Quarry", 0),
	("R101P6100A", "Blasted Bas Quarry", "Quarry", 0),
	("R101P6190A", "Gen Serv Bas Quarry", "Quarry", 0),
	("R101P6200A", "Basalt Mined", "Quarry", 0),

	# ── Crusher CCs ──
	("R101P4100A", "Limestone Crusher", "Crusher", 0),
	("R101P4110A", "Basalt Crusher", "Crusher", 0),
	("R101P4120A", "Limest Crushed Dep", "Crusher", 0),
	("R101P4130A", "Basalt Crushed Dep", "Crusher", 0),
	("R101P4500A", "Sand Deposit", "Crusher", 0),

	# ── Mill CCs ──
	("R101P0700P", "Coal Mill", "Mill", 0),
	("R101P4700A", "Coal and Petcoke Dep", "Mill", 0),
	("R101P4710A", "Circular Storage Mix", "Mill", 0),
	("R101P0800P", "Raw Mill", "Mill", 0),
	("R101P0810P", "Gypsum Crusher", "Mill", 0),
	("R101P0820P", "Additive Storage", "Mill", 0),

	# ── Kiln Area CCs ──
	("R101P0300C", "Kiln", "Kiln Area", 0),
	("R101P0310C", "Clinker Silo", "Kiln Area", 0),

	# ── Cement Area CCs ──
	("R101P0400D", "Cement Mill", "Cement Area", 0),
	("R101P0410D", "Cement Silos", "Cement Area", 0),

	# ── Packing Area CCs ──
	("R101P0600F", "Bulk Loading", "Packing Area", 0),
	("R101P0610F", "Bag Pack and Loading", "Packing Area", 0),

	# ── Power CCs ──
	("R10100900P", "Power HFO and LFO", "Power", 0),
	("R10100930N", "Power Subc Wartsila", "Power", 0),
	("R10100940N", "Power Oper Wartsila", "Power", 0),
	("R10100950N", "Power Maint Wartsila", "Power", 0),

	# ── General / Support CCs ──
	("R10100900M", "Plant Maint Internal", "General", 0),
	("R10100910M", "Plant Maint Internal 2", "General", 0),
	("R10100A10S", "General Services", "General", 0),
	("R10100A20S", "HSE Manager", "General", 0),
	("R10100A30S", "Production Manager", "General", 0),
	("R10100A40S", "Housing Colony", "General", 0),
	("R10100A50S", "Laboratory", "General", 0),

	# ── Commercial CCs ──
	("R901001000", "CEO", "Commercial", 0),
	("R901001100", "Sales Dept", "Commercial", 0),
	("R901002100", "Finance Dept", "Commercial", 0),
	("R901002200", "IT Dept", "Commercial", 0),

	# ── Special CCs ──
	("R101P9001A", "Inventory Reval", "Production", 0),
	("R101P9002A", "Out of Prod Cost", "Production", 0),
]

# Cost Elements: (code, name, type, secondary_category)
COST_ELEMENTS = [
	# Primary (need GL account mapping)
	("CE-MATL", "Materials (Stock Adjustment)", "Primary", None),
	("CE-MAT-RAW", "Raw Materials", "Primary", None),
	("CE-MAT-FUEL", "Fuel Materials", "Primary", None),
	("CE-MAT-SPARE", "Spare Parts", "Primary", None),
	("CE-MAT-PACK", "Packing Materials", "Primary", None),
	("CE-LABOR-DIR", "Direct Labor", "Primary", None),
	("CE-LABOR-IND", "Indirect Labor", "Primary", None),
	("CE-DEPR", "Depreciation", "Primary", None),
	("CE-POWER", "Power & Electricity", "Primary", None),
	("CE-WATER", "Water", "Primary", None),
	("CE-INSUR", "Insurance", "Primary", None),
	("CE-RENT", "Rent & Lease", "Primary", None),
	("CE-OTHER", "Other Expenses", "Primary", None),

	# Secondary (allocation results) — match SAP cycle names
	("CE-ALLOC-WARTSILA", "Wartsila Subcontract Allocation", "Secondary", "Assessment"),
	("CE-ALLOC-MAINT", "Maintenance Allocation", "Secondary", "Assessment"),
	("CE-ALLOC-WARTSILA-M", "Wartsila Maint to Oper", "Secondary", "Assessment"),
	("CE-ALLOC-WARTSILA-O", "Wartsila Oper to Power", "Secondary", "Assessment"),
	("CE-ALLOC-PWR", "Power Allocation", "Secondary", "Assessment"),
	("CE-ALLOC-GENERAL", "General Services Allocation", "Secondary", "Assessment"),
	("CE-ALLOC-BAS-GS", "Basalt Gen Serv Allocation", "Secondary", "Distribution"),
	("CE-ALLOC-LIM-GS", "Limestone Gen Serv Allocation", "Secondary", "Distribution"),
	("CE-ALLOC-CRUSH-DEP", "Crusher Deposit Allocation", "Secondary", "Distribution"),
	("CE-ALLOC-COAL-DEP", "Coal Deposit Allocation", "Secondary", "Distribution"),
	("CE-ALLOC-CLINKER", "Clinker Silo Allocation", "Secondary", "Distribution"),
	("CE-ALLOC-CEMENT", "Cement Silo Allocation", "Secondary", "Distribution"),
	# Fuel revaluation
	("CE-FUEL-REVAL", "Fuel Revaluation", "Secondary", "Assessment"),
]

# ─── Statistical Key Figures ─────────────────────────────────────────────────
SKF_MASTERS = [
	("KWH-TOTAL", "Total KWH Consumed", "Energy", "KWh"),
	("TONS-CRUSHED", "Tons Crushed Material", "Production Quantity", "Kg"),
	("TONS-RAW-MEAL", "Tons Raw Meal", "Production Quantity", "Kg"),
	("TONS-CLINKER", "Tons Clinker", "Production Quantity", "Kg"),
	("TONS-CEMENT", "Tons Cement", "Production Quantity", "Kg"),
	("TONS-PACKED", "Tons Packed", "Production Quantity", "Kg"),
]

# ─── Allocation Cycles ──────────────────────────────────────────────────────
# SAP 12 cycles from Costing Cycle.xlsx "Cycles" sheet.
# Multi-sender cycles are split into sub-cycles (e.g., 2.1 and 2.2).
# Format: (number, name, sender_cc_code, tracing_type, cost_element, co_doc_type, skf_code, receivers)

ALLOCATION_CYCLES = [
	# Cycle 1: Power Subc Wartsila → 70% Oper, 30% Maint
	(1, "Power Subc Wartsila Split", "R10100930N", "Fixed Percentage", "CE-ALLOC-WARTSILA", "Assessment", None, [
		("R10100940N", 70), ("R10100950N", 30),
	]),

	# Cycle 2: Plant Maint Internal (2 senders) → 75% Kiln, 25% Cement Mill
	(2, "Plant Maint Internal to Kiln/CM", "R10100900M", "Fixed Percentage", "CE-ALLOC-MAINT", "Assessment", None, [
		("R101P0300C", 75), ("R101P0400D", 25),
	]),
	(3, "Plant Maint Internal 2 to Kiln/CM", "R10100910M", "Fixed Percentage", "CE-ALLOC-MAINT", "Assessment", None, [
		("R101P0300C", 75), ("R101P0400D", 25),
	]),

	# Cycle 3: Power Maint Wartsila → Power Oper Wartsila (100%)
	(4, "Power Maint to Power Oper", "R10100950N", "Fixed Percentage", "CE-ALLOC-WARTSILA-M", "Assessment", None, [
		("R10100940N", 100),
	]),

	# Cycle 4: Power Oper Wartsila → Power HFO & LFO (100%)
	(5, "Power Oper to Power HFO", "R10100940N", "Fixed Percentage", "CE-ALLOC-WARTSILA-O", "Assessment", None, [
		("R10100900P", 100),
	]),

	# Cycle 5: Power HFO & LFO → 9 receivers based on KWH
	(6, "Power KWH Allocation", "R10100900P", "SKF-Based", "CE-ALLOC-PWR", "Assessment", "KWH-TOTAL", [
		("R101P4100A", 0),   # Limestone crusher
		("R101P4110A", 0),   # Basalt crusher
		("R101P0700P", 0),   # Coal mill
		("R101P0800P", 0),   # Raw mill
		("R101P0300C", 0),   # Kiln
		("R101P0400D", 0),   # Cement mill
		("R101P0610F", 0),   # Bag pack
		("R10100A10S", 0),   # General services (balance)
		("R101P0310C", 0),   # Clinker bins (PACKER area KWH)
	]),

	# Cycle 6: General Services (5 senders) → 75% Kiln, 25% Cement Mill
	(7, "General Services to Kiln/CM", "R10100A10S", "Fixed Percentage", "CE-ALLOC-GENERAL", "Assessment", None, [
		("R101P0300C", 75), ("R101P0400D", 25),
	]),
	(8, "HSE Manager to Kiln/CM", "R10100A20S", "Fixed Percentage", "CE-ALLOC-GENERAL", "Assessment", None, [
		("R101P0300C", 75), ("R101P0400D", 25),
	]),
	(9, "Production Manager to Kiln/CM", "R10100A30S", "Fixed Percentage", "CE-ALLOC-GENERAL", "Assessment", None, [
		("R101P0300C", 75), ("R101P0400D", 25),
	]),
	(10, "Housing Colony to Kiln/CM", "R10100A40S", "Fixed Percentage", "CE-ALLOC-GENERAL", "Assessment", None, [
		("R101P0300C", 75), ("R101P0400D", 25),
	]),
	(11, "Laboratory to Kiln/CM", "R10100A50S", "Fixed Percentage", "CE-ALLOC-GENERAL", "Assessment", None, [
		("R101P0300C", 75), ("R101P0400D", 25),
	]),

	# Cycle 7: Gen Serv Bas Quarry → Blasted Bas Quarry (100%)
	(12, "Basalt Gen Serv to Blasted", "R101P6190A", "Fixed Percentage", "CE-ALLOC-BAS-GS", "Distribution", None, [
		("R101P6100A", 100),
	]),

	# Cycle 8: Gen Serv Lim Quarry → Blasted Lim Quarry (100%)
	(13, "Limestone Gen Serv to Blasted", "R101P5190A", "Fixed Percentage", "CE-ALLOC-LIM-GS", "Distribution", None, [
		("R101P5110A", 100),
	]),

	# Cycle 9: Crusher deposits (3 senders) → Raw Mill (100%)
	(14, "Limest Crushed Dep to Raw Mill", "R101P4120A", "Fixed Percentage", "CE-ALLOC-CRUSH-DEP", "Distribution", None, [
		("R101P0800P", 100),
	]),
	(15, "Basalt Crushed Dep to Raw Mill", "R101P4130A", "Fixed Percentage", "CE-ALLOC-CRUSH-DEP", "Distribution", None, [
		("R101P0800P", 100),
	]),
	(16, "Sand Deposit to Raw Mill", "R101P4500A", "Fixed Percentage", "CE-ALLOC-CRUSH-DEP", "Distribution", None, [
		("R101P0800P", 100),
	]),

	# Cycle 10: Coal deposits (2 senders) → Coal Mill (100%)
	(17, "Coal Petcoke Dep to Coal Mill", "R101P4700A", "Fixed Percentage", "CE-ALLOC-COAL-DEP", "Distribution", None, [
		("R101P0700P", 100),
	]),
	(18, "Circular Storage to Coal Mill", "R101P4710A", "Fixed Percentage", "CE-ALLOC-COAL-DEP", "Distribution", None, [
		("R101P0700P", 100),
	]),

	# Cycle 11: Clinker Silo → Cement Mill (100%)
	(19, "Clinker Silo to Cement Mill", "R101P0310C", "Fixed Percentage", "CE-ALLOC-CLINKER", "Distribution", None, [
		("R101P0400D", 100),
	]),

	# Cycle 12: Cement Silos → Bulk Loading + Bag Pack (Based on QTY)
	# For now using Fixed Percentage as approximation — will refine with actual QTY data
	(20, "Cement Silos to Packing", "R101P0410D", "Fixed Percentage", "CE-ALLOC-CEMENT", "Distribution", None, [
		("R101P0600F", 5), ("R101P0610F", 95),
	]),
]

# Overhead Rates (cement industry standard)
OVERHEAD_RATES = [
	("Depreciation OH", "Depreciation", 62),
	("Power OH", "Power", 25),
	("Raw Materials OH", "Raw Materials", 8),
	("Other OH", "Other", 5),
]


# ─── Helper ──────────────────────────────────────────────────────────────────

def _cc_full_name(sap_code):
	"""Return the full Cost Center name for a SAP code: 'Description - BCP'."""
	cc_map = {row[0]: row[1] for row in COST_CENTERS}
	desc = cc_map.get(sap_code)
	if desc:
		return f"{desc} - {COMPANY_ABBR}"
	return sap_code


# ─── Execution ───────────────────────────────────────────────────────────────

def execute():
	"""Create all costing master data."""
	create_cost_centers()
	create_cost_elements()
	create_skf_masters()
	create_allocation_cycles()
	create_overhead_rates()
	frappe.db.commit()
	print("Costing master data setup complete.")


def create_cost_centers():
	"""Create cost centers from the SAP reference data."""
	root_cc = f"{COMPANY} - {COMPANY_ABBR}"

	if not frappe.db.exists("Cost Center", root_cc):
		print(f"Root cost center '{root_cc}' not found. Skipping cost center creation.")
		return

	for code, name, parent_name, is_group in COST_CENTERS:
		cc_name = f"{name} - {COMPANY_ABBR}"
		if frappe.db.exists("Cost Center", cc_name):
			continue

		parent = root_cc
		if parent_name:
			parent = f"{parent_name} - {COMPANY_ABBR}"

		cc = frappe.new_doc("Cost Center")
		cc.cost_center_name = name
		cc.company = COMPANY
		cc.parent_cost_center = parent
		cc.is_group = is_group
		try:
			cc.insert(ignore_permissions=True)
			print(f"  Created CC: {cc_name}")
		except Exception as e:
			print(f"  Error creating CC {cc_name}: {e}")


def create_cost_elements():
	"""Create cost elements. Primary elements are skipped if no GL account mapping exists yet."""
	for code, name, ce_type, secondary_cat in COST_ELEMENTS:
		if frappe.db.exists("Cost Element", code):
			continue

		if ce_type == "Primary":
			print(f"  Skipped Primary CE: {code} - {name} (needs GL account mapping)")
			continue

		ce = frappe.new_doc("Cost Element")
		ce.cost_element_code = code
		ce.cost_element_name = name
		ce.cost_element_type = ce_type
		if secondary_cat:
			ce.secondary_category = secondary_cat
		ce.status = "Active"
		try:
			ce.insert(ignore_permissions=True)
			print(f"  Created CE: {code} - {name}")
		except Exception as e:
			print(f"  Error creating CE {code}: {e}")


def create_skf_masters():
	"""Create statistical key figure masters."""
	for code, name, category, uom_name in SKF_MASTERS:
		if frappe.db.exists("Statistical Key Figure", code):
			continue

		if not frappe.db.exists("UOM", uom_name):
			uom = frappe.new_doc("UOM")
			uom.uom_name = uom_name
			uom.insert(ignore_permissions=True)

		skf = frappe.new_doc("Statistical Key Figure")
		skf.skf_code = code
		skf.skf_name = name
		skf.skf_category = category
		skf.uom = uom_name
		skf.source = "Manual Entry"
		skf.status = "Active"
		try:
			skf.insert(ignore_permissions=True)
			print(f"  Created SKF: {code} - {name}")
		except Exception as e:
			print(f"  Error creating SKF {code}: {e}")


def create_allocation_cycles():
	"""Create allocation cycle definitions matching SAP's 12 cycles."""
	for (num, name, sender_code, tracing_type, ce_code, co_type, skf_code, receivers) in ALLOCATION_CYCLES:
		cycle_name = f"CYCLE-{num:03d}"
		if frappe.db.exists("Allocation Cycle", cycle_name):
			continue

		sender_cc = _cc_full_name(sender_code)
		if not frappe.db.exists("Cost Center", sender_cc):
			print(f"  Skipping cycle {num}: sender CC {sender_cc} not found")
			continue

		# Ensure cost element exists
		if not frappe.db.exists("Cost Element", ce_code):
			print(f"  Skipping cycle {num}: cost element {ce_code} not found")
			continue

		cycle = frappe.new_doc("Allocation Cycle")
		cycle.cycle_number = num
		cycle.cycle_name = name
		cycle.co_document_type = co_type
		cycle.sender_cost_center = sender_cc
		cycle.secondary_cost_element = ce_code
		cycle.tracing_type = tracing_type
		cycle.is_active = 1

		if skf_code:
			cycle.tracing_skf = skf_code

		for recv_code, pct in receivers:
			recv_cc = _cc_full_name(recv_code)
			cycle.append("receivers", {
				"cost_center": recv_cc,
				"fixed_percentage": pct,
			})

		try:
			cycle.insert(ignore_permissions=True)
			print(f"  Created Cycle {num}: {name}")
		except Exception as e:
			print(f"  Error creating Cycle {num}: {e}")


def create_overhead_rates():
	"""Create overhead rate definitions."""
	fiscal_year = frappe.defaults.get_global_default("fiscal_year")
	if not fiscal_year:
		print("  No fiscal year set, skipping overhead rates")
		return

	for name, group, pct in OVERHEAD_RATES:
		oh_name = f"{name}-{fiscal_year}"
		if frappe.db.exists("Overhead Rate", oh_name):
			continue

		oh = frappe.new_doc("Overhead Rate")
		oh.overhead_name = name
		oh.cost_element_group = group
		oh.standard_pct = pct
		oh.fiscal_year = fiscal_year
		oh.company = COMPANY
		oh.status = "Active"
		try:
			oh.insert(ignore_permissions=True)
			print(f"  Created OH Rate: {name} ({pct}%)")
		except Exception as e:
			print(f"  Error creating OH Rate {name}: {e}")
