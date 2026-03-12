import frappe

def execute():
	sidebars = frappe.get_all("Workspace Sidebar", fields=["name", "title", "module", "app", "standard"], limit=30)
	print(f"Total Workspace Sidebars: {len(sidebars)}")
	for s in sidebars:
		marker = " <<<" if "standard" in s.title.lower() or "costing" in s.title.lower() else ""
		print(f"  {s.name} | title={s.title} | module={s.module} | app={s.app} | std={s.standard}{marker}")

execute()
