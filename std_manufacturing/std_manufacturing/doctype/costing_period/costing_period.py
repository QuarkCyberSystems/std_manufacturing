import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class CostingPeriod(Document):
	def validate(self):
		self._set_ytd_start()
		self._validate_single_in_progress()

	def _set_ytd_start(self):
		if self.fiscal_year:
			fy = frappe.get_doc("Fiscal Year", self.fiscal_year)
			self.ytd_start_date = fy.year_start_date

	def _validate_single_in_progress(self):
		if self.status == "In Progress":
			existing = frappe.db.exists(
				"Costing Period",
				{
					"company": self.company,
					"status": "In Progress",
					"name": ("!=", self.name),
					"docstatus": 1,
				},
			)
			if existing:
				frappe.throw(
					_("Only one Costing Period can be In Progress per company. {0} is already In Progress.").format(
						existing
					)
				)

	def on_submit(self):
		self.db_set("status", "In Progress")
		self.db_set("current_step", 1)
