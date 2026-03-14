import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class ProcessOrder(Document):
	def validate(self):
		self.calculate_totals()
		self.calculate_standard_quantities()

	def calculate_totals(self):
		self.total_output_qty = sum(
			flt(row.qty)
			for row in self.output_entries
			if row.movement_type == "Production"
		)

	def calculate_standard_quantities(self):
		if not self.production_recipe:
			return

		recipe = frappe.get_cached_doc("Production Recipe", self.production_recipe)
		recipe_inputs = {r.item_code: r.qty_per_unit for r in recipe.input_items}

		for row in self.input_entries:
			if row.item_code in recipe_inputs:
				row.standard_qty = flt(recipe_inputs[row.item_code]) * flt(self.total_output_qty)
				row.variance_qty = flt(row.qty) - flt(row.standard_qty)

	def on_submit(self):
		self.create_stock_entries()
		self.create_skf_entry()
		self.populate_chain_links()
		self.db_set("status", "Open")

	def on_cancel(self):
		self.cancel_stock_entries()
		self.cancel_skf_entry()
		self.db_set("status", "Cancelled")

	def create_stock_entries(self):
		"""Create Material Issue (consumption) and Material Receipt (production) Stock Entries."""
		period_doc = frappe.get_cached_doc("Costing Period", self.costing_period)
		posting_date = period_doc.period_end or frappe.utils.today()

		# Get standard rates for all items
		std_rates = self._get_standard_rates()

		# Material Issue for inputs (consumption)
		consumption_rows = [
			row for row in self.input_entries
			if row.movement_type == "Consumption" and flt(row.qty) > 0
		]
		if consumption_rows:
			se_issue = frappe.new_doc("Stock Entry")
			se_issue.stock_entry_type = "Material Issue"
			se_issue.company = self.company
			se_issue.posting_date = posting_date
			se_issue.set_posting_time = 1
			se_issue.posting_time = "23:59:59"
			se_issue.remarks = f"Consumption for {self.name} - {self.recipe_name}"

			for row in consumption_rows:
				se_issue.append("items", {
					"item_code": row.item_code,
					"qty": flt(row.qty),
					"s_warehouse": row.source_warehouse or "Stores - BCP",
					"cost_center": self.cost_center,
					"basic_rate": flt(std_rates.get(row.item_code, 0)),
				})

			se_issue.insert(ignore_permissions=True)
			se_issue.submit()

			# Store reference back on input rows
			for row in consumption_rows:
				frappe.db.set_value(
					"Process Order Input", row.name,
					{"reference_doctype": "Stock Entry", "reference_name": se_issue.name},
					update_modified=False,
				)

		# Material Receipt for outputs (production)
		production_rows = [
			row for row in self.output_entries
			if row.movement_type == "Production" and flt(row.qty) > 0
		]
		if production_rows:
			se_receipt = frappe.new_doc("Stock Entry")
			se_receipt.stock_entry_type = "Material Receipt"
			se_receipt.company = self.company
			se_receipt.posting_date = posting_date
			se_receipt.set_posting_time = 1
			se_receipt.posting_time = "23:59:59"
			se_receipt.remarks = f"Production output for {self.name} - {self.recipe_name}"

			for row in production_rows:
				target_wh = row.target_warehouse or self._get_default_target_warehouse(row.item_code)
				se_receipt.append("items", {
					"item_code": row.item_code,
					"qty": flt(row.qty),
					"t_warehouse": target_wh,
					"cost_center": self.cost_center,
					"basic_rate": flt(std_rates.get(row.item_code, 0)),
				})

			se_receipt.insert(ignore_permissions=True)
			se_receipt.submit()

			# Store reference back on output rows
			for row in production_rows:
				frappe.db.set_value(
					"Process Order Output", row.name,
					{"reference_doctype": "Stock Entry", "reference_name": se_receipt.name},
					update_modified=False,
				)

	def cancel_stock_entries(self):
		"""Cancel all Stock Entries linked from input/output rows."""
		se_names = set()

		for row in self.input_entries:
			if row.reference_doctype == "Stock Entry" and row.reference_name:
				se_names.add(row.reference_name)

		for row in self.output_entries:
			if row.reference_doctype == "Stock Entry" and row.reference_name:
				se_names.add(row.reference_name)

		for se_name in se_names:
			se = frappe.get_doc("Stock Entry", se_name)
			if se.docstatus == 1:
				se.cancel()

	def _get_standard_rates(self):
		"""Get active standard rates for all items in this Process Order."""
		item_codes = set()
		for row in self.input_entries:
			item_codes.add(row.item_code)
		for row in self.output_entries:
			item_codes.add(row.item_code)

		if not item_codes:
			return {}

		rates = frappe.get_all(
			"Standard Cost Rate",
			filters={"item_code": ("in", list(item_codes)), "status": "Active"},
			fields=["item_code", "standard_rate"],
		)
		return {r.item_code: flt(r.standard_rate) for r in rates}

	def _get_default_target_warehouse(self, item_code):
		"""Determine target warehouse based on item group."""
		item_group = frappe.db.get_value("Item", item_code, "item_group")
		if item_group == "Finished Goods":
			return "Finished Goods - BCP"
		return "Work In Progress - BCP"

	def create_skf_entry(self):
		if not self.production_recipe or flt(self.total_output_qty) <= 0:
			return

		recipe = frappe.get_cached_doc("Production Recipe", self.production_recipe)
		if not recipe.production_skf:
			return

		entry = frappe.new_doc("SKF Entry")
		entry.skf = recipe.production_skf
		entry.period = self.costing_period
		entry.cost_center = self.cost_center
		entry.quantity = self.total_output_qty
		entry.entry_source = "Production Report"
		entry.source_reference = self.name

		period_doc = frappe.get_cached_doc("Costing Period", self.costing_period)
		entry.entry_date = period_doc.period_end or frappe.utils.today()

		entry.insert(ignore_permissions=True)
		entry.submit()

		self.db_set("skf_entry", entry.name)
		self.db_set("skf_entry_posted", 1)

	def cancel_skf_entry(self):
		entries = frappe.get_all(
			"SKF Entry",
			filters={
				"source_reference": self.name,
				"entry_source": "Production Report",
				"docstatus": 1,
			},
			pluck="name",
		)
		for entry_name in entries:
			entry = frappe.get_doc("SKF Entry", entry_name)
			entry.cancel()

		self.db_set("skf_entry_posted", 0)
		self.db_set("skf_entry", None)

	def populate_chain_links(self):
		"""Find other Process Orders in the same period and link them via recipe relationships."""
		if not self.production_recipe:
			return

		recipe = frappe.get_cached_doc("Production Recipe", self.production_recipe)

		# Clear existing chain links
		self.set("predecessor_orders", [])
		self.set("successor_orders", [])

		# Find predecessor Process Orders
		for pred_link in recipe.predecessor_recipes:
			pred_po = frappe.db.get_value(
				"Process Order",
				{
					"production_recipe": pred_link.recipe,
					"costing_period": self.costing_period,
					"docstatus": ("!=", 2),
				},
				"name",
			)
			if pred_po:
				self.append(
					"predecessor_orders",
					{
						"process_order": pred_po,
						"item_code": pred_link.link_item,
						"direction": "Predecessor",
					},
				)

		# Find successor Process Orders
		for succ_link in recipe.successor_recipes:
			succ_po = frappe.db.get_value(
				"Process Order",
				{
					"production_recipe": succ_link.recipe,
					"costing_period": self.costing_period,
					"docstatus": ("!=", 2),
				},
				"name",
			)
			if succ_po:
				self.append(
					"successor_orders",
					{
						"process_order": succ_po,
						"item_code": succ_link.link_item,
						"direction": "Successor",
					},
				)

		self.save_chain_links()

	def save_chain_links(self):
		"""Save chain link child tables without triggering full save."""
		# Delete existing
		frappe.db.delete(
			"Process Order Chain Link",
			{"parent": self.name},
		)
		# Insert new
		for row in self.predecessor_orders:
			row.parent = self.name
			row.parenttype = "Process Order"
			row.parentfield = "predecessor_orders"
			row.insert(ignore_permissions=True)

		for row in self.successor_orders:
			row.parent = self.name
			row.parenttype = "Process Order"
			row.parentfield = "successor_orders"
			row.insert(ignore_permissions=True)
