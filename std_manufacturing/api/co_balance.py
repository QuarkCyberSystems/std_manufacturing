import frappe
from frappe import _
from frappe.utils import flt


def get_co_cc_balance(cost_center, period):
	"""Get net CO balance (debit - credit) for a cost center in a period.

	Considers only submitted CO Documents.
	"""
	result = frappe.db.sql(
		"""
		SELECT
			COALESCE(SUM(line.debit_amount), 0) - COALESCE(SUM(line.credit_amount), 0) as net_balance
		FROM `tabCO Document Line` line
		JOIN `tabCO Document` doc ON doc.name = line.parent
		WHERE doc.docstatus = 1
			AND doc.period = %s
			AND line.cost_center = %s
		""",
		(period, cost_center),
		as_dict=True,
	)
	return flt(result[0].net_balance) if result else 0


def get_co_cc_balance_by_type(cost_center, period, co_document_type=None):
	"""Get net CO balance filtered by document type."""
	conditions = "doc.docstatus = 1 AND doc.period = %s AND line.cost_center = %s"
	params = [period, cost_center]

	if co_document_type:
		conditions += " AND doc.co_document_type = %s"
		params.append(co_document_type)

	result = frappe.db.sql(
		f"""
		SELECT
			COALESCE(SUM(line.debit_amount), 0) - COALESCE(SUM(line.credit_amount), 0) as net_balance
		FROM `tabCO Document Line` line
		JOIN `tabCO Document` doc ON doc.name = line.parent
		WHERE {conditions}
		""",
		tuple(params),
		as_dict=True,
	)
	return flt(result[0].net_balance) if result else 0


def get_co_cc_balance_for_costing(cost_center, period):
	"""Get the CC balance for production costing purposes.

	This excludes outbound chain allocation credits (where this CC is the sender
	in a Production Ratio allocation cycle). This way, each production step
	retains its accumulated cost for unit cost calculation, even after
	downstream chain allocations have run.

	The balance includes:
	- Primary Mirror (direct GL costs)
	- Assessment / Distribution debits (costs received from support CCs)
	- But EXCLUDES credits from downstream chain allocations
	"""
	# Get allocation cycles where this CC is the sender (outbound chain)
	outbound_cycles = frappe.get_all(
		"Allocation Cycle",
		filters={
			"sender_cost_center": cost_center,
			"is_active": 1,
		},
		pluck="name",
	)

	if not outbound_cycles:
		# No outbound allocations - use standard balance
		return get_co_cc_balance(cost_center, period)

	# Get CO Documents created by those outbound allocation cycles
	# These are the ones where this CC was credited (cost sent out)
	outbound_co_docs = frappe.get_all(
		"CO Document",
		filters={
			"period": period,
			"docstatus": 1,
			"reference_doctype": "Allocation Cycle",
			"reference_name": ("in", outbound_cycles),
		},
		pluck="name",
	)

	if not outbound_co_docs:
		return get_co_cc_balance(cost_center, period)

	# Get full balance minus the outbound allocation credits
	result = frappe.db.sql(
		"""
		SELECT
			COALESCE(SUM(line.debit_amount), 0) - COALESCE(SUM(line.credit_amount), 0) as net_balance
		FROM `tabCO Document Line` line
		JOIN `tabCO Document` doc ON doc.name = line.parent
		WHERE doc.docstatus = 1
			AND doc.period = %s
			AND line.cost_center = %s
			AND doc.name NOT IN %s
		""",
		(period, cost_center, outbound_co_docs),
		as_dict=True,
	)
	return flt(result[0].net_balance) if result else 0


def get_skf_entry_value(skf, period, cost_center):
	"""Get submitted SKF Entry quantity for a specific SKF/period/cost center."""
	result = frappe.db.get_value(
		"SKF Entry",
		{"skf": skf, "period": period, "cost_center": cost_center, "docstatus": 1},
		"quantity",
	)
	return flt(result)


