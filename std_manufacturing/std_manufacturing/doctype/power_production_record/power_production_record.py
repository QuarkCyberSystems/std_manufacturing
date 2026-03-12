import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PowerProductionRecord(Document):
	def validate(self):
		self.calculate_totals()
		self.validate_consumption()

	def calculate_totals(self):
		self.total_kwh_pool = flt(self.total_kwh_generated) + flt(self.dewa_kwh_purchased)
		self.total_kwh_consumed = sum(flt(row.kwh_consumed) for row in self.kwh_consumption_table)
		self.general_service_kwh = flt(self.total_kwh_pool) - flt(self.total_kwh_consumed)

	def validate_consumption(self):
		for row in self.kwh_consumption_table:
			if flt(row.kwh_consumed) < 0:
				frappe.throw(
					_("Row {0}: KWH Consumed cannot be negative for {1}").format(
						row.idx, row.cost_center
					)
				)

		if flt(self.general_service_kwh) < 0:
			frappe.throw(
				_("Total KWH consumed ({0}) exceeds KWH pool ({1})").format(
					self.total_kwh_consumed, self.total_kwh_pool
				)
			)

	def on_submit(self):
		self.create_skf_entries()

	def on_cancel(self):
		self.cancel_skf_entries()

	def create_skf_entries(self):
		kwh_skf = frappe.db.get_value(
			"Statistical Key Figure", {"skf_code": "KWH-TOTAL"}, "name"
		)
		if not kwh_skf:
			frappe.throw(_("Statistical Key Figure 'KWH-TOTAL' not found. Please create it first."))

		for row in self.kwh_consumption_table:
			if flt(row.kwh_consumed) <= 0:
				continue

			entry = frappe.new_doc("SKF Entry")
			entry.skf = kwh_skf
			entry.period = self.costing_period
			entry.cost_center = row.cost_center
			entry.quantity = row.kwh_consumed
			entry.entry_source = "KWH Import"
			entry.source_reference = self.name
			entry.entry_date = self.end_date or frappe.utils.today()
			entry.insert(ignore_permissions=True)
			entry.submit()

		# Add general service KWH entry
		if flt(self.general_service_kwh) > 0 and self.general_service_cc:
			entry = frappe.new_doc("SKF Entry")
			entry.skf = kwh_skf
			entry.period = self.costing_period
			entry.cost_center = self.general_service_cc
			entry.quantity = self.general_service_kwh
			entry.entry_source = "KWH Import"
			entry.source_reference = self.name
			entry.entry_date = self.end_date or frappe.utils.today()
			entry.insert(ignore_permissions=True)
			entry.submit()

		self.db_set("skf_entries_posted", 1)

	def cancel_skf_entries(self):
		entries = frappe.get_all(
			"SKF Entry",
			filters={
				"source_reference": self.name,
				"entry_source": "KWH Import",
				"docstatus": 1,
			},
			pluck="name",
		)
		for entry_name in entries:
			entry = frappe.get_doc("SKF Entry", entry_name)
			entry.cancel()

		self.db_set("skf_entries_posted", 0)
