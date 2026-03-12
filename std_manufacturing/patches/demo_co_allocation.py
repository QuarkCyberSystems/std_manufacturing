"""
End-to-End Demo: CO Sub-Ledger + Allocation Engine

Builds on the existing test data (9 purchased materials, Jan 2020 Costing Period)
and adds:
  1. Primary Cost Elements mapped to GL Accounts
  2. Journal Entries posting expenses to cost centers (simulating monthly costs)
  3. Primary Mirror (GL → CO Documents)
  4. Power Production Record (KWH consumption)
  5. Allocation Run (13 cycles)
  6. Prints Cost Drilldown summary

Run with:
  bench --site badia.localhost execute std_manufacturing.patches.demo_co_allocation.execute
"""

import frappe
from frappe.utils import flt

COMPANY = None
COMPANY_ABBR = None
PERIOD_NAME = "CP-BCP-2020-01-01"  # existing Costing Period


def get_company():
	global COMPANY, COMPANY_ABBR
	COMPANY = frappe.db.get_single_value("Global Defaults", "default_company")
	if not COMPANY:
		COMPANY = frappe.db.get_value("Company", {}, "name")
	COMPANY_ABBR = frappe.db.get_value("Company", COMPANY, "abbr")
	print(f"Company: {COMPANY} ({COMPANY_ABBR})")


def execute():
	get_company()

	print("\n" + "=" * 70)
	print("DEMO: CO Sub-Ledger + Allocation Engine")
	print("=" * 70)

	ensure_fiscal_year_2020()
	step_0_cleanup()
	step_1_create_primary_cost_elements()
	step_2_create_journal_entries()
	step_3_run_primary_mirror()
	step_4_create_power_production()
	step_5_run_allocation()
	step_6_print_summary()

	frappe.db.commit()
	print("\n" + "=" * 70)
	print("DEMO COMPLETE")
	print("=" * 70)


def ensure_fiscal_year_2020():
	"""Create fiscal year 2020 if it doesn't exist (needed for Jan 2020 JEs)."""
	if not frappe.db.exists("Fiscal Year", "2020"):
		fy = frappe.new_doc("Fiscal Year")
		fy.year = "2020"
		fy.year_start_date = "2020-01-01"
		fy.year_end_date = "2020-12-31"
		fy.insert(ignore_permissions=True)
		print("  Created Fiscal Year 2020")
	else:
		# Ensure it's not disabled
		frappe.db.set_value("Fiscal Year", "2020", "disabled", 0)


def step_0_cleanup():
	"""Remove any previous demo CO data."""
	print("\n--- Step 0: Cleanup previous demo data ---")

	# Cancel and delete Allocation Runs
	for name in frappe.get_all("Allocation Run", filters={"docstatus": 1}, pluck="name"):
		doc = frappe.get_doc("Allocation Run", name)
		doc.cancel()
	for name in frappe.get_all("Allocation Run", pluck="name"):
		frappe.delete_doc("Allocation Run", name, force=True)

	# Cancel and delete CO Documents
	for name in frappe.get_all("CO Document", filters={"docstatus": 1}, pluck="name", order_by="creation desc"):
		doc = frappe.get_doc("CO Document", name)
		doc.cancel()
	for name in frappe.get_all("CO Document", pluck="name"):
		frappe.delete_doc("CO Document", name, force=True)

	# Cancel and delete Power Production Records
	for name in frappe.get_all("Power Production Record", filters={"docstatus": 1}, pluck="name"):
		doc = frappe.get_doc("Power Production Record", name)
		doc.cancel()
	for name in frappe.get_all("Power Production Record", pluck="name"):
		frappe.delete_doc("Power Production Record", name, force=True)

	# Cancel and delete SKF Entries
	for name in frappe.get_all("SKF Entry", filters={"docstatus": 1}, pluck="name"):
		doc = frappe.get_doc("SKF Entry", name)
		doc.cancel()
	for name in frappe.get_all("SKF Entry", pluck="name"):
		frappe.delete_doc("SKF Entry", name, force=True)

	# Delete demo Journal Entries (tagged with "CO-DEMO")
	for name in frappe.get_all("Journal Entry", filters={"docstatus": 1, "user_remark": ("like", "%CO-DEMO%")}, pluck="name"):
		doc = frappe.get_doc("Journal Entry", name)
		doc.cancel()
	for name in frappe.get_all("Journal Entry", filters={"user_remark": ("like", "%CO-DEMO%")}, pluck="name"):
		frappe.delete_doc("Journal Entry", name, force=True)

	# Reset Costing Period statuses
	if frappe.db.exists("Costing Period", PERIOD_NAME):
		frappe.db.set_value("Costing Period", PERIOD_NAME, {
			"primary_mirror_status": "Pending",
			"power_status": "Pending",
			"allocation_status": "Pending",
			"current_step": 1,
		})

	frappe.db.commit()
	print("  Cleanup complete.")


