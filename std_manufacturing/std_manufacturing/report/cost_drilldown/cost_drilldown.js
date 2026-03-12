frappe.query_reports["Cost Drilldown"] = {
	filters: [
		{
			fieldname: "period",
			label: __("Costing Period"),
			fieldtype: "Link",
			options: "Costing Period",
			reqd: 1,
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "Link",
			options: "Cost Center",
		},
		{
			fieldname: "show_detail",
			label: __("Show Source Breakdown"),
			fieldtype: "Check",
			default: 0,
		},
	],
	tree: true,
	name_field: "label",
	parent_field: "parent_label",
	initial_depth: 1,
};
