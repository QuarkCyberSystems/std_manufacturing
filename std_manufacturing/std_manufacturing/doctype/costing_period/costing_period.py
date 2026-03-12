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


@frappe.whitelist()
def run_primary_mirror(costing_period):
	"""Step 1: Run Primary CO Mirror — copies GL Entries to CO Documents."""
	from std_manufacturing.api.co_balance import run_primary_co_mirror

	count = run_primary_co_mirror(costing_period)
	if count:
		frappe.db.set_value("Costing Period", costing_period, "primary_mirror_status", "Completed")
		frappe.db.set_value("Costing Period", costing_period, "current_step", 2)
		frappe.db.commit()
	return count


@frappe.whitelist()
def run_allocation(costing_period):
	"""Step 3: Run CO Allocation — executes all active allocation cycles."""
	from std_manufacturing.api.allocation_engine import execute_allocation_run

	period_doc = frappe.get_doc("Costing Period", costing_period)
	if period_doc.docstatus != 1:
		frappe.throw(_("Costing Period must be submitted"))

	frappe.db.set_value("Costing Period", costing_period, "allocation_status", "Running")
	frappe.db.commit()

	try:
		run_name = execute_allocation_run(costing_period)
		frappe.db.set_value("Costing Period", costing_period, "allocation_status", "Completed")
		frappe.db.set_value("Costing Period", costing_period, "current_step", 4)
		frappe.db.commit()
		return run_name
	except Exception:
		frappe.db.set_value("Costing Period", costing_period, "allocation_status", "Pending")
		frappe.db.commit()
		raise


@frappe.whitelist()
def close_period(costing_period):
	"""Final step: Mark the costing period as Completed."""
	period_doc = frappe.get_doc("Costing Period", costing_period)
	if period_doc.docstatus != 1:
		frappe.throw(_("Costing Period must be submitted"))

	frappe.db.set_value("Costing Period", costing_period, "status", "Completed")
	frappe.db.commit()
	frappe.msgprint(_("Costing Period {0} has been closed").format(costing_period))
