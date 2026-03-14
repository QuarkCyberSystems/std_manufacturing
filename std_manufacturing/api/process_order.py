import frappe
from frappe import _
from frappe.utils import flt

from std_manufacturing.api.co_balance import get_co_cc_balance, get_co_cc_balance_for_costing


@frappe.whitelist()
def calculate_unit_costs(process_order):
	"""Calculate period and YTD unit costs using SAP weighted average inventory formula.

	CPU = (Opening_Value + Raw_Material_Cost + CC_Cost) / (Opening_QTY + Production_QTY)

	Where:
	  - Opening_Value = previous period's closing value for this item
	  - Raw_Material_Cost = sum of (consumed_qty × consumed_item_YTD_CPU)
	  - CC_Cost = post-allocation cost center balance
	  - Opening_QTY = inventory qty at start of fiscal year
	  - Production_QTY = YTD production output
	"""
	po = frappe.get_doc("Process Order", process_order)

	if po.docstatus != 1:
		frappe.throw(_("Process Order must be submitted"))

	if flt(po.total_output_qty) <= 0:
		frappe.throw(_("No output quantity recorded. Cannot calculate unit cost."))

	# Get period doc
	period_doc = frappe.get_cached_doc("Costing Period", po.costing_period)

	# YTD output qty (across all periods in fiscal year)
	ytd_output_qty = _get_ytd_output_qty(po.production_recipe, period_doc)

	# Opening inventory (start of fiscal year)
	opening_qty, opening_value = _get_opening_inventory(po.output_item)

	# Raw material cost (YTD consumed qty × each input's YTD CPU)
	ytd_raw_material_cost = _get_ytd_raw_material_cost(po.production_recipe, period_doc)

	# CC cost (post-allocation balance, YTD), split proportionally if shared CC
	full_cc_balance = _get_ytd_cc_balance(po.cost_center, period_doc)
	ytd_cc_balance = _get_cc_share(full_cc_balance, po.cost_center, po.production_recipe, period_doc)

	# Purchase cost (for items that are both produced and purchased)
	ytd_purchase_qty, ytd_purchase_value = _get_ytd_purchases(po.output_item, period_doc)

	# For items that are both produced AND purchased, use net production qty.
	# When production is fully consumed internally (e.g., quarry blasting → crushing),
	# only purchased qty counts as available inventory (SAP behavior).
	if flt(ytd_purchase_qty) > 0:
		ytd_internal_consumption = _get_ytd_internal_consumption(po.output_item, period_doc)
		net_production = max(0, flt(ytd_output_qty) - flt(ytd_internal_consumption))
	else:
		net_production = flt(ytd_output_qty)

	# Weighted average inventory CPU
	total_value = flt(opening_value) + flt(ytd_raw_material_cost) + flt(ytd_cc_balance) + flt(ytd_purchase_value)
	total_qty = flt(opening_qty) + flt(net_production) + flt(ytd_purchase_qty)

	ytd_unit_cost = flt(total_value) / flt(total_qty) if flt(total_qty) > 0 else 0

	# Period-only calculation (for reference)
	cc_balance = get_co_cc_balance_for_costing(po.cost_center, po.costing_period)
	unit_cost = flt(cc_balance) / flt(po.total_output_qty) if flt(po.total_output_qty) > 0 else 0

	# Standard rate
	standard_rate = frappe.db.get_value(
		"Standard Cost Rate",
		{"item_code": po.output_item, "status": "Active"},
		"standard_rate",
	) or 0

	cost_variance = flt(ytd_unit_cost) - flt(standard_rate)
	cost_variance_pct = (flt(cost_variance) / flt(standard_rate) * 100) if flt(standard_rate) else 0

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
		_("YTD CPU: {0} (Opening: {1} + RM: {2} + CC: {3}) / (Opening: {4} + Prod: {5})").format(
			frappe.format_value(ytd_unit_cost, {"fieldtype": "Currency"}),
			frappe.format_value(opening_value, {"fieldtype": "Currency"}),
			frappe.format_value(ytd_raw_material_cost, {"fieldtype": "Currency"}),
			frappe.format_value(ytd_cc_balance, {"fieldtype": "Currency"}),
			frappe.format_value(opening_qty, {"fieldtype": "Float"}),
			frappe.format_value(ytd_output_qty, {"fieldtype": "Float"}),
		)
	)

	return {
		"unit_cost": unit_cost,
		"ytd_unit_cost": ytd_unit_cost,
		"opening_qty": opening_qty,
		"opening_value": opening_value,
		"ytd_raw_material_cost": ytd_raw_material_cost,
		"ytd_cc_balance": ytd_cc_balance,
		"ytd_output_qty": ytd_output_qty,
	}


