import frappe

def execute():
	# Check what allowed_workspaces looks like
	from frappe.desk.desktop import get_workspace_sidebar_items
	result = get_workspace_sidebar_items()
	pages = result.get("pages", [])
	print("Allowed workspace pages:")
	for p in pages:
		print(f"  {p.get('name', '?')}")

	# Check what get_sidebar_items returns
	from frappe.boot import get_sidebar_items
	allowed = [p.get("name") for p in pages]
	sidebar = get_sidebar_items(allowed)
	print(f"\nSidebar sections: {len(sidebar)}")
	for key, val in sidebar.items():
		items_count = len(val.get("items", []))
		print(f"  '{key}' — {items_count} items")
		if "costing" in key.lower() or "standard" in key.lower():
			print(f"    FOUND! Details:")
			for item in val.get("items", []):
				print(f"      {item.get('type')}: {item.get('label')} -> {item.get('link_to')} ({item.get('link_type')})")

execute()
