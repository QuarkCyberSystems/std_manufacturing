import frappe
from frappe import _
from frappe.utils import flt, now

from std_manufacturing.api.co_balance import get_co_cc_balance, get_skf_entry_value, get_skf_total_for_period


@frappe.whitelist()
def execute_allocation_run(costing_period):
	"""Execute all active allocation cycles for a costing period.

	Creates an Allocation Run document with results for each cycle.
	Each cycle creates a CO Document moving costs from sender to receivers.
	"""
	period_doc = frappe.get_doc("Costing Period", costing_period)

	if period_doc.docstatus != 1:
		frappe.throw(_("Costing Period must be submitted"))

	# Check no existing submitted run
	existing = frappe.db.get_value(
		"Allocation Run",
		{"period": costing_period, "docstatus": 1},
		"name",
	)
	if existing:
		frappe.throw(
			_("A submitted Allocation Run already exists for this period: {0}").format(existing)
		)

	# Get all active cycles ordered by cycle_number
	cycles = frappe.get_all(
		"Allocation Cycle",
		filters={"is_active": 1},
		fields=["name", "cycle_number", "cycle_name", "sender_cost_center",
				"secondary_cost_element", "tracing_type", "tracing_skf",
				"intermediate_item", "co_document_type"],
		order_by="cycle_number asc",
	)

	if not cycles:
		frappe.throw(_("No active Allocation Cycles found"))

	# Create the Allocation Run
	run = frappe.new_doc("Allocation Run")
	run.period = costing_period
	run.company = period_doc.company
	run.posting_date = period_doc.period_end
	run.status = "In Progress"
	run.run_started_at = now()

	co_docs_created = []
	total_allocated = 0
	cycles_executed = 0

	for cycle in cycles:
		cycle_result = {
			"cycle_number": cycle.cycle_number,
			"cycle_name": cycle.cycle_name,
			"sender_cost_center": cycle.sender_cost_center,
		}

		try:
			# Get sender balance from CO sub-ledger
			sender_balance = get_co_cc_balance(cycle.sender_cost_center, costing_period)
			cycle_result["sender_balance"] = sender_balance

			if flt(sender_balance, 2) == 0:
				cycle_result["status"] = "Skipped"
				cycle_result["amount_allocated"] = 0
				run.append("cycle_results", cycle_result)
				continue

			# Get receiver shares
			cycle_doc = frappe.get_doc("Allocation Cycle", cycle.name)
			shares = _get_receiver_shares(cycle_doc, costing_period, sender_balance)

			if not shares:
				cycle_result["status"] = "Skipped"
				cycle_result["amount_allocated"] = 0
				run.append("cycle_results", cycle_result)
				continue

			# Create CO Document
			co_doc = _create_allocation_co_document(
				cycle, shares, sender_balance, costing_period, period_doc
			)
			co_docs_created.append(co_doc.name)

			cycle_result["co_document"] = co_doc.name
			cycle_result["amount_allocated"] = abs(sender_balance)
			cycle_result["status"] = "Completed"
			total_allocated += abs(sender_balance)
			cycles_executed += 1

		except Exception as e:
			cycle_result["status"] = "Failed"
			cycle_result["error_message"] = str(e)
			# Rollback: cancel all CO Documents created so far
			for co_name in co_docs_created:
				try:
					co = frappe.get_doc("CO Document", co_name)
					if co.docstatus == 1:
						co.cancel()
				except Exception:
					pass

			run.status = "Failed"
			run.append("cycle_results", cycle_result)
			run.run_completed_at = now()
			run.total_cycles_executed = cycles_executed
			run.total_amount_allocated = total_allocated
			run.insert(ignore_permissions=True)
			frappe.db.commit()
			frappe.throw(
				_("Allocation failed at Cycle {0} ({1}): {2}. All allocations rolled back.").format(
					cycle.cycle_number, cycle.cycle_name, str(e)
				)
			)

		run.append("cycle_results", cycle_result)

	# All cycles completed successfully
	run.status = "Completed"
	run.run_completed_at = now()
	run.total_cycles_executed = cycles_executed
	run.total_amount_allocated = total_allocated
	run.insert(ignore_permissions=True)
	run.submit()
	frappe.db.commit()

	frappe.msgprint(
		_("Allocation Run completed: {0} cycles executed, {1} total allocated").format(
			cycles_executed, frappe.format_value(total_allocated, {"fieldtype": "Currency"})
		)
	)
	return run.name


