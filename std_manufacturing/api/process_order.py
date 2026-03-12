import frappe
from frappe import _
from frappe.utils import flt

from std_manufacturing.api.co_balance import get_co_cc_balance, get_co_cc_balance_for_costing


@frappe.whitelist()
def calculate_unit_costs(process_order):
	"""Calculate period and YTD unit costs for a Process Order.

	Unit Cost = CC Balance / Output Qty
	"""
	po = frappe.get_doc("Process Order", process_order)

	if po.docstatus != 1:
		frappe.throw(_("Process Order must be submitted"))

	if flt(po.total_output_qty) <= 0:
		frappe.throw(_("No output quantity recorded. Cannot calculate unit cost."))

	# Period unit cost
	cc_balance = get_co_cc_balance_for_costing(po.cost_center, po.costing_period)
	unit_cost = flt(cc_balance) / flt(po.total_output_qty)

	# Standard rate from active Standard Cost Rate
	standard_rate = frappe.db.get_value(
		"Standard Cost Rate",
		{
			"item_code": po.output_item,
			"status": "Active",
		},
		"standard_rate",
	) or 0

	cost_variance = flt(unit_cost) - flt(standard_rate)
	cost_variance_pct = (flt(cost_variance) / flt(standard_rate) * 100) if flt(standard_rate) else 0

	# YTD calculations
	period_doc = frappe.get_cached_doc("Costing Period", po.costing_period)
	ytd_output_qty, ytd_cc_balance = _get_ytd_values(
		po.production_recipe, po.cost_center, period_doc
	)

	ytd_unit_cost = flt(ytd_cc_balance) / flt(ytd_output_qty) if flt(ytd_output_qty) else 0

	# Update the Process Order
	frappe.db.set_value(
		"Process Order",
		process_order,
		{
			"cc_balance": cc_balance,
			"unit_cost": unit_cost,
			"standard_rate": standard_rate,
			"cost_variance": cost_variance,
			"cost_variance_pct": cost_variance_pct,
			"ytd_output_qty": ytd_output_qty,
			"ytd_cc_balance": ytd_cc_balance,
			"ytd_unit_cost": ytd_unit_cost,
		},
	)
	frappe.db.commit()

	frappe.msgprint(
		_("Unit Cost: {0} | YTD Unit Cost: {1}").format(
			frappe.format_value(unit_cost, {"fieldtype": "Currency"}),
			frappe.format_value(ytd_unit_cost, {"fieldtype": "Currency"}),
		)
	)

	return {"unit_cost": unit_cost, "ytd_unit_cost": ytd_unit_cost}


def _get_ytd_values(production_recipe, cost_center, period_doc):
	"""Get YTD output qty and CC balance across all periods in the fiscal year."""
	# Get all costing periods in this fiscal year up to and including current
	periods = frappe.get_all(
		"Costing Period",
		filters={
			"company": period_doc.company,
			"fiscal_year": period_doc.fiscal_year,
			"period_start": ("<=", period_doc.period_end),
			"docstatus": 1,
		},
		pluck="name",
	)

	ytd_output_qty = 0
	ytd_cc_balance = 0

	for period_name in periods:
		# Sum output qty from Process Orders for same recipe
		qty = frappe.db.get_value(
			"Process Order",
			{
				"production_recipe": production_recipe,
				"costing_period": period_name,
				"docstatus": 1,
			},
			"total_output_qty",
		)
		ytd_output_qty += flt(qty)

		# Sum CC balance
		ytd_cc_balance += get_co_cc_balance_for_costing(cost_center, period_name)

	return ytd_output_qty, ytd_cc_balance


@frappe.whitelist()
def create_process_orders_for_period(costing_period):
	"""Create draft Process Orders for all active recipes for a given costing period."""
	period_doc = frappe.get_doc("Costing Period", costing_period)

	if period_doc.docstatus != 1:
		frappe.throw(_("Costing Period must be submitted"))

	recipes = frappe.get_all(
		"Production Recipe",
		filters={"is_active": 1, "company": period_doc.company},
		fields=["name", "recipe_code", "recipe_name"],
		order_by="phase_sequence ASC",
	)

	created = 0
	skipped = 0

	for recipe in recipes:
		existing = frappe.db.exists(
			"Process Order",
			{
				"production_recipe": recipe.name,
				"costing_period": costing_period,
				"docstatus": ("!=", 2),
			},
		)

		if existing:
			skipped += 1
			continue

		po = frappe.new_doc("Process Order")
		po.costing_period = costing_period
		po.production_recipe = recipe.name
		po.insert(ignore_permissions=True)
		created += 1

	frappe.db.commit()
	frappe.msgprint(
		_("{0} Process Orders created, {1} skipped (already exist)").format(created, skipped)
	)

	return {"created": created, "skipped": skipped}


