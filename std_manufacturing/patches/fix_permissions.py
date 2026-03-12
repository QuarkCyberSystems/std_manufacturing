import frappe

def execute():
	# Check and fix DocType permissions
	for dt in ["Standard Cost Rate", "Costing Period", "PLCV Entry", "Cost Pool", "Standard Cost Revaluation"]:
		perms = frappe.get_all("DocPerm", filters={"parent": dt}, fields=["role", "read", "write", "create", "submit", "cancel"], order_by="idx")
		if perms:
			print(f"{dt}:")
			for p in perms:
				print(f"  {p.role}: read={p.read} write={p.write} create={p.create} submit={p.submit} cancel={p.cancel}")
		else:
			print(f"{dt}: NO PERMISSIONS — adding now")
			doc = frappe.get_doc("DocType", dt)
			doc.append("permissions", {
				"role": "System Manager",
				"read": 1,
				"write": 1,
				"create": 1,
				"delete": 1,
				"submit": 1 if doc.is_submittable else 0,
				"cancel": 1 if doc.is_submittable else 0,
				"amend": 1 if doc.is_submittable else 0,
			})
			doc.append("permissions", {
				"role": "Accounts Manager",
				"read": 1,
				"write": 1,
				"create": 1,
				"delete": 1,
				"submit": 1 if doc.is_submittable else 0,
				"cancel": 1 if doc.is_submittable else 0,
				"amend": 1 if doc.is_submittable else 0,
			})
			doc.append("permissions", {
				"role": "Accounts User",
				"read": 1,
				"write": 1,
				"create": 1,
				"submit": 1 if doc.is_submittable else 0,
				"cancel": 0,
			})
			doc.save()
			print(f"  Added permissions for System Manager, Accounts Manager, Accounts User")

	frappe.db.commit()
	print("\nDone.")

execute()
