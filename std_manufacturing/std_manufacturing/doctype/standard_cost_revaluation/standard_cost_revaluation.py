import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, add_days


class StandardCostRevaluation(Document):
	def validate(self):
		self._calculate_revaluation_amounts()

	def _calculate_revaluation_amounts(self):
		total = 0
		for row in self.items:
			row.revaluation_amount = (flt(row.new_standard_rate) - flt(row.current_standard_rate)) * flt(row.closing_qty)
			total += flt(row.revaluation_amount)
		self.total_revaluation_amount = total

	def on_submit(self):
		self._update_standard_rates()
		self._create_stock_reconciliation()
		self._create_standard_cost_rate_records()
		self.db_set("status", "Submitted")

	def _update_standard_rates(self):
		for row in self.items:
			frappe.db.set_value("Item", row.item_code, "standard_rate", row.new_standard_rate)

	def _create_stock_reconciliation(self):
		# Get default expense account for stock adjustment
		expense_account = frappe.db.get_value(
			"Company", self.company, "stock_adjustment_account"
		)
		if not expense_account:
			frappe.throw(_("Please set Stock Adjustment Account in Company {0}").format(self.company))

		sr = frappe.new_doc("Stock Reconciliation")
		sr.company = self.company
		sr.posting_date = self.posting_date
		sr.purpose = "Stock Reconciliation"
		sr.expense_account = expense_account

		for row in self.items:
			if flt(row.closing_qty) > 0 and flt(row.revaluation_amount) != 0:
				sr.append("items", {
					"item_code": row.item_code,
					"warehouse": row.warehouse,
					"qty": row.closing_qty,
					"valuation_rate": row.new_standard_rate,
				})

		if sr.items:
			sr.insert()
			sr.submit()
			self.db_set("stock_reconciliation", sr.name)

	def _create_standard_cost_rate_records(self):
		"""Create new Standard Cost Rate records with the updated rates."""
		next_day = add_days(self.posting_date, 1)

		for row in self.items:
			if flt(row.new_standard_rate) == flt(row.current_standard_rate):
				continue

			scr = frappe.new_doc("Standard Cost Rate")
			scr.item_code = row.item_code
			scr.standard_rate = row.new_standard_rate
			scr.effective_from = next_day
			scr.rate_basis = "PLCV Actual" if self.source_type == "PLCV" else "Manual"
			scr.costing_period = self.costing_period
			scr.remarks = f"Created by Standard Cost Revaluation {self.name}"
			scr.insert()
			scr.submit()

	def on_cancel(self):
		# Revert standard rates
		for row in self.items:
			frappe.db.set_value("Item", row.item_code, "standard_rate", row.current_standard_rate)

		# Cancel stock reconciliation
		if self.stock_reconciliation:
			sr = frappe.get_doc("Stock Reconciliation", self.stock_reconciliation)
			if sr.docstatus == 1:
				sr.cancel()

		self.db_set("status", "Cancelled")