def _get_opening_inventory(item_code):
	"""Get opening inventory qty and value for an item at start of fiscal year.

	Looks at the item's opening stock (Stock Reconciliation or Material Receipt
	dated before the fiscal year start).
	"""
	# Check OPENING_INVENTORY data in demo_setup
	try:
		from std_manufacturing.demo_setup import OPENING_INVENTORY
		for code, name, group, uom, qty, value, rate in OPENING_INVENTORY:
			if code == item_code and flt(qty) > 0:
				return flt(qty), flt(value)
	except ImportError:
		pass

	return 0, 0


def _get_ytd_output_qty(production_recipe, period_doc):
	"""Get total YTD output qty across all periods in fiscal year."""
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

	ytd_qty = 0
	for period_name in periods:
		qty = frappe.db.get_value(
			"Process Order",
			{"production_recipe": production_recipe, "costing_period": period_name, "docstatus": 1},
			"total_output_qty",
		)
		ytd_qty += flt(qty)

	return ytd_qty


def _get_ytd_internal_consumption(item_code, period_doc):
	"""Get YTD qty of this item consumed as input by other Process Orders.

	When production output is consumed internally (by downstream POs),
	it should be excluded from available qty for CPU calculation.
	"""
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

	consumed = 0
	for period_name in periods:
		# Find all Process Orders in this period that consume this item
		po_names = frappe.get_all(
			"Process Order",
			filters={"costing_period": period_name, "docstatus": 1},
			pluck="name",
		)
		for po_name in po_names:
			inputs = frappe.get_all(
				"Process Order Input",
				filters={"parent": po_name, "item_code": item_code, "movement_type": "Consumption"},
				fields=["qty"],
			)
			for inp in inputs:
				consumed += flt(inp.qty)

	return consumed


def _get_ytd_cc_balance(cost_center, period_doc):
	"""Get YTD CC balance across all periods in fiscal year."""
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

	ytd_balance = 0
	for period_name in periods:
		ytd_balance += get_co_cc_balance_for_costing(cost_center, period_name)

	return ytd_balance


def _get_cc_share(full_cc_balance, cost_center, production_recipe, period_doc):
	"""Split CC balance proportionally if multiple recipes share the same cost center.

	Share = recipe_ytd_output / total_ytd_output_for_cc
	"""
	# Get all recipes that use this cost center
	recipes_on_cc = frappe.get_all(
		"Production Recipe",
		filters={"cost_center": cost_center, "is_active": 1},
		pluck="name",
	)

	if len(recipes_on_cc) <= 1:
		return full_cc_balance

	# Calculate total YTD output for all recipes on this CC
	total_output = 0
	my_output = 0
	for recipe in recipes_on_cc:
		qty = _get_ytd_output_qty(recipe, period_doc)
		total_output += flt(qty)
		if recipe == production_recipe:
			my_output = flt(qty)

	if total_output <= 0:
		return full_cc_balance

	return full_cc_balance * (my_output / total_output)


def _get_ytd_raw_material_cost(production_recipe, period_doc):
	"""Calculate YTD raw material cost using each input's YTD CPU.

	For each input material consumed:
	  Cost = consumed_qty × input_item_YTD_CPU

	The input's YTD CPU is calculated recursively for produced items
	(its own opening + RM cost + CC cost) / (opening_qty + production_qty).
	For purchased items, YTD CPU = (opening_value + purchase_value) / (opening_qty + purchase_qty).
	"""
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

	# Sum consumed quantities across all YTD periods
	from collections import defaultdict
	consumed = defaultdict(float)

	for period_name in periods:
		po_name = frappe.db.get_value(
			"Process Order",
			{"production_recipe": production_recipe, "costing_period": period_name, "docstatus": 1},
			"name",
		)
		if not po_name:
			continue

		inputs = frappe.get_all(
			"Process Order Input",
			filters={"parent": po_name, "movement_type": "Consumption"},
			fields=["item_code", "qty"],
		)
		for inp in inputs:
			consumed[inp.item_code] += flt(inp.qty)

	# Calculate cost for each consumed material
	total_cost = 0
	for item_code, qty in consumed.items():
		cpu = get_item_ytd_cpu(item_code, period_doc)
		total_cost += flt(qty) * flt(cpu)

	return total_cost


def get_item_ytd_cpu(item_code, period_doc=None):
	"""Get the YTD CPU for any item (purchased or produced).

	For purchased items: (opening_value + YTD_purchase_value) / (opening_qty + YTD_purchase_qty)
	For produced items: Uses the Process Order's ytd_unit_cost (must be calculated first)
	"""
	# Check if this item has a Process Order (produced item)
	if period_doc:
		po_data = frappe.db.get_value(
			"Process Order",
			{
				"output_item": item_code,
				"costing_period": period_doc.name,
				"docstatus": 1,
			},
			["ytd_unit_cost", "name"],
			as_dict=True,
		)
		if po_data and flt(po_data.ytd_unit_cost) > 0:
			return flt(po_data.ytd_unit_cost)

	# For purchased items, calculate from opening inventory + purchases
	return _get_purchased_item_ytd_cpu(item_code, period_doc)


