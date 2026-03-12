import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class AllocationCycle(Document):
	def validate(self):
		self.validate_cost_element()
		self.validate_receivers()

	def validate_cost_element(self):
		ce_type = frappe.db.get_value("Cost Element", self.secondary_cost_element, "cost_element_type")
		if ce_type != "Secondary":
			frappe.throw(
				_("Cost Element {0} must be of type Secondary for allocation cycles").format(
					self.secondary_cost_element
				)
			)

	def validate_receivers(self):
		if not self.receivers:
			frappe.throw(_("At least one receiver is required"))

		# Check sender is not in receivers
		for row in self.receivers:
			if row.cost_center == self.sender_cost_center:
				frappe.throw(
					_("Row {0}: Sender cost center cannot be a receiver").format(row.idx)
				)

		# For Fixed Percentage, validate sum = 100
		if self.tracing_type == "Fixed Percentage":
			total_pct = sum(flt(row.fixed_percentage) for row in self.receivers)
			if abs(total_pct - 100.0) > 0.01:
				frappe.throw(
					_("Fixed percentages must sum to 100% (currently {0}%)").format(total_pct)
				)
