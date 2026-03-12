import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters):
	columns = [
		{
			"fieldname": "cost_element",
			"label": _("Cost Element"),
			"fieldtype": "Link",
			"options": "Cost Element",
			"width": 200,
		},
		{
			"fieldname": "cost_element_name",
			"label": _("Description"),
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"fieldname": "cost_element_type",
			"label": _("Type"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "cost_center",
			"label": _("Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center",
			"width": 200,
		},
		{
			"fieldname": "primary_amount",
			"label": _("Primary Amount"),
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"fieldname": "allocated_in",
			"label": _("Allocated In"),
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"fieldname": "allocated_out",
			"label": _("Allocated Out"),
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"fieldname": "net_balance",
			"label": _("Net Balance"),
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"fieldname": "pct_of_total",
			"label": _("% of Total"),
			"fieldtype": "Percent",
			"width": 100,
		},
	]
	return columns


def get_data(filters):
	if not filters:
		filters = {}

	period = filters.get("period")
	if not period:
		return []

	cost_center_filter = filters.get("cost_center")
	show_detail = filters.get("show_detail")

	conditions = "doc.docstatus = 1 AND doc.period = %(period)s"
	params = {"period": period}

	if cost_center_filter:
		conditions += " AND line.cost_center = %(cost_center)s"
		params["cost_center"] = cost_center_filter

	# Get all CO Document Lines grouped by cost element and cost center
	query = f"""
		SELECT
			doc.cost_element,
			ce.cost_element_name,
			ce.cost_element_type,
			line.cost_center,
			doc.co_document_type,
			SUM(line.debit_amount) as total_debit,
			SUM(line.credit_amount) as total_credit
		FROM `tabCO Document Line` line
		JOIN `tabCO Document` doc ON doc.name = line.parent
		LEFT JOIN `tabCost Element` ce ON ce.name = doc.cost_element
		WHERE {conditions}
		GROUP BY doc.cost_element, line.cost_center, doc.co_document_type
		ORDER BY ce.cost_element_type, doc.cost_element, line.cost_center
	"""

	raw_data = frappe.db.sql(query, params, as_dict=True)

	if not raw_data:
		return []

	# Aggregate by cost element and cost center
	from collections import defaultdict

	agg = defaultdict(lambda: {
		"primary_amount": 0,
		"allocated_in": 0,
		"allocated_out": 0,
		"cost_element_name": "",
		"cost_element_type": "",
	})

	for row in raw_data:
		key = (row.cost_element, row.cost_center) if show_detail else (row.cost_element, None)
		entry = agg[key]
		entry["cost_element_name"] = row.cost_element_name
		entry["cost_element_type"] = row.cost_element_type

		net = flt(row.total_debit) - flt(row.total_credit)

		if row.co_document_type == "Primary Mirror":
			entry["primary_amount"] += net
		elif net > 0:
			entry["allocated_in"] += net
		else:
			entry["allocated_out"] += abs(net)

	# Calculate total for percentage
	grand_total = sum(
		abs(v["primary_amount"] + v["allocated_in"] - v["allocated_out"])
		for v in agg.values()
	)

	data = []
	for (cost_element, cost_center), vals in sorted(agg.items()):
		net_balance = vals["primary_amount"] + vals["allocated_in"] - vals["allocated_out"]
		pct = (abs(net_balance) / grand_total * 100) if grand_total else 0

		data.append({
			"cost_element": cost_element,
			"cost_element_name": vals["cost_element_name"],
			"cost_element_type": vals["cost_element_type"],
			"cost_center": cost_center or "",
			"primary_amount": vals["primary_amount"],
			"allocated_in": vals["allocated_in"],
			"allocated_out": vals["allocated_out"],
			"net_balance": net_balance,
			"pct_of_total": pct,
		})

	return data
