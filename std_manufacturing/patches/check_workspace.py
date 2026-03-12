import frappe
import json

def execute():
    from frappe.desk.desktop import get_workspace_sidebar_items
    items = get_workspace_sidebar_items()
    pages = items.get('pages', [])
    print(f"Total sidebar pages: {len(pages)}")
    for p in pages:
        print(f"  name={p.get('name', '?')} title={p.get('title', '?')}")
    
    # Check workspace directly
    ws = frappe.get_all("Workspace", filters={"public": 1}, fields=["name", "title", "module", "is_hidden"], limit=30)
    print(f"\nAll public workspaces:")
    for w in ws:
        print(f"  {w.name} | title={w.title} | module={w.module} | hidden={w.is_hidden}")

execute()
