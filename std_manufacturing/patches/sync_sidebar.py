import frappe
from frappe.modules.import_file import import_file_by_path


def execute():
	"""Delete and re-sync the Standard Costing workspace sidebar from JSON."""
	if frappe.db.exists("Workspace Sidebar", "Standard Costing"):
		frappe.delete_doc("Workspace Sidebar", "Standard Costing", force=True)
		frappe.db.commit()
		print("Deleted old sidebar")

	# Import directly from the JSON file
	import os
	json_path = os.path.join(
		frappe.get_app_path("std_manufacturing"),
		"workspace_sidebar",
		"standard_costing.json",
	)
	import_file_by_path(json_path, force=True)
	frappe.db.commit()

	doc = frappe.get_doc("Workspace Sidebar", "Standard Costing")
	print(f"Synced sidebar: {len(doc.items)} items")
	for item in doc.items:
		print(f"  {item.type}: {item.label} -> {item.link_to or ''}")
