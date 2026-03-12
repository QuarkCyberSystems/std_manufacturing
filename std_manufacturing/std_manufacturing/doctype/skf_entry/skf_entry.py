import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class SKFEntry(Document):
	def validate(self):
		self.validate_quantity()
		self.validate_duplicate()

	def validate_quantity(self):
		if flt(self.quantity) < 0:
			frappe.throw(_("Quantity must be non-negative"))

	def validate_duplicate(self):
		existing = frappe.db.get_value(
			"SKF Entry",
			{
				"skf": self.skf,
				"period": self.period,
				"cost_center": self.cost_center,
				"docstatus": 1,
				"name": ("!=", self.name),
			},
			"name",
		)
		if existing:
			frappe.throw(
				_("A submitted SKF Entry already exists for {0} / {1} / {2}: {3}").format(
					self.skf, self.period, self.cost_center, existing
				)
			)