# ──────────────────────────────────────────────────────────────
# GL Account → Cost Element mapping
# ──────────────────────────────────────────────────────────────
ACCOUNT_CE_MAP = [
	# (gl_account_suffix, cost_element_code, cost_element_name)
	("Cost of Goods Sold", "CE-COGS", "Cost of Goods Sold"),
	("Depreciation", "CE-DEPR", "Depreciation"),
	("Salary", "CE-LABOR", "Labor & Salary"),
	("Utility Expenses", "CE-UTIL", "Utility Expenses"),
	("Office Maintenance Expenses", "CE-MAINT", "Maintenance Expenses"),
	("Administrative Expenses", "CE-ADMIN", "Administrative Expenses"),
	("Freight and Forwarding Charges", "CE-FREIGHT", "Freight & Forwarding"),
	("Miscellaneous Expenses", "CE-MISC", "Miscellaneous Expenses"),
]


def step_1_create_primary_cost_elements():
	"""Create Primary Cost Elements and map them to GL Accounts."""
	print("\n--- Step 1: Create Primary Cost Elements ---")

	for acct_suffix, ce_code, ce_name in ACCOUNT_CE_MAP:
		gl_account = f"{acct_suffix} - {COMPANY_ABBR}"
		if not frappe.db.exists("Account", gl_account):
			print(f"  Skipping {gl_account} — not found")
			continue

		# Create or update Cost Element
		if not frappe.db.exists("Cost Element", ce_code):
			ce = frappe.new_doc("Cost Element")
			ce.cost_element_code = ce_code
			ce.cost_element_name = ce_name
			ce.cost_element_type = "Primary"
			ce.gl_account = gl_account
			ce.status = "Active"
			ce.insert(ignore_permissions=True)
			print(f"  Created CE: {ce_code} → {gl_account}")
		else:
			frappe.db.set_value("Cost Element", ce_code, "gl_account", gl_account)
			print(f"  Updated CE: {ce_code} → {gl_account}")

		# Map GL Account → Cost Element via custom field
		frappe.db.set_value("Account", gl_account, "custom_cost_element", ce_code)

	frappe.db.commit()


# ──────────────────────────────────────────────────────────────
# Journal Entries: monthly expenses posted to cost centers
# From SAP Costing Cycle.xlsx — OH/Maintenance CC amounts (Jan 2020)
# ──────────────────────────────────────────────────────────────
# (cost_center_name, expense_account_suffix, amount, description)
MONTHLY_EXPENSES = [
	# Depreciation (62% of production cost) — allocated across production CCs
	("Quarry Operations", "Depreciation", 850000, "Quarry equipment depreciation"),
	("Crusher", "Depreciation", 1200000, "Crusher machinery depreciation"),
	("Raw Mill", "Depreciation", 1800000, "Raw Mill depreciation"),
	("Coal Mill", "Depreciation", 600000, "Coal Mill depreciation"),
	("Kiln", "Depreciation", 3500000, "Kiln depreciation"),
	("Cement Mill", "Depreciation", 2200000, "Cement Mill depreciation"),
	("Packing", "Depreciation", 450000, "Packing line depreciation"),

	# Maintenance costs at support cost centers
	("Workshop Maintenance", "Office Maintenance Expenses", 2800000, "Workshop labor & parts"),
	("Electrical Maintenance", "Office Maintenance Expenses", 1900000, "Electrical maintenance"),
	("Civil Maintenance", "Office Maintenance Expenses", 950000, "Civil maintenance"),
	("Heavy Equipment", "Office Maintenance Expenses", 1600000, "Heavy equipment maintenance"),

	# Labor/salary at support CCs
	("Laboratory", "Salary", 750000, "Lab staff salaries"),
	("Plant Administration", "Salary", 1200000, "Plant admin salaries"),
	("Safety", "Salary", 400000, "Safety team salaries"),
	("Stores", "Salary", 350000, "Stores staff salaries"),

	# Power plant running costs
	("Power Plant", "Utility Expenses", 8500000, "HFO/LFO fuel + generator maintenance"),
	("Water Treatment", "Utility Expenses", 450000, "Water treatment chemicals & power"),

	# Admin & overhead
	("Production Overhead", "Administrative Expenses", 500000, "Production overhead allocation base"),
	("Maintenance Overhead", "Administrative Expenses", 300000, "Maintenance overhead"),
	("Admin Overhead", "Administrative Expenses", 400000, "Admin overhead"),

	# Commercial
	("Sales and Distribution", "Freight and Forwarding Charges", 2100000, "Cement distribution freight"),
	("General Administration", "Miscellaneous Expenses", 600000, "General admin expenses"),
]


