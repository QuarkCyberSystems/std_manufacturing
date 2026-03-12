"""
End-to-end test for Standard Cost valuation flow.
Tests: Standard Cost Rate → Purchase Receipt → Stock Entry → PLCV → Revaluation
"""

import frappe
from frappe.utils import today, add_days, getdate, flt
from frappe.tests.utils import FrappeTestCase


class TestStandardCostFlow(FrappeTestCase):

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._setup_test_data()

	@classmethod
	def _setup_test_data(cls):
		"""Create test item, warehouse, accounts, and standard cost rate."""
		frappe.set_user("Administrator")

		# Ensure company exists
		cls.company = frappe.db.get_single_value("Global Defaults", "default_company")
		if not cls.company:
			cls.company = frappe.db.get_value("Company", {}, "name")

		cls.company_abbr = frappe.db.get_value("Company", cls.company, "abbr")

		# Get default warehouse
		cls.warehouse = frappe.db.get_value(
			"Warehouse", {"company": cls.company, "is_group": 0}, "name"
		)
		if not cls.warehouse:
			cls.warehouse = f"Stores - {cls.company_abbr}"

		# Create test item
		if not frappe.db.exists("Item", "TEST-COAL-STD"):
			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": "TEST-COAL-STD",
				"item_name": "Test Coal Standard Cost",
				"item_group": "Raw Material",
				"stock_uom": "Nos",
				"is_stock_item": 1,
				"custom_valuation_method": "Standard Cost",
				"custom_cost_category": "Purchased",
				"custom_include_in_plcv": 1,
				"standard_rate": 155,
			})
			item.insert()

		# Get or set stock adjustment account
		cls.stock_adjustment_account = frappe.db.get_value(
			"Company", cls.company, "stock_adjustment_account"
		)

	def test_01_standard_cost_rate_creation(self):
		"""Test creating and activating a Standard Cost Rate."""
		scr = frappe.get_doc({
			"doctype": "Standard Cost Rate",
			"item_code": "TEST-COAL-STD",
			"standard_rate": 155,
			"effective_from": "2026-01-01",
			"rate_basis": "Budget",
			"fiscal_year": frappe.db.get_value("Fiscal Year", {"disabled": 0}, "name"),
		})
		scr.insert()
		scr.submit()

		# Should be Active after submit
		scr.reload()
		self.assertEqual(scr.status, "Active")

		# Item.standard_rate should be updated
		item_rate = frappe.db.get_value("Item", "TEST-COAL-STD", "standard_rate")
		self.assertEqual(flt(item_rate), 155)

	def test_02_get_active_standard_rate(self):
		"""Test the rate lookup API."""
		from std_manufacturing.std_manufacturing.doctype.standard_cost_rate.standard_cost_rate import (
			get_active_standard_rate,
		)

		# Should find rate for Jan 15
		rate = get_active_standard_rate("TEST-COAL-STD", "2026-01-15")
		self.assertIsNotNone(rate)
		self.assertEqual(flt(rate.standard_rate), 155)

		# Should NOT find rate before effective date
		rate_before = get_active_standard_rate("TEST-COAL-STD", "2025-12-31")
		self.assertIsNone(rate_before)

	def test_03_purchase_receipt_standard_cost(self):
		"""Test Purchase Receipt hook overrides valuation_rate."""
		# Create a supplier
		supplier = self._get_or_create_supplier()

		# Create Purchase Receipt with actual rate = 165
		pr = frappe.get_doc({
			"doctype": "Purchase Receipt",
			"supplier": supplier,
			"company": self.company,
			"posting_date": "2026-01-15",
			"items": [{
				"item_code": "TEST-COAL-STD",
				"qty": 1000,
				"rate": 165,
				"warehouse": self.warehouse,
			}],
		})
		pr.insert()
		pr.submit()

		pr.reload()
		item = pr.items[0]

		# Valuation rate should be overridden to Standard Rate
		self.assertEqual(flt(item.valuation_rate), 155)

		# Price variance should be calculated
		self.assertEqual(flt(item.custom_standard_rate_applied), 155)
		self.assertEqual(flt(item.custom_price_variance), (165 - 155) * 1000)  # 10,000

		# SLE should have standard rate
		sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": pr.name, "item_code": "TEST-COAL-STD"},
			["incoming_rate", "stock_value_difference"],
			as_dict=True,
		)
		self.assertEqual(flt(sle.incoming_rate), 155)
		self.assertEqual(flt(sle.stock_value_difference), 155 * 1000)  # 155,000

	def test_04_stock_entry_standard_cost(self):
		"""Test Stock Entry hook uses standard rate for issues."""
		# Create material issue
		se = frappe.get_doc({
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Issue",
			"company": self.company,
			"posting_date": "2026-01-20",
			"items": [{
				"item_code": "TEST-COAL-STD",
				"qty": 500,
				"s_warehouse": self.warehouse,
			}],
		})
		se.insert()
		se.submit()

		se.reload()
		item = se.items[0]
		self.assertEqual(flt(item.valuation_rate), 155)
		self.assertEqual(flt(item.basic_rate), 155)

	def test_05_plcv_entry_calculation(self):
		"""Test PLCV Entry calculates YTD CPU and variance."""
		plcv = frappe.get_doc({
			"doctype": "PLCV Entry",
			"costing_period": self._get_or_create_costing_period(),
			"item_code": "TEST-COAL-STD",
			"cost_category": "Purchased",
			"opening_qty": 0,
			"opening_value": 0,
			"ytd_purchase_qty": 1000,
			"ytd_purchase_value": 165000,  # Actual total from PR (1000 * 165)
			"ytd_cost_pool_amount": 0,
			"standard_rate": 155,
			"closing_stock_qty": 500,
			"ytd_issued_qty": 500,
		})
		plcv.insert()

		# YTD Actual CPU should be calculated
		self.assertEqual(flt(plcv.ytd_actual_cpu, 2), 165.00)

		# Variance
		self.assertEqual(flt(plcv.variance_per_unit, 2), 10.00)  # 165 - 155

		# Total variance = 10 * 1000 = 10,000
		self.assertEqual(flt(plcv.total_variance, 2), 10000.00)

		# COGS variance = 10,000 * (500/1000) = 5,000
		self.assertEqual(flt(plcv.cogs_variance, 2), 5000.00)

		# Inventory variance = 10,000 * (500/1000) = 5,000
		self.assertEqual(flt(plcv.inventory_variance, 2), 5000.00)

		plcv.submit()
		plcv.reload()
		self.assertEqual(plcv.status, "Calculated")

	def test_06_standard_cost_revaluation(self):
		"""Test Standard Cost Revaluation creates Stock Reconciliation."""
		if not self.stock_adjustment_account:
			return

		scr = frappe.get_doc({
			"doctype": "Standard Cost Revaluation",
			"company": self.company,
			"posting_date": "2026-01-31",
			"source_type": "PLCV",
			"rate_derivation_method": "YTD",
			"costing_period": self._get_or_create_costing_period(),
			"items": [{
				"item_code": "TEST-COAL-STD",
				"warehouse": self.warehouse,
				"current_standard_rate": 155,
				"new_standard_rate": 165,
				"closing_qty": 500,
			}],
		})
		scr.insert()

		# Revaluation amount should be calculated
		self.assertEqual(flt(scr.items[0].revaluation_amount), (165 - 155) * 500)  # 5,000
		self.assertEqual(flt(scr.total_revaluation_amount), 5000)

		scr.submit()
		scr.reload()

		# Stock Reconciliation should be created
		self.assertTrue(scr.stock_reconciliation)
		self.assertEqual(scr.status, "Submitted")

		# Item.standard_rate should be updated to 165
		item_rate = frappe.db.get_value("Item", "TEST-COAL-STD", "standard_rate")
		self.assertEqual(flt(item_rate), 165)

		# New Standard Cost Rate record should exist
		new_scr_rate = frappe.db.exists(
			"Standard Cost Rate",
			{"item_code": "TEST-COAL-STD", "standard_rate": 165, "status": "Active"},
		)
		self.assertTrue(new_scr_rate)

	def _get_or_create_supplier(self):
		if not frappe.db.exists("Supplier", "Test Supplier STD"):
			frappe.get_doc({
				"doctype": "Supplier",
				"supplier_name": "Test Supplier STD",
				"supplier_group": frappe.db.get_value("Supplier Group", {}, "name"),
			}).insert()
		return "Test Supplier STD"

	def _get_or_create_costing_period(self):
		# Auto-naming uses format CP-{abbr}-{period_start}
		existing = frappe.db.get_value(
			"Costing Period",
			{"company": self.company, "period_start": "2026-01-01"},
			"name",
		)
		if existing:
			return existing

		fy = frappe.db.get_value("Fiscal Year", {"disabled": 0}, "name")
		cp = frappe.get_doc({
			"doctype": "Costing Period",
			"period_name": "January 2026",
			"company": self.company,
			"fiscal_year": fy,
			"period_start": "2026-01-01",
			"period_end": "2026-01-31",
		})
		cp.insert()
		cp.submit()
		return cp.name
