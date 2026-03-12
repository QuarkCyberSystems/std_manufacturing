import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class CostPool(Document):
	def validate(self):
		self._validate_allocation_total()

	def _validate_allocation_total(self):
		if not self.items:
			return
		total_allocated = sum(flt(item.allocated_amount) for item in self.items)
		if abs(total_allocated - flt(self.total_amount)) > 0.01:
			frappe.throw(
				_("Sum of allocated amounts ({0}) does not equal total amount ({1})").format(
					total_allocated, self.total_amount
				)
			)

	@frappe.whitelist()
	def fetch_items(self):
		"""Populate items from linked Purchase Receipts."""
		self.items = []
		total_qty = total_amount = 0
		lines = []

		for pr_row in self.purchase_receipts:
			pr = frappe.get_doc("Purchase Receipt", pr_row.purchase_receipt)
			for item in pr.items:
				lines.append({
					"item_code": item.item_code,
					"warehouse": item.warehouse,
					"pr_qty": item.qty,
					"pr_amount": item.amount,
				})
				total_qty += flt(item.qty)
				total_amount += flt(item.amount)

		for line in lines:
			if self.allocation_method == "By Qty":
				line["allocated_amount"] = (flt(line["pr_qty"]) / total_qty) * flt(self.total_amount) if total_qty else 0
			else:
				line["allocated_amount"] = (flt(line["pr_amount"]) / total_amount) * flt(self.total_amount) if total_amount else 0
			line["allocation_pct"] = (flt(line["allocated_amount"]) / flt(self.total_amount)) * 100 if flt(self.total_amount) else 0
			self.append("items", line)

	def on_submit(self):
		self.db_set("status", "Allocated")