def step_2_create_journal_entries():
	"""Create Journal Entries posting monthly expenses to cost centers.

	These generate GL Entries that the Primary Mirror will pick up.
	"""
	print("\n--- Step 2: Create Journal Entries (monthly expenses) ---")

	# Find a suitable bank/cash account for the credit side
	bank_account = frappe.db.get_value(
		"Account",
		{"account_type": "Bank", "is_group": 0, "company": COMPANY},
		"name",
	)
	if not bank_account:
		bank_account = frappe.db.get_value(
			"Account",
			{"account_type": "Cash", "is_group": 0, "company": COMPANY},
			"name",
		)
	if not bank_account:
		# Create a temporary bank account
		bank_account = f"Demo Bank Account - {COMPANY_ABBR}"
		if not frappe.db.exists("Account", bank_account):
			ba = frappe.new_doc("Account")
			ba.account_name = "Demo Bank Account"
			ba.company = COMPANY
			ba.parent_account = f"Bank Accounts - {COMPANY_ABBR}"
			ba.account_type = "Bank"
			ba.insert(ignore_permissions=True)
			print(f"  Created bank account: {bank_account}")

	total_posted = 0
	je_count = 0

	for cc_name, acct_suffix, amount, desc in MONTHLY_EXPENSES:
		cost_center = f"{cc_name} - {COMPANY_ABBR}"
		expense_account = f"{acct_suffix} - {COMPANY_ABBR}"

		if not frappe.db.exists("Cost Center", cost_center):
			print(f"  Skipping: CC {cost_center} not found")
			continue
		if not frappe.db.exists("Account", expense_account):
			print(f"  Skipping: Account {expense_account} not found")
			continue

		je = frappe.new_doc("Journal Entry")
		je.posting_date = "2020-01-31"
		je.company = COMPANY
		je.user_remark = f"CO-DEMO: {desc}"

		# ERPNext requires Depreciation Entry type for depreciation account
		acct_type = frappe.db.get_value("Account", expense_account, "account_type")
		if acct_type == "Depreciation":
			je.voucher_type = "Depreciation Entry"

		# Debit: expense account with cost center
		je.append("accounts", {
			"account": expense_account,
			"cost_center": cost_center,
			"debit_in_account_currency": amount,
			"credit_in_account_currency": 0,
		})

		# Credit: bank account (no cost center)
		je.append("accounts", {
			"account": bank_account,
			"debit_in_account_currency": 0,
			"credit_in_account_currency": amount,
		})

		try:
			je.insert(ignore_permissions=True)
			je.submit()
			total_posted += amount
			je_count += 1
		except Exception as e:
			print(f"  Error posting JE for {cc_name}/{acct_suffix}: {e}")
			frappe.db.rollback()

	print(f"  Created {je_count} Journal Entries, total: {total_posted:,.2f}")


def step_3_run_primary_mirror():
	"""Run Primary Mirror to create CO Documents from GL Entries."""
	print("\n--- Step 3: Run Primary Mirror (GL → CO Documents) ---")

	if not frappe.db.exists("Costing Period", PERIOD_NAME):
		print("  ERROR: Costing Period not found. Run test_costing_cycle.py first.")
		return

	from std_manufacturing.api.co_balance import run_primary_co_mirror

	count = run_primary_co_mirror(PERIOD_NAME)
	if count:
		frappe.db.set_value("Costing Period", PERIOD_NAME, "primary_mirror_status", "Completed")
		frappe.db.set_value("Costing Period", PERIOD_NAME, "current_step", 2)
	print(f"  Created {count} CO Documents from Primary Mirror")


