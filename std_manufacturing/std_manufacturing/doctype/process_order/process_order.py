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
		self.create_skf_entry()
		self.populate_chain_links()
		self.db_set("status", "Open")

	def on_cancel(self):
		self.cancel_skf_entry()
		self.db_set("status", "Cancelled")

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