def _get_receiver_shares(cycle_doc, period, sender_balance):
	"""Calculate allocation shares for each receiver based on tracing type.

	Returns list of dicts: [{"cost_center": cc, "share": fraction, "amount": amount}]
	"""
	receivers = cycle_doc.receivers
	if not receivers:
		return []

	shares = []
	amount_to_allocate = abs(sender_balance)

	if cycle_doc.tracing_type == "Fixed Percentage":
		allocated_so_far = 0
		for i, row in enumerate(receivers):
			if i == len(receivers) - 1:
				# Last receiver gets remainder
				amount = amount_to_allocate - allocated_so_far
			else:
				amount = flt(amount_to_allocate * flt(row.fixed_percentage) / 100, 2)
			allocated_so_far += amount
			shares.append({
				"cost_center": row.cost_center,
				"share": flt(row.fixed_percentage) / 100,
				"amount": amount,
			})

	elif cycle_doc.tracing_type == "SKF-Based":
		skf = cycle_doc.tracing_skf
		total_skf = get_skf_total_for_period(skf, period)
		if flt(total_skf) == 0:
			frappe.throw(
				_("No SKF entries found for {0} in period {1}. Cannot allocate.").format(
					skf, period
				)
			)

		# Only include receivers that have SKF entries
		allocated_so_far = 0
		valid_receivers = []
		for row in receivers:
			qty = get_skf_entry_value(skf, period, row.cost_center)
			if flt(qty) > 0:
				valid_receivers.append((row, qty))

		for i, (row, qty) in enumerate(valid_receivers):
			share = flt(qty) / flt(total_skf)
			if i == len(valid_receivers) - 1:
				amount = amount_to_allocate - allocated_so_far
			else:
				amount = flt(amount_to_allocate * share, 2)
			allocated_so_far += amount
			shares.append({
				"cost_center": row.cost_center,
				"share": share,
				"amount": amount,
			})

	elif cycle_doc.tracing_type == "Production Ratio":
		# Single receiver gets ratio * sender_balance based on production
		# The ratio is: total consumed qty / total produced qty for the intermediate item
		# at the sender cost center during the period
		if len(receivers) != 1:
			frappe.throw(
				_("Production Ratio tracing requires exactly one receiver, got {0}").format(
					len(receivers)
				)
			)

		# For production ratio, we allocate 100% of the sender balance
		# (the ratio concept applies to standard cost calculations, not allocation splitting)
		shares.append({
			"cost_center": receivers[0].cost_center,
			"share": 1.0,
			"amount": amount_to_allocate,
		})

	return shares


def _create_allocation_co_document(cycle, shares, sender_balance, costing_period, period_doc):
	"""Create and submit a CO Document for an allocation cycle."""
	co_doc = frappe.new_doc("CO Document")
	co_doc.co_document_type = cycle.co_document_type
	co_doc.company = period_doc.company
	co_doc.cost_element = cycle.secondary_cost_element
	co_doc.period = costing_period
	co_doc.posting_date = period_doc.period_end
	co_doc.remarks = f"Allocation Cycle {cycle.cycle_number}: {cycle.cycle_name}"

	amount_to_allocate = abs(sender_balance)

	# Credit the sender (reduce balance)
	co_doc.append(
		"lines",
		{
			"cost_center": cycle.sender_cost_center,
			"debit_amount": 0,
			"credit_amount": amount_to_allocate,
		},
	)

	# Debit each receiver
	for share in shares:
		if flt(share["amount"], 2) > 0:
			co_doc.append(
				"lines",
				{
					"cost_center": share["cost_center"],
					"debit_amount": flt(share["amount"], 2),
					"credit_amount": 0,
				},
			)

	co_doc.insert(ignore_permissions=True)
	co_doc.submit()
	return co_doc
