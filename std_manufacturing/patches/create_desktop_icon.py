import frappe


def execute():
	# Delete and recreate to ensure clean state
	if frappe.db.exists("Desktop Icon", {"label": "Standard Costing"}):
		frappe.delete_doc("Desktop Icon", "Standard Costing", force=True)

	di = frappe.new_doc("Desktop Icon")
	di.label = "Standard Costing"
	di.icon_type = "Link"
	di.link_type = "Workspace Sidebar"
	di.standard = 1
	di.app = "std_manufacturing"
	di.icon = "accounting"
	di.bg_color = "blue"
	di.insert(ignore_permissions=True)
	frappe.db.commit()
	print(f"Created: {di.name}")
