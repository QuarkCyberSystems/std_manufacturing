import frappe
import json

def execute():
	# Simulate what boot.py does
	from frappe.boot import get_sidebar_items
	sidebar_items = get_sidebar_items()

	print(f"Total sidebar sections: {len(sidebar_items)}")
	for key, val in sidebar_items.items():
		marker = " <<<" if "costing" in key.lower() or "standard" in key.lower() else ""
		items_count = len(val.get("items", []))
		print(f"  '{key}' — {items_count} items, app={val.get('app', '?')}{marker}")

	# Also check desktop API
	from frappe.desk.desktop import get_workspace_sidebar_items
	desk_items = get_workspace_sidebar_items()
	pages = desk_items.get("pages", [])
	print(f"\nDesktop sidebar pages: {len(pages)}")
	for p in pages:
		name = p.get("name", "?")
		marker = " <<<" if "costing" in name.lower() or "standard" in name.lower() else ""
		print(f"  {name}{marker}")

	# Check if "Standard Costing" workspace page exists (linked from sidebar Home item)
	ws_exists = frappe.db.exists("Workspace", "Standard Costing")
	print(f"\nWorkspace 'Standard Costing' exists: {ws_exists}")

execute()
