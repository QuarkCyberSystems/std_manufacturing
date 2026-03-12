"""
Test Costing Cycle — based on Costing Cycle.xlsx (SAP reference data)
Creates real transactions for a 2-month (Jan+Feb 2020) cycle for purchased raw materials.

Run with: bench --site badia.localhost execute /tmp/test_costing_cycle.py
"""

import frappe
from frappe.utils import flt

# ──────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────
COMPANY = None  # auto-detect
WAREHOUSE = None
COMPANY_ABBR = None


def get_company():
	global COMPANY, WAREHOUSE, COMPANY_ABBR
	COMPANY = frappe.db.get_single_value("Global Defaults", "default_company")
	if not COMPANY:
		COMPANY = frappe.db.get_value("Company", {}, "name")
	COMPANY_ABBR = frappe.db.get_value("Company", COMPANY, "abbr")
	WAREHOUSE = f"Stores - {COMPANY_ABBR}"
	if not frappe.db.exists("Warehouse", WAREHOUSE):
		WAREHOUSE = frappe.db.get_value("Warehouse", {"company": COMPANY, "is_group": 0}, "name")
	print(f"Company: {COMPANY} ({COMPANY_ABBR}), Warehouse: {WAREHOUSE}")


# ──────────────────────────────────────────────────────────────
# MATERIAL MASTER — from "Purchased Materials YTD CPU" sheet
# Format: (item_code, item_name, initial_qty, initial_value, budget_std_rate,
#           jan_purchase_qty, jan_purchase_value, feb_purchase_qty, feb_purchase_value)
# ──────────────────────────────────────────────────────────────
PURCHASED_MATERIALS = [
	# Key purchased raw materials with actual SAP data
	("RM-120002", "Pouzzolana/ground Fine",     556667,   4876673097.77, 8760.49,
	 130266.73, 1172400570,    58123.80,  523114200),
	("RM-120070", "Gypsum/dihydrate/mined",     24893,    203541738.72,  8176.67,
	 20995.92,  174266136,     3019.85,   25064755),
	("RM-120119", "Coal/BTZ/ground",             57421,    4280034303.96, 74537.79,
	 0,         0,             7520.83,   965674572),
	("RM-120238", "Silica sand",                 37524,    212399291.98,  5660.36,
	 0,         0,             21867.60,  130768248),
	("RM-120402", "Limestone/blasted",           0,        0,             350.00,
	 23362.98,  8133966.99,    329466.17, 44068932.87),
	("RM-2000011", "LFO - Light Fuel Oil",      116998,   44121038.91,   377.11,
	 83773.00,  25040884.00,   224463.00, 102084929.00),
	("RM-2000012", "HFO - Heavy Fuel Oil",      9009.90,  2102717121.02, 233378.52,
	 3679.00,   812027721.93,  3229.85,   713346410.28),
	("PK-3100061", "Bags CEM II 32.5N PP",      987334,   84404445.78,   85.49,
	 910000,    161700000,     732399,    131400000),
	("PK-3100070", "Bags CEM II 42.5N PP",      1401368,  156706810.66,  111.82,
	 1010000,   171700000,     1011051,   181800000),
]

# Simulated consumption (issued to production) — estimated from process orders
CONSUMPTION_JAN = {
	"RM-120002":  80000,      # Pouzzolana issued to cement mill
	"RM-120070":  12000,      # Gypsum issued to cement mill
	"RM-120402":  20000,      # Limestone issued to crusher
	"RM-2000011": 60000,      # LFO issued to power plant
	"RM-2000012": 2500,       # HFO issued to power plant
	"PK-3100061": 600000,     # Bags issued to packing
	"PK-3100070": 700000,     # Bags issued to packing
}


