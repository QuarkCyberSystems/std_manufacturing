import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class StandardCostRate(Document):
	def validate(self):
		if self.standard_rate <= 0:
			frappe.throw(_("Standard Rate must be greater than zero"))

		if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
			frappe.throw(_("Effective To must be on or after Effective From"))

	def on_submit(self):
		self._supersede_previous_rate()
		self._update_item_standard_rate()
		self.db_set("status", "Active")

	def _supersede_previous_rate(self):
		"""Auto-supersede any previous open-ended active rate for the same item."""
		previous = frappe.db.get_all(
			"Standard Cost Rate",
			filters={
				"item_code": self.item_code,
				"status": "Active",
				"name": ("!=", self.name),
				"docstatus": 1,
			},
			fields=["name", "effective_from"],
			order_by="effective_from desc",
		)
		for rate in previous:
			day_before = frappe.utils.add_days(self.effective_from, -1)
			frappe.db.set_value(
				"Standard Cost Rate", rate.name, {
					"status": "Superseded",
					"effective_to": day_before,
				}
			)

	def _update_item_standard_rate(self):
		"""Update Item.standard_rate to the new active rate."""
		frappe.db.set_value("Item", self.item_code, "standard_rate", self.standard_rate)

	def on_cancel(self):
		# Check if any PLCV Entries reference this rate
		plcv_refs = frappe.db.count(
			"PLCV Entry",
			filters={
				"item_code": self.item_code,
				"standard_rate": self.standard_rate,
				"status": ("in", ["Calculated", "Posted"]),
				"docstatus": 1,
			},
		)
		if plcv_refs:
			frappe.throw(
				_("Cannot cancel: {0} PLCV Entries reference this rate").format(plcv_refs)
			)
		self.db_set("status", "Cancelled")


def get_active_standard_rate(item_code, as_of_date):
	"""
	Returns the active Standard Cost Rate for an item on a given date.
	Called by:
	  - Purchase Receipt hook (to get rate for valuation override)
	  - PLCV engine (to get rate for variance calculation)
	Returns dict {name, standard_rate, effective_from, rate_basis} or None.
	"""
	as_of_date = getdate(as_of_date)
	rate = frappe.db.get_value(
		"Standard Cost Rate",
		filters={
			"item_code": item_code,
			"status": "Active",
			"effective_from": ("<=", as_of_date),
			"docstatus": 1,
		},
		fieldname=["name", "standard_rate", "effective_from", "effective_to", "rate_basis"],
		as_dict=True,
		order_by="effective_from desc",
	)
	if not rate:
		return None
	if rate.effective_to and getdate(rate.effective_to) < as_of_date:
		return None
	return rate
