import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PLCVEntry(Document):
	def validate(self):
		self.calculate_ytd_cpu()
		self.calculate_variance()

	def calculate_ytd_cpu(self):
		if self.cost_category == "Purchased":
			total_qty = flt(self.opening_qty) + flt(self.ytd_purchase_qty)
			total_value = (
				flt(self.opening_value) + flt(self.ytd_purchase_value) + flt(self.ytd_cost_pool_amount)
			)
			self.ytd_actual_cpu = total_value / total_qty if total_qty else 0
		else:
			# Produced items
			total_cost = flt(self.ytd_material_cost) + flt(self.ytd_overhead_cost)
			self.ytd_actual_cpu = total_cost / flt(self.ytd_production_qty) if flt(self.ytd_production_qty) else 0

	def calculate_variance(self):
		self.variance_per_unit = flt(self.ytd_actual_cpu) - flt(self.standard_rate)

		total_qty = flt(self.closing_stock_qty) + flt(self.ytd_issued_qty)
		self.total_variance = self.variance_per_unit * total_qty if total_qty else 0

		if total_qty:
			cogs_ratio = flt(self.ytd_issued_qty) / total_qty
			self.cogs_variance = self.total_variance * cogs_ratio
			self.inventory_variance = self.total_variance - self.cogs_variance
		else:
			self.cogs_variance = 0
			self.inventory_variance = 0

	def on_submit(self):
		self.db_set("status", "Calculated")
