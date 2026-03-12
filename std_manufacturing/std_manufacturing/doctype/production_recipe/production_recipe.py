import frappe
from frappe import _
from frappe.model.document import Document


class ProductionRecipe(Document):
	def validate(self):
		self.validate_output_not_in_inputs()
		self.validate_phase_sequence()

	def validate_output_not_in_inputs(self):
		input_items = [row.item_code for row in self.input_items]
		if self.output_item in input_items:
			frappe.throw(
				_("Output item {0} cannot also be listed as an input material").format(
					self.output_item
				)
			)

	def validate_phase_sequence(self):
		if self.phase_sequence and self.phase_sequence < 0:
			frappe.throw(_("Phase Sequence must be a positive number"))