@frappe.whitelist()
def get_production_chain(costing_period):
	"""Return the production chain as nodes and edges for visualization."""
	process_orders = frappe.get_all(
		"Process Order",
		filters={
			"costing_period": costing_period,
			"docstatus": ("!=", 2),
		},
		fields=[
			"name", "production_recipe", "recipe_name", "production_phase",
			"cost_center", "output_item", "output_item_name", "output_uom",
			"total_output_qty", "unit_cost", "ytd_unit_cost", "status",
		],
		order_by="production_phase ASC",
	)

	# Get phase sequences for ordering
	recipe_sequences = {}
	for po in process_orders:
		if po.production_recipe not in recipe_sequences:
			seq = frappe.db.get_value(
				"Production Recipe", po.production_recipe, "phase_sequence"
			)
			recipe_sequences[po.production_recipe] = seq or 0

	nodes = []
	for po in process_orders:
		nodes.append({
			"name": po.name,
			"recipe": po.production_recipe,
			"recipe_name": po.recipe_name,
			"phase": po.production_phase,
			"phase_sequence": recipe_sequences.get(po.production_recipe, 0),
			"cost_center": po.cost_center,
			"output_item": po.output_item,
			"output_item_name": po.output_item_name,
			"output_qty": po.total_output_qty,
			"unit_cost": po.unit_cost,
			"ytd_unit_cost": po.ytd_unit_cost,
			"status": po.status,
		})

	# Build edges from chain links
	edges = []
	chain_links = frappe.get_all(
		"Process Order Chain Link",
		filters={
			"parent": ("in", [po.name for po in process_orders]),
			"parentfield": "successor_orders",
		},
		fields=["parent", "process_order", "item_code"],
	)

	for link in chain_links:
		edges.append({
			"from": link.parent,
			"to": link.process_order,
			"item": link.item_code,
		})

	# Sort nodes by phase sequence
	nodes.sort(key=lambda n: n["phase_sequence"])

	return {"nodes": nodes, "edges": edges}


@frappe.whitelist()
def populate_plcv_from_process_orders(costing_period):
	"""Update PLCV Entries with production data from Process Orders.

	For items with cost_category = 'Semi-Finished' or 'Finished',
	fills ytd_production_qty from Process Order data.
	"""
	period_doc = frappe.get_doc("Costing Period", costing_period)

	process_orders = frappe.get_all(
		"Process Order",
		filters={
			"costing_period": costing_period,
			"docstatus": 1,
		},
		fields=["name", "production_recipe", "output_item", "total_output_qty",
				"cost_center", "ytd_output_qty", "cc_balance", "ytd_cc_balance"],
	)

	updated = 0
	for po in process_orders:
		plcv = frappe.db.get_value(
			"PLCV Entry",
			{
				"item_code": po.output_item,
				"period": costing_period,
				"docstatus": 0,
			},
			"name",
		)

		if not plcv:
			continue

		update_fields = {
			"ytd_production_qty": flt(po.ytd_output_qty),
		}

		# Calculate material cost from input entries
		input_cost = _calculate_input_material_cost(po.name)
		if input_cost:
			update_fields["ytd_material_cost"] = input_cost

		# Overhead = CC balance (costs accumulated via allocation cycles)
		if flt(po.ytd_cc_balance):
			update_fields["ytd_overhead_cost"] = flt(po.ytd_cc_balance)

		frappe.db.set_value("PLCV Entry", plcv, update_fields)
		updated += 1

	frappe.db.commit()
	frappe.msgprint(_("{0} PLCV Entries updated from Process Orders").format(updated))
	return updated


def _calculate_input_material_cost(process_order_name):
	"""Sum input material costs using standard rates."""
	inputs = frappe.get_all(
		"Process Order Input",
		filters={"parent": process_order_name, "movement_type": "Consumption"},
		fields=["item_code", "qty"],
	)

	total_cost = 0
	for inp in inputs:
		std_rate = frappe.db.get_value(
			"Standard Cost Rate",
			{"item_code": inp.item_code, "status": "Active"},
			"standard_rate",
		)
		total_cost += flt(inp.qty) * flt(std_rate)

	return total_cost
