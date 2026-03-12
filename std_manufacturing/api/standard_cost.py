import frappe
from frappe import _
from frappe.utils import flt

from std_manufacturing.std_manufacturing.doctype.standard_cost_rate.standard_cost_rate import (
	get_active_standard_rate,
)


def enforce_standard_rate_on_receipt(doc, method):
	"""
	Purchase Receipt — before_submit hook.
	For Standard Cost items: override valuation_rate with active Standard Cost Rate.
	Post price variance to Purchase Price Variance account.
	"""
	for item in doc.items:
		item_doc = frappe.get_cached_doc("Item", item.item_code)

		if not item_doc.get("custom_valuation_method") or item_doc.custom_valuation_method != "Standard Cost":
			continue

		rate_record = get_active_standard_rate(item.item_code, doc.posting_date)
		if not rate_record:
			frappe.throw(
				_("No active Standard Cost Rate for {0} on {1}").format(item.item_code, doc.posting_date)
			)

		std_rate = flt(rate_record.standard_rate)
		actual_rate = flt(item.rate)

		# Calculate price variance BEFORE overriding the rate
		item.custom_price_variance = (actual_rate - std_rate) * flt(item.qty)
		item.custom_standard_rate_applied = std_rate

		# Override valuation rate — SLE will use this
		item.valuation_rate = std_rate


def enforce_standard_rate_on_entry(doc, method):
	"""
	Stock Entry — before_submit hook.
	For Material Issue / Transfer / Manufacture:
	ensure outgoing rate = Standard Rate.
	"""
	for item in doc.items:
		item_doc = frappe.get_cached_doc("Item", item.item_code)

		if not item_doc.get("custom_valuation_method") or item_doc.custom_valuation_method != "Standard Cost":
			continue

		std_rate = flt(item_doc.standard_rate)
		if std_rate > 0:
			item.valuation_rate = std_rate
			item.basic_rate = std_rate


def check_freight_invoice(doc, method):
	"""
	Purchase Invoice — on_submit hook.
	If PI is against a freight/logistics account with no stock receipt,
	prompt user to link to a Cost Pool.
	"""
	# Get freight accounts from company custom field (if configured)
	freight_account = frappe.db.get_value(
		"Company", doc.company, "custom_purchase_price_variance_account"
	)
	if not freight_account:
		return

	for item in doc.items:
		if item.expense_account == freight_account and not item.purchase_receipt:
			frappe.msgprint(
				_("Invoice {0} line {1} may be a freight charge. "
				  "Please create a Cost Pool entry to allocate this to materials.").format(
					doc.name, item.idx
				),
				indicator="orange",
				alert=True,
			)