def step_0_cleanup():
	"""Remove any previous test data."""
	print("\n═══ Step 0: Cleanup previous test data ═══")

	# Delete PLCV Entries first
	for dt in ["PLCV Entry"]:
		for prefix in ["RM-%", "PK-%"]:
			for name in frappe.get_all(dt, filters={"item_code": ("like", prefix)}, pluck="name"):
				doc = frappe.get_doc(dt, name)
				if doc.docstatus == 1:
					doc.cancel()
				doc.delete()
				print(f"  Deleted {dt}: {name}")

	# Delete Standard Cost Revaluation (cancel first to revert rates + cancel stock recon)
	for name in frappe.get_all("Standard Cost Revaluation", filters={"company": COMPANY}, pluck="name"):
		if not frappe.db.exists("Standard Cost Revaluation", name):
			continue
		doc = frappe.get_doc("Standard Cost Revaluation", name)
		if doc.docstatus == 1:
			try:
				doc.cancel()
			except Exception:
				frappe.db.set_value("Standard Cost Revaluation", name, "docstatus", 2)
		doc.delete()
		print(f"  Deleted Standard Cost Revaluation: {name}")

	# Delete Standard Cost Rates
	for prefix in ["RM-%", "PK-%"]:
		for name in frappe.get_all("Standard Cost Rate", filters={"item_code": ("like", prefix)}, pluck="name"):
			if not frappe.db.exists("Standard Cost Rate", name):
				continue
			doc = frappe.get_doc("Standard Cost Rate", name)
			if doc.docstatus == 1:
				doc.cancel()
			doc.delete()
			print(f"  Deleted Standard Cost Rate: {name}")

	# Delete Costing Period
	for name in frappe.get_all("Costing Period", filters={"company": COMPANY, "period_start": (">=", "2020-01-01")}, pluck="name"):
		doc = frappe.get_doc("Costing Period", name)
		if doc.docstatus == 1:
			try:
				doc.cancel()
			except Exception:
				frappe.db.set_value("Costing Period", name, "docstatus", 2)
		doc.delete()
		print(f"  Deleted Costing Period: {name}")

	# Delete Stock Reconciliations
	for name in frappe.get_all("Stock Reconciliation", filters={"company": COMPANY, "posting_date": (">=", "2019-12-01"), "posting_date": ("<=", "2020-12-31")}, pluck="name"):
		doc = frappe.get_doc("Stock Reconciliation", name)
		if doc.docstatus == 1:
			doc.cancel()
		doc.delete()
		print(f"  Deleted Stock Reconciliation: {name}")

	# Delete Stock Entries (material issues + opening receipts)
	for name in frappe.get_all("Stock Entry", filters={"company": COMPANY, "posting_date": (">=", "2019-12-01"), "posting_date": ("<=", "2020-12-31")}, pluck="name"):
		doc = frappe.get_doc("Stock Entry", name)
		if doc.docstatus == 1:
			doc.cancel()
		doc.delete()

	# Delete Purchase Receipts
	for name in frappe.get_all("Purchase Receipt", filters={"company": COMPANY, "posting_date": (">=", "2019-12-01"), "posting_date": ("<=", "2020-12-31")}, pluck="name"):
		doc = frappe.get_doc("Purchase Receipt", name)
		if doc.docstatus == 1:
			doc.cancel()
		doc.delete()

	# Delete test items
	for mat in PURCHASED_MATERIALS:
		if frappe.db.exists("Item", mat[0]):
			frappe.delete_doc("Item", mat[0], force=True)
			print(f"  Deleted Item: {mat[0]}")

	frappe.db.commit()
	print("  Cleanup complete.")


def step_1_create_items():
	"""Create items with Standard Cost valuation method."""
	print("\n═══ Step 1: Create Items ═══")

	# Ensure item groups exist
	for group in ["Raw Material", "Packing Material"]:
		if not frappe.db.exists("Item Group", group):
			frappe.get_doc({
				"doctype": "Item Group",
				"item_group_name": group,
				"parent_item_group": "All Item Groups",
			}).insert()

	for item_code, item_name, init_qty, init_val, std_rate, *_ in PURCHASED_MATERIALS:
		if frappe.db.exists("Item", item_code):
			print(f"  {item_code} already exists, skipping")
			continue

		group = "Packing Material" if item_code.startswith("PK-") else "Raw Material"
		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": item_code,
			"item_name": item_name,
			"item_group": group,
			"stock_uom": "Kg",
			"is_stock_item": 1,
			"custom_valuation_method": "Standard Cost",
			"custom_cost_category": "Purchased",
			"custom_include_in_plcv": 1,
			"standard_rate": std_rate,
		})
		item.insert()
		print(f"  Created: {item_code} — {item_name} (Std Rate: {std_rate:,.2f})")

	frappe.db.commit()


