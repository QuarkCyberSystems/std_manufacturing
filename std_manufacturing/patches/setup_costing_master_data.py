"""Setup master data for the costing module.

Creates cost centers, cost elements, allocation cycles, SKF masters,
and overhead rates based on SAP Costing Cycle.xlsx reference data.

Run with: bench --site <site> execute std_manufacturing.patches.setup_costing_master_data.execute
"""

import frappe

COMPANY = "Badia Cement PSJ"
COMPANY_ABBR = "BCP"

# Cost Centers: (code, name, parent_cc_name, is_group)
COST_CENTERS = [
	# Groups
	("0000", "Production", None, 1),
	("0001", "Support Services", None, 1),
	("0002", "Utilities", None, 1),
	("0003", "Overheads", None, 1),
	("0004", "Commercial", None, 1),

	# Production CCs
	("210100", "Quarry Operations", "Production", 0),
	("220100", "Crusher", "Production", 0),
	("230100", "Raw Mill", "Production", 0),
	("230200", "Coal Mill", "Production", 0),
	("240100", "Kiln", "Production", 0),
	("250100", "Cement Mill", "Production", 0),
	("260100", "Packing", "Production", 0),

	# Support CCs
	("410100", "Workshop Maintenance", "Support Services", 0),
	("410200", "Electrical Maintenance", "Support Services", 0),
	("410300", "Civil Maintenance", "Support Services", 0),
	("420100", "Heavy Equipment", "Support Services", 0),
	("430100", "Laboratory", "Support Services", 0),
	("440100", "Plant Administration", "Support Services", 0),
	("440300", "Safety", "Support Services", 0),
	("610100", "Stores", "Support Services", 0),

	# Utility CCs
	("310100", "Power Plant", "Utilities", 0),
	("320100", "Water Treatment", "Utilities", 0),

	# Overhead CCs
	("510100", "Production Overhead", "Overheads", 0),
	("510200", "Maintenance Overhead", "Overheads", 0),
	("510300", "Admin Overhead", "Overheads", 0),

	# Commercial CCs
	("710100", "Sales and Distribution", "Commercial", 0),
	("720100", "Commercial Administration", "Commercial", 0),
	("810100", "General Administration", "Commercial", 0),
]

# Cost Elements: (code, name, type, secondary_category)
COST_ELEMENTS = [
	# Primary (will need GL account mapping later)
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

	# Secondary (allocation results)
	("CE-ALLOC-MAINT", "Maintenance Allocation", "Secondary", "Assessment"),
	("CE-ALLOC-ELEC", "Electrical Maintenance Allocation", "Secondary", "Assessment"),
	("CE-ALLOC-CIVIL", "Civil Maintenance Allocation", "Secondary", "Assessment"),
	("CE-ALLOC-HEAVY", "Heavy Equipment Allocation", "Secondary", "Assessment"),
	("CE-ALLOC-PWR", "Power Allocation", "Secondary", "Assessment"),
	("CE-ALLOC-WATER", "Water Treatment Allocation", "Secondary", "Assessment"),
	("CE-ALLOC-LAB", "Laboratory Allocation", "Secondary", "Assessment"),
	("CE-ALLOC-ADMIN", "Plant Admin Allocation", "Secondary", "Assessment"),
	("CE-ALLOC-QUARRY", "Quarry to Crusher", "Secondary", "Distribution"),
	("CE-ALLOC-CRUSH", "Crusher to Raw Mill", "Secondary", "Distribution"),
	("CE-ALLOC-RAWML", "Raw Mill to Kiln", "Secondary", "Distribution"),
	("CE-ALLOC-KILN", "Kiln to Cement Mill", "Secondary", "Distribution"),
	("CE-ALLOC-CEMNT", "Cement Mill to Packing", "Secondary", "Distribution"),
]

# Statistical Key Figures
SKF_MASTERS = [
	("KWH-TOTAL", "Total KWH Consumed", "Energy", "KWh"),
	("TONS-CRUSHED", "Tons Crushed Material", "Production Quantity", "Kg"),
	("TONS-RAW-MEAL", "Tons Raw Meal", "Production Quantity", "Kg"),
	("TONS-CLINKER", "Tons Clinker", "Production Quantity", "Kg"),
	("TONS-CEMENT", "Tons Cement", "Production Quantity", "Kg"),
	("TONS-PACKED", "Tons Packed", "Production Quantity", "Kg"),
]

