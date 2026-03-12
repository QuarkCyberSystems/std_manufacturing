import frappe

def execute():
	# Create Module Def if missing
	if not frappe.db.exists("Module Def", "Std Manufacturing"):
		md = frappe.get_doc({
			"doctype": "Module Def",
			"module_name": "Std Manufacturing",
			"app_name": "std_manufacturing",
		})
		md.insert(ignore_permissions=True)
		frappe.db.commit()
		print("Created Module Def: Std Manufacturing")
	else:
		print("Module Def already exists")

	# Check DocTypes
	for dt in [
		"Standard Cost Rate", "Costing Period", "PLCV Entry", "Cost Pool",
		"Standard Cost Revaluation", "Cost Pool Purchase Receipt",
		"Cost Pool Item", "Standard Cost Revaluation Item",
	]:
		exists = frappe.db.exists("DocType", dt)
		print(f"  {dt}: {'EXISTS' if exists else 'MISSING'}")

execute()
