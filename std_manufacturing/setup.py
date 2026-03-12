import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


CUSTOM_FIELDS = {
	"Item": [
		{
			"fieldname": "custom_valuation_method",
			"fieldtype": "Select",
			"label": "Valuation Method (Custom)",
			"options": "\nMoving Average\nStandard Cost",
			"insert_after": "valuation_method",
			"description": "Overrides default valuation. Set to Standard Cost for standard costing items.",
		},
		{
			"fieldname": "custom_cost_category",
			"fieldtype": "Select",
			"label": "Cost Category",
			"options": "\nPurchased\nSemi-Finished\nFinished",
			"insert_after": "custom_valuation_method",
			"description": "Drives PLCV calculation path",
		},
		{
			"fieldname": "custom_include_in_plcv",
			"fieldtype": "Check",
			"label": "Include in PLCV",
			"insert_after": "custom_cost_category",
			"description": "Include in period-end YTD cycle",
		},
		{
			"fieldname": "custom_production_recipe",
			"fieldtype": "Link",
			"label": "Default Production Recipe",
			"options": "Production Recipe",
			"insert_after": "custom_include_in_plcv",
			"description": "Default recipe for producing this item",
		},
	],
	"Purchase Receipt Item": [
		{
			"fieldname": "custom_standard_rate_applied",
			"fieldtype": "Currency",
			"label": "Standard Rate Applied",
			"insert_after": "valuation_rate",
			"read_only": 1,
			"description": "The Standard Rate used for this receipt",
		},
		{
			"fieldname": "custom_price_variance",
			"fieldtype": "Currency",
			"label": "Price Variance",
			"insert_after": "custom_standard_rate_applied",
			"read_only": 1,
			"description": "(rate - standard_rate) x qty",
		},
	],
	"Company": [
		{
			"fieldname": "custom_plcv_variance_cogs_account",
			"fieldtype": "Link",
			"label": "PLCV Variance — COGS Account",
			"options": "Account",
			"insert_after": "stock_adjustment_account",
			"description": "PLCV Variance COGS account for period-end variance posting",
		},
		{
			"fieldname": "custom_plcv_variance_inventory_account",
			"fieldtype": "Link",
			"label": "PLCV Variance — Inventory Account",
			"options": "Account",
			"insert_after": "custom_plcv_variance_cogs_account",
			"description": "PLCV Variance Inventory account (tracked, optional)",
		},
		{
			"fieldname": "custom_purchase_price_variance_account",
			"fieldtype": "Link",
			"label": "Purchase Price Variance Account",
			"options": "Account",
			"insert_after": "custom_plcv_variance_inventory_account",
			"description": "Default Purchase Price Variance account for Standard Cost items",
		},
	],
	"Account": [
		{
			"fieldname": "custom_cost_element",
			"fieldtype": "Link",
			"label": "Cost Element",
			"options": "Cost Element",
			"insert_after": "account_type",
			"description": "Maps this GL Account to a CO Cost Element for controlling postings",
		},
	],
	"Job Card": [
		{
			"fieldname": "custom_kwh_consumed",
			"fieldtype": "Float",
			"label": "KWH Consumed",
			"insert_after": "total_completed_qty",
			"default": "0",
			"description": "Electricity consumed during this job (KWH)",
		},
	],
}


def setup_custom_fields():
	create_custom_fields(CUSTOM_FIELDS, update=True)
	frappe.db.commit()