def step_2_create_standard_cost_rates():
	"""Create Standard Cost Rate records (budget rates effective Jan 1, 2020)."""
	print("\n═══ Step 2: Create Standard Cost Rates ═══")

	fy = frappe.db.get_value("Fiscal Year", {"disabled": 0}, "name")

	for item_code, item_name, _, _, std_rate, *_ in PURCHASED_MATERIALS:
		scr_name = f"SCR-{item_code}-2020-01-01"
		if frappe.db.exists("Standard Cost Rate", scr_name):
			print(f"  {scr_name} already exists, skipping")
			continue

		scr = frappe.get_doc({
			"doctype": "Standard Cost Rate",
			"item_code": item_code,
			"standard_rate": std_rate,
			"effective_from": "2020-01-01",
			"rate_basis": "Budget",
			"fiscal_year": fy,
		})
		scr.insert()
		scr.submit()
		print(f"  SCR: {item_code} = {std_rate:,.2f} (Active from 2020-01-01)")

	frappe.db.commit()


def step_3_create_opening_stock():
	"""Create opening stock via Material Receipt Stock Entries for items with initial qty."""
	print("\n═══ Step 3: Create Opening Stock (Dec 31 2019) ═══")

	for item_code, item_name, init_qty, init_val, std_rate, *_ in PURCHASED_MATERIALS:
		if flt(init_qty) <= 0:
			continue

		se = frappe.get_doc({
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": COMPANY,
			"posting_date": "2019-12-31",
			"items": [{
				"item_code": item_code,
				"qty": init_qty,
				"basic_rate": std_rate,
				"t_warehouse": WAREHOUSE,
			}],
		})
		se.insert()
		se.submit()
		print(f"  Opening: {item_code} — Qty: {init_qty:,.2f} @ {std_rate:,.2f} → {se.name}")

	frappe.db.commit()


def step_4_jan_purchase_receipts():
	"""Create January Purchase Receipts with actual prices (triggers price variance)."""
	print("\n═══ Step 4: January Purchase Receipts ═══")

	supplier = _get_or_create_supplier()

	for item_code, item_name, init_qty, _, std_rate, jan_qty, jan_val, *_ in PURCHASED_MATERIALS:
		if flt(jan_qty) <= 0:
			continue

		actual_rate = flt(jan_val) / flt(jan_qty)
		variance = (actual_rate - std_rate) * jan_qty

		pr = frappe.get_doc({
			"doctype": "Purchase Receipt",
			"supplier": supplier,
			"company": COMPANY,
			"posting_date": "2020-01-15",
			"items": [{
				"item_code": item_code,
				"qty": jan_qty,
				"rate": actual_rate,
				"warehouse": WAREHOUSE,
			}],
		})
		pr.insert()
		pr.submit()
		pr.reload()

		item_row = pr.items[0]
		print(f"  PR {pr.name}: {item_code}")
		print(f"    Actual Rate: {actual_rate:,.2f} | Std Rate Applied: {flt(item_row.custom_standard_rate_applied):,.2f}")
		print(f"    Qty: {jan_qty:,.2f} | Price Variance: {flt(item_row.custom_price_variance):,.2f}")

	frappe.db.commit()


def step_5_jan_material_issues():
	"""Create January material issues (consumption to production)."""
	print("\n═══ Step 5: January Material Issues ═══")

	for item_code, qty in CONSUMPTION_JAN.items():
		se = frappe.get_doc({
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Issue",
			"company": COMPANY,
			"posting_date": "2020-01-31",
			"items": [{
				"item_code": item_code,
				"qty": qty,
				"s_warehouse": WAREHOUSE,
			}],
		})
		se.insert()
		se.submit()
		se.reload()
		rate = flt(se.items[0].valuation_rate)
		print(f"  Issue {se.name}: {item_code} — Qty: {qty:,.0f} @ {rate:,.2f}")

	frappe.db.commit()


