import frappe
from frappe import _
from frappe.model.document import Document


class AllocationRun(Document):
	def validate(self):
		self.validate_no_existing_run()

	def validate_no_existing_run(self):
		existing = frappe.db.get_value(
			"Allocation Run",
			{
				"period": self.period,
				"docstatus": 1,
				"name": ("!=", self.name),
			},
			"name",
		)
		if existing:
			frappe.throw(
				_("A submitted Allocation Run already exists for period {0}: {1}").format(
					self.period, existing
				)
			)

	def on_cancel(self):
		self.cancel_co_documents()

	def cancel_co_documents(self):
		for row in self.cycle_results:
			if row.co_document and row.status == "Completed":
				co_doc = frappe.get_doc("CO Document", row.co_document)
				if co_doc.docstatus == 1:
					co_doc.cancel()
