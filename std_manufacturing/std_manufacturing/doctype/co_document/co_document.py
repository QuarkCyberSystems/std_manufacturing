import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class CODocument(Document):
	def validate(self):
		self.calculate_totals()
		self.validate_balance()
		self.validate_lines()

	def calculate_totals(self):
		self.total_debit = sum(flt(line.debit_amount) for line in self.lines)
		self.total_credit = sum(flt(line.credit_amount) for line in self.lines)

	def validate_balance(self):
		if flt(self.total_debit, 2) != flt(self.total_credit, 2):
			frappe.throw(
				_("Total Debit ({0}) must equal Total Credit ({1})").format(
					self.total_debit, self.total_credit
				)
			)

	def validate_lines(self):
		if not self.lines:
			frappe.throw(_("At least one CO Document Line is required"))

		for line in self.lines:
			if flt(line.debit_amount) < 0 or flt(line.credit_amount) < 0:
				frappe.throw(_("Row {0}: Debit and Credit amounts must be non-negative").format(line.idx))

			if flt(line.debit_amount) == 0 and flt(line.credit_amount) == 0:
				frappe.throw(
					_("Row {0}: At least one of Debit or Credit must be non-zero").format(line.idx)
				)