def step_6_create_costing_period():
	"""Create Jan 2020 Costing Period."""
	print("\n═══ Step 6: Create Costing Period (Jan 2020) ═══")

	fy = frappe.db.get_value("Fiscal Year", {"disabled": 0}, "name")

	existing = frappe.db.get_value("Costing Period",
		{"company": COMPANY, "period_start": "2020-01-01"}, "name")
	if existing:
		print(f"  Already exists: {existing}")
		return existing

	cp = frappe.get_doc({
		"doctype": "Costing Period",
		"period_name": "January 2020",
		"company": COMPANY,
		"fiscal_year": fy,
		"period_start": "2020-01-01",
		"period_end": "2020-01-31",
	})
	cp.insert()
	cp.submit()
	print(f"  Created: {cp.name}")
	frappe.db.commit()
	return cp.name


def step_7_plcv_entries(costing_period):
	"""Create PLCV Entries for January — YTD CPU vs Standard Rate variance."""
	print("\n═══ Step 7: PLCV Entries (Jan 2020) ═══")
	print(f"{'Item':<15} {'Init Qty':>12} {'Init Val':>18} {'Purch Qty':>12} {'Purch Val':>18} {'YTD CPU':>12} {'Std Rate':>12} {'Variance/u':>12}")
	print("─" * 115)

	for item_code, item_name, init_qty, init_val, std_rate, jan_qty, jan_val, *_ in PURCHASED_MATERIALS:
		total_qty = flt(init_qty) + flt(jan_qty)
		total_val = flt(init_val) + flt(jan_val)

		if total_qty <= 0:
			continue

		ytd_cpu = total_val / total_qty
		issued_qty = CONSUMPTION_JAN.get(item_code, 0)
		closing_qty = total_qty - issued_qty

		if closing_qty < 0:
			closing_qty = 0
			issued_qty = total_qty

		plcv = frappe.get_doc({
			"doctype": "PLCV Entry",
			"costing_period": costing_period,
			"item_code": item_code,
			"cost_category": "Purchased",
			"opening_qty": init_qty,
			"opening_value": init_val,
			"ytd_purchase_qty": jan_qty,
			"ytd_purchase_value": jan_val,
			"ytd_cost_pool_amount": 0,
			"standard_rate": std_rate,
			"closing_stock_qty": closing_qty,
			"ytd_issued_qty": issued_qty,
		})
		plcv.insert()

		print(f"{item_code:<15} {init_qty:>12,.0f} {init_val:>18,.2f} {jan_qty:>12,.0f} {jan_val:>18,.2f} "
			  f"{flt(plcv.ytd_actual_cpu, 2):>12,.2f} {std_rate:>12,.2f} {flt(plcv.variance_per_unit, 2):>12,.2f}")

		# Verify calculation matches SAP "CPU Jan YTD Stock" column
		print(f"  → Total Var: {flt(plcv.total_variance, 2):,.2f} | "
			  f"COGS Var: {flt(plcv.cogs_variance, 2):,.2f} | "
			  f"Inv Var: {flt(plcv.inventory_variance, 2):,.2f} | "
			  f"Closing: {closing_qty:,.0f} | Issued: {issued_qty:,.0f}")

		plcv.submit()

	frappe.db.commit()


