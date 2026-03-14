import frappe
from frappe import _
from frappe.utils import flt
from collections import OrderedDict

from std_manufacturing.api.co_balance import get_co_cc_balance_for_costing


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	chart = get_chart(data, filters)
	report_summary = get_report_summary(data)
	return columns, data, None, chart, report_summary


def get_columns(filters):
	show_ytd = filters.get("show_ytd") if filters else False

	cols = [
		{
			"fieldname": "label",
			"label": _("Product / Detail"),
			"fieldtype": "Data",
			"width": 350,
		},
		{
			"fieldname": "output_qty",
			"label": _("Output Qty"),
			"fieldtype": "Float",
			"width": 120,
			"precision": 2,
		},
		{
			"fieldname": "uom",
			"label": _("UOM"),
			"fieldtype": "Data",
			"width": 60,
		},
		{
			"fieldname": "cc_balance",
			"label": _("CC Balance"),
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"fieldname": "unit_cost",
			"label": _("Unit Cost"),
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"fieldname": "standard_rate",
			"label": _("Std Rate"),
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"fieldname": "cost_variance",
			"label": _("Variance"),
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"fieldname": "variance_pct",
			"label": _("Var %"),
			"fieldtype": "Percent",
			"width": 80,
		},
	]

	if show_ytd:
		cols.extend([
			{
				"fieldname": "ytd_output_qty",
				"label": _("YTD Qty"),
				"fieldtype": "Float",
				"width": 120,
				"precision": 2,
			},
			{
				"fieldname": "ytd_unit_cost",
				"label": _("YTD Unit Cost"),
				"fieldtype": "Currency",
				"width": 120,
			},
			{
				"fieldname": "ytd_variance",
				"label": _("YTD Variance"),
				"fieldtype": "Currency",
				"width": 120,
			},
		])

	return cols


def get_data(filters):
	if not filters:
		filters = {}

	period = filters.get("period")
	if not period:
		return []

	phase_filter = filters.get("production_phase")
	item_filter = filters.get("output_item")
	show_ytd = filters.get("show_ytd")
	show_inputs = filters.get("show_inputs")

	# Fetch submitted Process Orders for the period
	po_filters = {
		"costing_period": period,
		"docstatus": 1,
	}
	if item_filter:
		po_filters["output_item"] = item_filter

	process_orders = frappe.get_all(
		"Process Order",
		filters=po_filters,
		fields=[
			"name", "production_recipe", "output_item",
			"total_output_qty", "cc_balance", "unit_cost",
			"standard_rate", "cost_variance", "cost_variance_pct",
			"ytd_output_qty", "ytd_cc_balance", "ytd_unit_cost",
			"cost_center",
		],
	)

	if not process_orders:
		return []

	# Get recipe details for phase grouping
	recipe_map = {}
	recipes = frappe.get_all(
		"Production Recipe",
		filters={"name": ("in", [po.production_recipe for po in process_orders])},
		fields=["name", "recipe_name", "production_phase", "phase_sequence",
				"output_item", "output_uom"],
	)
	for r in recipes:
		recipe_map[r.name] = r

	# Apply phase filter
	if phase_filter:
		process_orders = [
			po for po in process_orders
			if recipe_map.get(po.production_recipe, {}).get("production_phase") == phase_filter
		]
		if not process_orders:
			return []

	# Get item names
	item_names = {}
	items = frappe.get_all(
		"Item",
		filters={"name": ("in", list({po.output_item for po in process_orders}))},
		fields=["name", "item_name"],
	)
	for item in items:
		item_names[item.name] = item.item_name

	# Group by production phase → process orders
	phases = OrderedDict()
	for po in process_orders:
		recipe = recipe_map.get(po.production_recipe)
		if not recipe:
			continue

		phase = recipe.production_phase
		seq = recipe.phase_sequence or 0

		if phase not in phases:
			phases[phase] = {"sequence": seq, "orders": []}

		phases[phase]["orders"].append({
			"po": po,
			"recipe": recipe,
		})

	# Sort phases by sequence
	sorted_phases = sorted(phases.items(), key=lambda x: x[1]["sequence"])

	# Collect input data if needed
	input_data = {}
	if show_inputs:
		all_po_names = [po.name for po in process_orders]
		inputs = frappe.get_all(
			"Process Order Input",
			filters={"parent": ("in", all_po_names), "movement_type": "Consumption"},
			fields=["parent", "item_code", "qty"],
		)

		# Get input item names and standard rates
		input_item_codes = list({i.item_code for i in inputs})
		if input_item_codes:
			input_items = frappe.get_all(
				"Item",
				filters={"name": ("in", input_item_codes)},
				fields=["name", "item_name", "stock_uom"],
			)
			for item in input_items:
				item_names[item.name] = item.item_name

		input_std_rates = {}
		if input_item_codes:
			rates = frappe.get_all(
				"Standard Cost Rate",
				filters={"item_code": ("in", input_item_codes), "status": "Active"},
				fields=["item_code", "standard_rate"],
			)
			for r in rates:
				input_std_rates[r.item_code] = flt(r.standard_rate)

		for inp in inputs:
			input_data.setdefault(inp.parent, []).append(inp)

	# Build tree rows
	data = []

	for phase_name, phase_info in sorted_phases:
		orders = phase_info["orders"]
		# Sort orders within phase by recipe sequence, then name
		orders.sort(key=lambda x: (x["recipe"].phase_sequence or 0, x["recipe"].recipe_name))

		# Phase totals
		phase_cc_balance = sum(flt(o["po"].cc_balance) for o in orders)
		phase_output = sum(flt(o["po"].total_output_qty) for o in orders)

		data.append({
			"label": phase_name,
			"output_qty": None,
			"uom": "",
			"cc_balance": phase_cc_balance,
			"unit_cost": None,
			"standard_rate": None,
			"cost_variance": None,
			"variance_pct": None,
			"ytd_output_qty": None,
			"ytd_unit_cost": None,
			"ytd_variance": None,
			"indent": 0,
			"has_value": True,
		})

		for entry in orders:
			po = entry["po"]
			recipe = entry["recipe"]
			item_name = item_names.get(po.output_item, po.output_item)
			variance_pct = (
				flt(po.cost_variance) / flt(po.standard_rate) * 100
				if flt(po.standard_rate) else 0
			)

			row = {
				"label": f"{item_name} ({po.output_item})",
				"output_qty": flt(po.total_output_qty),
				"uom": recipe.output_uom or "",
				"cc_balance": flt(po.cc_balance),
				"unit_cost": flt(po.unit_cost),
				"standard_rate": flt(po.standard_rate),
				"cost_variance": flt(po.cost_variance),
				"variance_pct": variance_pct,
				"indent": 1,
				"has_value": True,
			}

			if show_ytd:
				ytd_variance = flt(po.ytd_unit_cost) - flt(po.standard_rate)
				row["ytd_output_qty"] = flt(po.ytd_output_qty)
				row["ytd_unit_cost"] = flt(po.ytd_unit_cost)
				row["ytd_variance"] = ytd_variance

			data.append(row)

			# Input breakdown (indent 2)
			if show_inputs and po.name in input_data:
				po_inputs = input_data[po.name]
				po_inputs.sort(key=lambda x: x.item_code)

				total_input_cost = 0
				for inp in po_inputs:
					inp_name = item_names.get(inp.item_code, inp.item_code)
					std_rate = input_std_rates.get(inp.item_code, 0)
					line_cost = flt(inp.qty) * flt(std_rate)
					total_input_cost += line_cost

					data.append({
						"label": f"{inp_name} ({inp.item_code})",
						"output_qty": flt(inp.qty),
						"uom": "",
						"cc_balance": line_cost,
						"unit_cost": flt(std_rate),
						"standard_rate": None,
						"cost_variance": None,
						"variance_pct": None,
						"indent": 2,
						"has_value": True,
					})

				# Overhead line: CC balance minus material cost
				overhead = flt(po.cc_balance) - total_input_cost
				data.append({
					"label": _("Overhead (CC Balance - Materials)"),
					"output_qty": None,
					"uom": "",
					"cc_balance": overhead,
					"unit_cost": flt(overhead) / flt(po.total_output_qty) if flt(po.total_output_qty) else 0,
					"standard_rate": None,
					"cost_variance": None,
					"variance_pct": None,
					"indent": 2,
					"has_value": True,
				})

	return data