# Allocation Cycles: (number, name, sender_cc_code, tracing_type, cost_element_code, co_doc_type, skf_code, receivers)
# receivers: list of (cc_code, fixed_pct) — pct is 0 for SKF/Production Ratio
ALLOCATION_CYCLES = [
	(1, "Workshop Maintenance", "410100", "Fixed Percentage", "CE-ALLOC-MAINT", "Assessment", None, [
		("220100", 10), ("230100", 15), ("230200", 10), ("240100", 25),
		("250100", 20), ("260100", 10), ("310100", 10),
	]),
	(2, "Electrical Maintenance", "410200", "Fixed Percentage", "CE-ALLOC-ELEC", "Assessment", None, [
		("220100", 10), ("230100", 15), ("230200", 10), ("240100", 20),
		("250100", 25), ("260100", 10), ("310100", 10),
	]),
	(3, "Civil Maintenance", "410300", "Fixed Percentage", "CE-ALLOC-CIVIL", "Assessment", None, [
		("220100", 10), ("230100", 15), ("230200", 5), ("240100", 30),
		("250100", 20), ("260100", 10), ("310100", 10),
	]),
	(4, "Heavy Equipment", "420100", "Fixed Percentage", "CE-ALLOC-HEAVY", "Assessment", None, [
		("210100", 70), ("220100", 30),
	]),
	(5, "Power Plant", "310100", "SKF-Based", "CE-ALLOC-PWR", "Assessment", "KWH-TOTAL", [
		("220100", 0), ("230100", 0), ("230200", 0), ("240100", 0),
		("250100", 0), ("260100", 0), ("320100", 0),
	]),
	(6, "Water Treatment", "320100", "Fixed Percentage", "CE-ALLOC-WATER", "Assessment", None, [
		("230100", 20), ("240100", 40), ("250100", 20), ("260100", 10), ("210100", 10),
	]),
	(7, "Laboratory", "430100", "Fixed Percentage", "CE-ALLOC-LAB", "Assessment", None, [
		("230100", 60), ("250100", 40),
	]),
	(8, "Plant Administration", "440100", "Fixed Percentage", "CE-ALLOC-ADMIN", "Assessment", None, [
		("210100", 5), ("220100", 10), ("230100", 15), ("230200", 10),
		("240100", 25), ("250100", 20), ("260100", 15),
	]),
	(9, "Quarry to Crusher", "210100", "Production Ratio", "CE-ALLOC-QUARRY", "Distribution", None, [
		("220100", 0),
	]),
	(10, "Crusher to Raw Mill", "220100", "Production Ratio", "CE-ALLOC-CRUSH", "Distribution", None, [
		("230100", 0),
	]),
	(11, "Raw Mill to Kiln", "230100", "Production Ratio", "CE-ALLOC-RAWML", "Distribution", None, [
		("240100", 0),
	]),
	(12, "Kiln to Cement Mill", "240100", "Production Ratio", "CE-ALLOC-KILN", "Distribution", None, [
		("250100", 0),
	]),
	(13, "Cement Mill to Packing", "250100", "Production Ratio", "CE-ALLOC-CEMNT", "Distribution", None, [
		("260100", 0),
	]),
]

# Overhead Rates (cement industry standard)
OVERHEAD_RATES = [
	("Depreciation OH", "Depreciation", 62),
	("Power OH", "Power", 25),
	("Raw Materials OH", "Raw Materials", 8),
	("Other OH", "Other", 5),
]


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

	# Ensure root exists
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
			# Primary cost elements need GL account mapping — skip for now
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

		# Ensure UOM exists
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
	"""Create allocation cycle definitions."""
	for (num, name, sender_code, tracing_type, ce_code, co_type, skf_code, receivers) in ALLOCATION_CYCLES:
		cycle_name = f"CYCLE-{num:03d}"
		if frappe.db.exists("Allocation Cycle", cycle_name):
			continue

		sender_cc = f"{_get_cc_name(sender_code)} - {COMPANY_ABBR}"
		if not frappe.db.exists("Cost Center", sender_cc):
			print(f"  Skipping cycle {num}: sender CC {sender_cc} not found")
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
			recv_cc = f"{_get_cc_name(recv_code)} - {COMPANY_ABBR}"
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
	# Get current fiscal year
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


def _get_cc_name(code):
	"""Map cost center code to name."""
	cc_map = {row[0]: row[1] for row in COST_CENTERS}
	return cc_map.get(code, code)