def get_skf_total_for_period(skf, period):
	"""Get sum of all submitted SKF Entry quantities for an SKF/period."""
	result = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(quantity), 0) as total
		FROM `tabSKF Entry`
		WHERE skf = %s AND period = %s AND docstatus = 1
		""",
		(skf, period),
		as_dict=True,
	)
	return flt(result[0].total) if result else 0


@frappe.whitelist()
def run_primary_co_mirror(costing_period):
	"""Mirror GL Entries to CO Documents for a costing period.

	Reads GL Entries within the period date range that have a cost center and
	whose account is mapped to a Cost Element. Creates one CO Document per
	GL Entry with matching debit/credit lines.
	"""
	period_doc = frappe.get_doc("Costing Period", costing_period)

	if period_doc.docstatus != 1:
		frappe.throw(_("Costing Period must be submitted before running Primary Mirror"))

	# Check if already done
	existing_count = frappe.db.count(
		"CO Document",
		{"period": costing_period, "co_document_type": "Primary Mirror", "docstatus": 1},
	)
	if existing_count > 0:
		frappe.throw(
			_("Primary Mirror already has {0} CO Documents for this period. Cancel them first.").format(
				existing_count
			)
		)

	company = period_doc.company
	start_date = period_doc.period_start
	end_date = period_doc.period_end

	# Get all GL Entries with cost centers in the period
	gl_entries = frappe.db.sql(
		"""
		SELECT
			gle.name, gle.account, gle.cost_center, gle.debit, gle.credit,
			gle.posting_date, gle.voucher_type, gle.voucher_no,
			acc.custom_cost_element
		FROM `tabGL Entry` gle
		LEFT JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE gle.company = %s
			AND gle.posting_date BETWEEN %s AND %s
			AND gle.cost_center IS NOT NULL
			AND gle.cost_center != ''
			AND gle.is_cancelled = 0
			AND acc.custom_cost_element IS NOT NULL
			AND acc.custom_cost_element != ''
			AND gle.voucher_type NOT IN ('Stock Entry', 'Purchase Receipt')
		ORDER BY gle.posting_date, gle.name
		""",
		(company, start_date, end_date),
		as_dict=True,
	)

	if not gl_entries:
		frappe.msgprint(_("No GL Entries with mapped Cost Elements found in this period"))
		return 0

	co_doc_count = 0

	# Get clearing cost center for CO balancing
	clearing_cc = frappe.db.get_single_value("Controlling Settings", "co_clearing_cost_center")
	if not clearing_cc:
		# Use the company's main/root cost center as clearing
		clearing_cc = frappe.db.get_value(
			"Cost Center", {"company": company, "is_group": 1, "parent_cost_center": ("in", ["", None])}, "name"
		)
		if not clearing_cc:
			clearing_cc = frappe.db.get_value(
				"Cost Center", {"company": company, "is_group": 1}, "name"
			)

	# Group GL entries by voucher + cost element for consolidated CO Documents
	from collections import defaultdict

	voucher_groups = defaultdict(list)
	for gle in gl_entries:
		key = (gle.voucher_type, gle.voucher_no, gle.custom_cost_element)
		voucher_groups[key].append(gle)

	for (voucher_type, voucher_no, cost_element), entries in voucher_groups.items():
		co_doc = frappe.new_doc("CO Document")
		co_doc.co_document_type = "Primary Mirror"
		co_doc.company = company
		co_doc.cost_element = cost_element
		co_doc.period = costing_period
		co_doc.posting_date = entries[0].posting_date
		co_doc.reference_doctype = voucher_type
		co_doc.reference_name = voucher_no
		co_doc.remarks = f"Primary Mirror from {voucher_type} {voucher_no}"

		total_debit = 0
		total_credit = 0
		for gle in entries:
			co_doc.append(
				"lines",
				{
					"cost_center": gle.cost_center,
					"debit_amount": flt(gle.debit),
					"credit_amount": flt(gle.credit),
				},
			)
			total_debit += flt(gle.debit)
			total_credit += flt(gle.credit)

		# Balance the CO Document using a clearing line
		net = flt(total_debit - total_credit, 2)
		if net > 0:
			co_doc.append("lines", {
				"cost_center": clearing_cc,
				"debit_amount": 0,
				"credit_amount": net,
			})
		elif net < 0:
			co_doc.append("lines", {
				"cost_center": clearing_cc,
				"debit_amount": abs(net),
				"credit_amount": 0,
			})

		try:
			co_doc.insert(ignore_permissions=True)
			co_doc.submit()
			co_doc_count += 1
		except Exception:
			frappe.log_error(
				title=f"Primary Mirror Error: {voucher_type} {voucher_no}",
			)

	frappe.db.commit()
	frappe.msgprint(_("{0} CO Documents created from Primary Mirror").format(co_doc_count))
	return co_doc_count


@frappe.whitelist()
def run_fuel_revaluation(costing_period):
	"""Book fuel consumed in power generation at YTD CPU to Power CC.

	Since Stock Entry GL entries are excluded from Primary Mirror,
	fuel consumption cost must be added to the Power CC via CO Documents.
	This books the full consumption cost: consumed_qty × YTD_CPU.

	SAP revalues HFO and LFO consumed in power generation using the current
	YTD actual CPU. This adds a significant amount to the Power CC (R10100900P),
	which then gets allocated via KWH.
	"""
	from std_manufacturing.api.process_order import get_item_ytd_cpu

	period_doc = frappe.get_doc("Costing Period", costing_period)

	# Check if already done
	existing = frappe.db.count(
		"CO Document",
		{"period": costing_period, "co_document_type": "Primary Mirror",
		 "remarks": ("like", "%Fuel Cost%"), "docstatus": 1},
	)
	if existing > 0:
		frappe.msgprint(_("Fuel Revaluation already run for this period"))
		return 0

	# Get fuel consumption from demo data
	try:
		from std_manufacturing.demo_setup import POWER_FUEL_CONSUMPTION, CEMENT_FUEL_CONSUMPTION, cc as cc_fn
		power_cc = cc_fn("R10100900P")
		cement_mill_cc = cc_fn("R101P0400D")
	except ImportError:
		frappe.throw(_("Could not import fuel consumption data"))
		return 0

	company = period_doc.company
	month_idx = 0 if period_doc.period_start.month == 1 else 1

	# Get clearing cost center
	clearing_cc = frappe.db.get_value(
		"Cost Center", {"company": company, "is_group": 1, "parent_cost_center": ("in", ["", None])}, "name"
	)
	if not clearing_cc:
		clearing_cc = frappe.db.get_value("Cost Center", {"company": company, "is_group": 1}, "name")

	total_reval = 0
	co_docs_created = 0

	# Combine fuel consumption: (item_code, qty_tuple, target_cc)
	all_fuel = []
	for item_code, qty_tuple in POWER_FUEL_CONSUMPTION.items():
		all_fuel.append((item_code, qty_tuple, power_cc))
	for item_code, qty_tuple in CEMENT_FUEL_CONSUMPTION.items():
		all_fuel.append((item_code, qty_tuple, cement_mill_cc))

	for item_code, (jan_qty, feb_qty), target_cc in all_fuel:
		# Current period consumed qty only (not YTD)
		period_qty = jan_qty if month_idx == 0 else feb_qty

		if flt(period_qty) <= 0:
			continue

		# Get YTD CPU for this fuel
		ytd_cpu = get_item_ytd_cpu(item_code, period_doc)

		# Period consumption cost at YTD CPU
		fuel_cost = flt(period_qty) * flt(ytd_cpu)
		if abs(fuel_cost) < 0.01:
			continue

		total_reval += fuel_cost

		# Ensure CE-FUEL-REVAL exists
		if not frappe.db.exists("Cost Element", "CE-FUEL-REVAL"):
			ce = frappe.new_doc("Cost Element")
			ce.cost_element_code = "CE-FUEL-REVAL"
			ce.cost_element_name = "Fuel Revaluation"
			ce.cost_element_type = "Secondary"
			ce.secondary_category = "Assessment"
			ce.status = "Active"
			ce.insert(ignore_permissions=True)

		# Create CO Document debiting Power CC with fuel cost
		co_doc = frappe.new_doc("CO Document")
		co_doc.co_document_type = "Primary Mirror"
		co_doc.company = company
		co_doc.cost_element = "CE-FUEL-REVAL"
		co_doc.period = costing_period
		co_doc.posting_date = period_doc.period_end
		co_doc.remarks = f"Fuel Cost {item_code}: {period_qty:,.2f} × {ytd_cpu:,.2f}"

		co_doc.append("lines", {
			"cost_center": target_cc,
			"debit_amount": fuel_cost,
			"credit_amount": 0,
		})
		co_doc.append("lines", {
			"cost_center": clearing_cc,
			"debit_amount": 0,
			"credit_amount": fuel_cost,
		})

		co_doc.insert(ignore_permissions=True)
		co_doc.submit()
		co_docs_created += 1

	frappe.db.commit()
	frappe.msgprint(
		_("Fuel Revaluation: {0} CO Documents created, total revaluation: {1}").format(
			co_docs_created, frappe.format_value(total_reval, {"fieldtype": "Currency"})
		)
	)
	return co_docs_created