def step_8_standard_cost_revaluation(costing_period):
	"""Standard Cost Revaluation — update standard rates to YTD actual CPU."""
	print("\n═══ Step 8: Standard Cost Revaluation ═══")

	expense_account = frappe.db.get_value("Company", COMPANY, "stock_adjustment_account")
	if not expense_account:
		print("  WARNING: No stock_adjustment_account — skipping revaluation.")
		return

	scr = frappe.get_doc({
		"doctype": "Standard Cost Revaluation",
		"company": COMPANY,
		"posting_date": "2020-01-31",
		"source_type": "PLCV",
		"rate_derivation_method": "YTD",
		"costing_period": costing_period,
		"items": [],
	})

	for item_code, item_name, init_qty, init_val, std_rate, jan_qty, jan_val, *_ in PURCHASED_MATERIALS:
		total_qty = flt(init_qty) + flt(jan_qty)
		total_val = flt(init_val) + flt(jan_val)

		if total_qty <= 0:
			continue

		new_rate = round(total_val / total_qty, 2)
		issued_qty = CONSUMPTION_JAN.get(item_code, 0)
		closing_qty = total_qty - issued_qty

		if closing_qty <= 0 or abs(new_rate - std_rate) < 0.01:
			continue

		scr.append("items", {
			"item_code": item_code,
			"warehouse": WAREHOUSE,
			"current_standard_rate": std_rate,
			"new_standard_rate": new_rate,
			"closing_qty": closing_qty,
		})

	if not scr.items:
		print("  No items need revaluation.")
		return

	scr.insert()
	print(f"\n  Revaluation {scr.name}:")
	for row in scr.items:
		print(f"    {row.item_code}: {flt(row.current_standard_rate):,.2f} → {flt(row.new_standard_rate):,.2f} "
			  f"| Qty: {flt(row.closing_qty):,.0f} | Reval Amt: {flt(row.revaluation_amount):,.2f}")
	print(f"  Total Revaluation Amount: {flt(scr.total_revaluation_amount):,.2f}")

	scr.submit()
	scr.reload()
	print(f"  Stock Reconciliation created: {scr.stock_reconciliation}")
	print(f"  Status: {scr.status}")

	# Verify Item standard_rate was updated
	print("\n  Updated Item Standard Rates:")
	for row in scr.items:
		new_rate = frappe.db.get_value("Item", row.item_code, "standard_rate")
		print(f"    {row.item_code}: {flt(new_rate):,.2f}")

	frappe.db.commit()


def step_9_summary():
	"""Print summary of all test entries created."""
	print("\n═══ SUMMARY ═══")

	# Count documents
	for dt in ["Item", "Standard Cost Rate", "Purchase Receipt", "Stock Entry",
			   "Costing Period", "PLCV Entry", "Standard Cost Revaluation", "Stock Reconciliation"]:
		count = len(frappe.get_all(dt, limit=0))
		print(f"  {dt}: {count} total records")

	# Show SLE for one item
	print("\n  Sample SLE for RM-120002 (Pouzzolana):")
	sles = frappe.get_all("Stock Ledger Entry",
		filters={"item_code": "RM-120002"},
		fields=["posting_date", "voucher_type", "voucher_no", "actual_qty", "incoming_rate",
				"stock_value", "valuation_rate"],
		order_by="posting_date, creation",
		limit=10,
	)
	for sle in sles:
		print(f"    {sle.posting_date} | {sle.voucher_type:<25} | Qty: {flt(sle.actual_qty):>12,.2f} "
			  f"| Rate: {flt(sle.incoming_rate):>12,.2f} | Value: {flt(sle.stock_value):>18,.2f}")

	# Show GL entries for price variance
	print("\n  Price Variance GL (from Purchase Receipts):")
	pr_names = frappe.get_all("Purchase Receipt",
		filters={"company": COMPANY, "posting_date": (">=", "2020-01-01")},
		pluck="name", limit=5)
	for pr_name in pr_names:
		pr = frappe.get_doc("Purchase Receipt", pr_name)
		for item in pr.items:
			if flt(item.custom_price_variance) != 0:
				print(f"    {pr_name} | {item.item_code} | Variance: {flt(item.custom_price_variance):,.2f}")


def _get_or_create_supplier():
	name = "Test Supplier Costing"
	if not frappe.db.exists("Supplier", name):
		sg = frappe.db.get_value("Supplier Group", {}, "name")
		frappe.get_doc({
			"doctype": "Supplier",
			"supplier_name": name,
			"supplier_group": sg,
		}).insert()
		frappe.db.commit()
	return name


def execute():
	frappe.set_user("Administrator")
	get_company()

	step_0_cleanup()
	step_1_create_items()
	step_2_create_standard_cost_rates()
	step_3_create_opening_stock()
	step_4_jan_purchase_receipts()
	step_5_jan_material_issues()
	costing_period = step_6_create_costing_period()
	step_7_plcv_entries(costing_period)
	step_8_standard_cost_revaluation(costing_period)
	step_9_summary()

	print("\n✓ Full January 2020 costing cycle completed successfully!")


execute()