def step_4_create_power_production():
	"""Create Power Production Record with KWH data from SAP reference."""
	print("\n--- Step 4: Create Power Production Record (KWH) ---")

	# KWH consumption from SAP Costing Cycle.xlsx
	KWH_DATA = [
		("Crusher", 1498770),
		("Raw Mill", 5847390),
		("Coal Mill", 1282330),
		("Kiln", 2318930),
		("Cement Mill", 8773360),
		("Packing", 724790),
		("Water Treatment", 312440),
	]

	total_generated = 21843180  # Total KWH generated by power plant
	general_service_cc = f"Plant Administration - {COMPANY_ABBR}"

	ppr = frappe.new_doc("Power Production Record")
	ppr.costing_period = PERIOD_NAME
	ppr.total_kwh_generated = total_generated
	ppr.dewa_kwh_purchased = 0
	ppr.general_service_cc = general_service_cc

	for cc_name, kwh in KWH_DATA:
		cc = f"{cc_name} - {COMPANY_ABBR}"
		ppr.append("kwh_consumption_table", {
			"cost_center": cc,
			"kwh_consumed": kwh,
		})

	ppr.insert(ignore_permissions=True)
	ppr.submit()

	frappe.db.set_value("Costing Period", PERIOD_NAME, "power_status", "KWH Posted")
	print(f"  Power Production Record: {ppr.name}")
	print(f"  Total generated: {total_generated:,.0f} KWH")
	print(f"  Total consumed: {ppr.total_kwh_consumed:,.0f} KWH")
	print(f"  General service: {ppr.general_service_kwh:,.0f} KWH → {general_service_cc}")
	print(f"  SKF Entries created: {frappe.db.count('SKF Entry', {'docstatus': 1})}")


def step_5_run_allocation():
	"""Run the allocation engine — 13 cycles."""
	print("\n--- Step 5: Run Allocation Engine (13 Cycles) ---")

	from std_manufacturing.api.allocation_engine import execute_allocation_run

	run_name = execute_allocation_run(PERIOD_NAME)

	frappe.db.set_value("Costing Period", PERIOD_NAME, "allocation_status", "Completed")
	frappe.db.set_value("Costing Period", PERIOD_NAME, "current_step", 4)

	# Print cycle results
	run = frappe.get_doc("Allocation Run", run_name)
	print(f"\n  Allocation Run: {run.name}")
	print(f"  Status: {run.status}")
	print(f"  Cycles executed: {run.total_cycles_executed}")
	print(f"  Total allocated: {run.total_amount_allocated:,.2f}")
	print()
	print(f"  {'#':>3} {'Cycle':<30} {'Sender CC':<30} {'Balance':>15} {'Allocated':>15} {'Status':<10}")
	print(f"  {'─' * 3} {'─' * 30} {'─' * 30} {'─' * 15} {'─' * 15} {'─' * 10}")
	for row in run.cycle_results:
		print(
			f"  {row.cycle_number:>3} {row.cycle_name:<30} "
			f"{(row.sender_cost_center or '')[:30]:<30} "
			f"{flt(row.sender_balance):>15,.2f} "
			f"{flt(row.amount_allocated):>15,.2f} "
			f"{row.status:<10}"
		)


def step_6_print_summary():
	"""Print a summary of the CO sub-ledger state."""
	print("\n--- Step 6: Cost Drilldown Summary ---")

	from std_manufacturing.api.co_balance import get_co_cc_balance

	# Get all production cost centers and their final balances
	production_ccs = [
		"Quarry Operations", "Crusher", "Raw Mill", "Coal Mill",
		"Kiln", "Cement Mill", "Packing",
	]

	print(f"\n  {'Cost Center':<30} {'Net Balance':>15}")
	print(f"  {'─' * 30} {'─' * 15}")

	total = 0
	for cc_name in production_ccs:
		cc = f"{cc_name} - {COMPANY_ABBR}"
		balance = get_co_cc_balance(cc, PERIOD_NAME)
		print(f"  {cc_name:<30} {balance:>15,.2f}")
		total += balance

	print(f"  {'─' * 30} {'─' * 15}")
	print(f"  {'Total Production':.<30} {total:>15,.2f}")

	# Support CCs should be zero (fully allocated)
	print(f"\n  Support Cost Centers (should be 0 after allocation):")
	support_ccs = [
		"Workshop Maintenance", "Electrical Maintenance", "Civil Maintenance",
		"Heavy Equipment", "Power Plant", "Water Treatment", "Laboratory",
		"Plant Administration",
	]
	for cc_name in support_ccs:
		cc = f"{cc_name} - {COMPANY_ABBR}"
		balance = get_co_cc_balance(cc, PERIOD_NAME)
		status = "✓" if abs(balance) < 0.01 else f"!! {balance:,.2f}"
		print(f"  {cc_name:<30} {status}")

	# Summary counts
	print(f"\n  Document Counts:")
	print(f"    CO Documents: {frappe.db.count('CO Document', {'docstatus': 1, 'period': PERIOD_NAME})}")
	print(f"    SKF Entries:  {frappe.db.count('SKF Entry', {'docstatus': 1})}")
	print(f"    GL Entries (Jan 2020): {frappe.db.count('GL Entry', {'is_cancelled': 0, 'posting_date': ['between', ['2020-01-01', '2020-01-31']]})}")