def get_chart(data, filters=None):
	"""Bar chart comparing Unit Cost vs Standard Rate per product."""
	if not data:
		return None

	show_ytd = filters.get("show_ytd") if filters else False

	labels = []
	unit_cost_values = []
	std_rate_values = []
	variance_values = []

	for row in data:
		if row.get("indent") == 1 and flt(row.get("unit_cost")):
			labels.append(row["label"])
			if show_ytd and flt(row.get("ytd_unit_cost")):
				unit_cost_values.append(flt(row.get("ytd_unit_cost"), 2))
				variance_values.append(flt(row.get("ytd_variance"), 2))
			else:
				unit_cost_values.append(flt(row.get("unit_cost"), 2))
				variance_values.append(flt(row.get("cost_variance"), 2))
			std_rate_values.append(flt(row.get("standard_rate"), 2))

	if not labels:
		return None

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Unit Cost"), "values": unit_cost_values},
				{"name": _("Standard Rate"), "values": std_rate_values},
			],
		},
		"type": "bar",
		"colors": ["#5e64ff", "#7cd6fd"],
		"barOptions": {"stacked": False},
	}


def get_report_summary(data):
	"""Reconciliation summary: total CC balance, product count, avg variance."""
	if not data:
		return []

	total_cc_balance = 0
	total_variance = 0
	product_count = 0
	favorable = 0
	unfavorable = 0

	for row in data:
		if row.get("indent") != 1:
			continue
		product_count += 1
		total_cc_balance += flt(row.get("cc_balance"))
		var = flt(row.get("cost_variance"))
		total_variance += var
		if var > 0:
			unfavorable += 1
		elif var < 0:
			favorable += 1

	phase_count = sum(1 for row in data if row.get("indent") == 0)

	return [
		{
			"value": product_count,
			"indicator": "Blue",
			"label": _("Products"),
			"datatype": "Int",
		},
		{
			"value": phase_count,
			"indicator": "Blue",
			"label": _("Production Phases"),
			"datatype": "Int",
		},
		{
			"value": total_cc_balance,
			"indicator": "Blue",
			"label": _("Total CC Balance"),
			"datatype": "Currency",
		},
		{
			"value": unfavorable,
			"indicator": "Red",
			"label": _("Unfavorable Variances"),
			"datatype": "Int",
		},
		{
			"value": favorable,
			"indicator": "Green",
			"label": _("Favorable Variances"),
			"datatype": "Int",
		},
	]
