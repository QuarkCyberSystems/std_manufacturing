import frappe
from frappe import _
from frappe.model.document import Document


class CostElement(Document):
	def validate(self):
		if self.cost_element_type == "Primary" and not self.gl_account:
			frappe.throw(_("GL Account is mandatory for Primary cost elements"))

		if self.cost_element_type == "Secondary" and not self.secondary_category:
			frappe.throw(_("Secondary Category is mandatory for Secondary cost elements"))

		if self.cost_element_type == "Primary" and self.gl_account:
			existing = frappe.db.get_value(
				"Cost Element",
				{"gl_account": self.gl_account, "name": ("!=", self.name)},
				"name",
			)
			if existing:
				frappe.throw(
					_("GL Account {0} is already mapped to Cost Element {1}").format(
						self.gl_account, existing
					)
				)
