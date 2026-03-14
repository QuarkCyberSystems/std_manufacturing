import frappe
from frappe import _
from frappe.utils import flt
from collections import defaultdict, OrderedDict


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	chart = get_chart(data)
	report_summary = get_report_summary(data)
	return columns, data, None, chart, report_summary


def get_columns(filters):
	return [
		{
			"fieldname": "label",
			"label": _("Cost Center / Source"),
			"fieldtype": "Data",
			"width": 350,
		},
		{
			"fieldname": "primary_amount",
			"label": _("Primary Cost"),
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


def get_data(filters):
	if not filters:
		filters = {}

	period = filters.get("period")
	if not period:
		return []

	cost_center_filter = filters.get("cost_center")

	# ── 1. Fetch all CO Document Lines for the period ──
	conditions = "doc.docstatus = 1 AND doc.period = %(period)s"
	params = {"period": period}

	if cost_center_filter:
		conditions += " AND line.cost_center = %(cost_center)s"
		params["cost_center"] = cost_center_filter

	raw = frappe.db.sql(
		f"""
		SELECT
			line.cost_center,
			doc.co_document_type,
			doc.cost_element,
			ce.cost_element_name,
			doc.remarks,
			SUM(line.debit_amount) as total_debit,
			SUM(line.credit_amount) as total_credit
		FROM `tabCO Document Line` line
		JOIN `tabCO Document` doc ON doc.name = line.parent
		LEFT JOIN `tabCost Element` ce ON ce.name = doc.cost_element
		WHERE {conditions}
		GROUP BY line.cost_center, doc.co_document_type, doc.cost_element, doc.remarks
		ORDER BY line.cost_center, doc.co_document_type, doc.cost_element
		""",
		params,
		as_dict=True,
	)

	if not raw:
		return []

	# ── 2. Build cost center hierarchy ──
	cc_hierarchy = _get_cost_center_hierarchy(cost_center_filter)

	# ── 3. Aggregate per cost center → source ──
	# Key: cost_center → list of source rows
	cc_data = defaultdict(lambda: {
		"primary_amount": 0,
		"allocated_in": 0,
		"allocated_out": 0,
		"sources": OrderedDict(),  # source_label → {primary, alloc_in, alloc_out}
	})

	for row in raw:
		cc = row.cost_center
		net = flt(row.total_debit) - flt(row.total_credit)

		source_label = _get_source_label(row)

		entry = cc_data[cc]
		if source_label not in entry["sources"]:
			entry["sources"][source_label] = {
				"primary_amount": 0,
				"allocated_in": 0,
				"allocated_out": 0,
			}

		src = entry["sources"][source_label]

		if row.co_document_type == "Primary Mirror":
			entry["primary_amount"] += net
			src["primary_amount"] += net
		elif net > 0:
			entry["allocated_in"] += net
			src["allocated_in"] += net
		else:
			entry["allocated_out"] += abs(net)
			src["allocated_out"] += abs(net)

	# ── 4. Calculate grand total for % column ──
	grand_total = 0
	for cc, vals in cc_data.items():
		net = vals["primary_amount"] + vals["allocated_in"] - vals["allocated_out"]
		if net > 0:
			grand_total += net

	# ── 5. Build tree rows ──
	data = []
	show_detail = filters.get("show_detail")

	for group_name, children in cc_hierarchy.items():
		# Filter to children that have data
		active_children = [c for c in children if c in cc_data]
		if not active_children:
			continue

		# Group totals
		group_primary = sum(cc_data[c]["primary_amount"] for c in active_children)
		group_alloc_in = sum(cc_data[c]["allocated_in"] for c in active_children)
		group_alloc_out = sum(cc_data[c]["allocated_out"] for c in active_children)
		group_net = group_primary + group_alloc_in - group_alloc_out
		group_pct = (group_net / grand_total * 100) if grand_total and group_net > 0 else 0

		# Parent row (indent 0)
		data.append({
			"label": group_name,
			"primary_amount": group_primary,
			"allocated_in": group_alloc_in,
			"allocated_out": group_alloc_out,
			"net_balance": group_net,
			"pct_of_total": group_pct,
			"indent": 0,
			"has_value": True,
		})

		# Child cost centers (indent 1)
		for cc in active_children:
			vals = cc_data[cc]
			cc_net = vals["primary_amount"] + vals["allocated_in"] - vals["allocated_out"]
			cc_pct = (cc_net / grand_total * 100) if grand_total and cc_net > 0 else 0

			# Strip company suffix for cleaner display
			cc_short = cc.split(" - ")[0] if " - " in cc else cc

			data.append({
				"label": cc_short,
				"primary_amount": vals["primary_amount"],
				"allocated_in": vals["allocated_in"],
				"allocated_out": vals["allocated_out"],
				"net_balance": cc_net,
				"pct_of_total": cc_pct,
				"indent": 1,
				"has_value": True,
			})

			# Source breakdown (indent 2) — only if show_detail
			if show_detail:
				for source_label, src in vals["sources"].items():
					src_net = src["primary_amount"] + src["allocated_in"] - src["allocated_out"]
					if flt(src_net, 2) == 0 and flt(src["primary_amount"], 2) == 0:
						continue

					data.append({
						"label": source_label,
						"primary_amount": src["primary_amount"],
						"allocated_in": src["allocated_in"],
						"allocated_out": src["allocated_out"],
						"net_balance": src_net,
						"pct_of_total": 0,
						"indent": 2,
						"has_value": True,
					})

	return data


def _get_cost_center_hierarchy(cost_center_filter=None):
	"""Build ordered dict: group_name → [child_cost_centers].

	Uses the Cost Center tree (parent_cost_center / lft / rgt).
	Only includes leaf cost centers (is_group=0).
	"""
	all_cc = frappe.db.sql(
		"""
		SELECT name, parent_cost_center, is_group, lft, rgt
		FROM `tabCost Center`
		ORDER BY lft
		""",
		as_dict=True,
	)

	if not all_cc:
		return OrderedDict()

	# Find the root
	root = None
	for cc in all_cc:
		if not cc.parent_cost_center:
			root = cc.name
			break

	# Build parent → children map for immediate children of root (groups)
	groups = OrderedDict()
	cc_to_group = {}

	for cc in all_cc:
		if cc.parent_cost_center == root and cc.is_group:
			groups[cc.name] = []

	# Assign leaf nodes to their parent group
	for cc in all_cc:
		if cc.is_group:
			continue

		# Walk up to find which top-level group this belongs to
		parent = cc.parent_cost_center
		while parent and parent != root:
			if parent in groups:
				break
			# Find parent's parent
			parent_row = next((r for r in all_cc if r.name == parent), None)
			parent = parent_row.parent_cost_center if parent_row else None

		if parent and parent in groups:
			if not cost_center_filter or cc.name == cost_center_filter:
				groups[parent].append(cc.name)

	return groups


def _get_source_label(row):
	"""Generate a human-readable source label from a CO Document row."""
	if row.co_document_type == "Primary Mirror":
		ce_name = row.cost_element_name or row.cost_element or "Primary"
		return f"Primary: {ce_name}"
	else:
		# For allocation docs, use the remarks which contain cycle info
		if row.remarks and "Allocation Cycle" in (row.remarks or ""):
			return row.remarks
		ce_name = row.cost_element_name or row.cost_element or ""
		return f"{row.co_document_type}: {ce_name}"


def get_chart(data):
	"""Bar chart showing Primary Cost vs Allocated In vs Allocated Out per CC group."""
	if not data:
		return None

	labels = []
	primary_values = []
	alloc_in_values = []
	net_values = []

	for row in data:
		if row.get("indent") == 0:
			label = row["label"]
			# Shorten: strip company suffix
			if " - " in label:
				label = label.split(" - ")[0]
			labels.append(label)
			primary_values.append(flt(row.get("primary_amount"), 2))
			alloc_in_values.append(flt(row.get("allocated_in"), 2))
			net_values.append(flt(row.get("net_balance"), 2))

	if not labels:
		return None

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Primary Cost"), "values": primary_values},
				{"name": _("Allocated In"), "values": alloc_in_values},
				{"name": _("Net Balance"), "values": net_values},
			],
		},
		"type": "bar",
		"colors": ["#7cd6fd", "#5e64ff", "#ffa00a"],
		"barOptions": {"stacked": False},
	}


def get_report_summary(data):
	"""Reconciliation summary: total primary, total allocated, net balance."""
	if not data:
		return []

	total_primary = 0
	total_alloc_in = 0
	total_alloc_out = 0

	for row in data:
		if row.get("indent") == 0:
			total_primary += flt(row.get("primary_amount"))
			total_alloc_in += flt(row.get("allocated_in"))
			total_alloc_out += flt(row.get("allocated_out"))

	total_net = total_primary + total_alloc_in - total_alloc_out

	return [
		{
			"value": total_primary,
			"indicator": "Blue",
			"label": _("Total Primary Cost"),
			"datatype": "Currency",
		},
		{
			"value": total_alloc_in,
			"indicator": "Green",
			"label": _("Total Allocated In"),
			"datatype": "Currency",
		},
		{
			"value": total_alloc_out,
			"indicator": "Orange",
			"label": _("Total Allocated Out"),
			"datatype": "Currency",
		},
		{
			"value": total_net,
			"indicator": "Red" if total_net < 0 else "Blue",
			"label": _("Net Balance (Reconciliation)"),
			"datatype": "Currency",
		},
	]