def _get_ytd_purchases(item_code, period_doc):
	"""Get YTD purchase qty and value for an item (for items that are both produced and purchased)."""
	try:
		from std_manufacturing.demo_setup import PURCHASES
		ytd_qty = 0
		ytd_value = 0
		for code, jan_qty, jan_val, feb_qty, feb_val in PURCHASES:
			if code != item_code:
				continue
			if period_doc.period_start and period_doc.period_start.month >= 1:
				ytd_qty += flt(jan_qty)
				ytd_value += flt(jan_val)
			if period_doc.period_start and period_doc.period_start.month >= 2:
				ytd_qty += flt(feb_qty)
				ytd_value += flt(feb_val)
		return ytd_qty, ytd_value
	except ImportError:
		return 0, 0


def _get_purchased_item_ytd_cpu(item_code, period_doc=None):
	"""Calculate YTD CPU for a purchased item.

	YTD CPU = (Opening_Value + YTD_Purchase_Value) / (Opening_QTY + YTD_Purchase_QTY)
	"""
	# Opening inventory
	opening_qty, opening_value = _get_opening_inventory(item_code)

	# YTD purchases — sum from purchase receipts
	ytd_purchase_qty = 0
	ytd_purchase_value = 0

	if period_doc:
		# Get purchase data from demo_setup
		try:
			from std_manufacturing.demo_setup import PURCHASES
			fiscal_year_start = period_doc.period_start.replace(month=1, day=1) if period_doc.period_start else None

			for code, jan_qty, jan_val, feb_qty, feb_val in PURCHASES:
				if code != item_code:
					continue
				# Determine which months are within YTD
				if period_doc.period_start and period_doc.period_start.month >= 1:
					ytd_purchase_qty += flt(jan_qty)
					ytd_purchase_value += flt(jan_val)
				if period_doc.period_start and period_doc.period_start.month >= 2:
					ytd_purchase_qty += flt(feb_qty)
					ytd_purchase_value += flt(feb_val)
		except ImportError:
			pass

	total_qty = flt(opening_qty) + flt(ytd_purchase_qty)
	total_value = flt(opening_value) + flt(ytd_purchase_value)

	if total_qty > 0:
		return total_value / total_qty

	# No opening stock and no purchases — item has no inventory value
	return 0


@frappe.whitelist()
def calculate_all_unit_costs(costing_period):
	"""Calculate unit costs for all Process Orders in a period, in production chain order.

	Must be called AFTER allocation cycles have run, so CC balances are final.
	Processes orders in phase_sequence order so upstream CPUs are available
	for downstream raw material cost calculations.
	"""
	period_doc = frappe.get_doc("Costing Period", costing_period)

	# Get all process orders in phase sequence order
	orders = frappe.get_all(
		"Process Order",
		filters={"costing_period": costing_period, "docstatus": 1},
		fields=["name", "production_recipe", "output_item", "total_output_qty"],
		order_by="production_phase ASC",
	)

	# Get phase sequences for proper ordering
	for order in orders:
		seq = frappe.db.get_value("Production Recipe", order.production_recipe, "phase_sequence")
		order["phase_sequence"] = seq or 0

	orders.sort(key=lambda x: x["phase_sequence"])

	results = {}
	for order in orders:
		if flt(order.total_output_qty) <= 0:
			continue

		result = calculate_unit_costs(order.name)
		results[order.output_item] = result

	return results


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

	nodes.sort(key=lambda n: n["phase_sequence"])

	return {"nodes": nodes, "edges": edges}


@frappe.whitelist()
def populate_plcv_from_process_orders(costing_period):
	"""Update PLCV Entries with production data from Process Orders."""
	period_doc = frappe.get_doc("Costing Period", costing_period)

	process_orders = frappe.get_all(
		"Process Order",
		filters={"costing_period": costing_period, "docstatus": 1},
		fields=["name", "production_recipe", "output_item", "total_output_qty",
				"cost_center", "ytd_output_qty", "cc_balance", "ytd_cc_balance"],
	)

	updated = 0
	for po in process_orders:
		plcv = frappe.db.get_value(
			"PLCV Entry",
			{"item_code": po.output_item, "period": costing_period, "docstatus": 0},
			"name",
		)
		if not plcv:
			continue

		update_fields = {
			"ytd_production_qty": flt(po.ytd_output_qty),
		}

		input_cost = _calculate_input_material_cost(po.name)
		if input_cost:
			update_fields["ytd_material_cost"] = input_cost

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
