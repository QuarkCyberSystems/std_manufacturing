frappe.query_reports["Product Cost Drilldown"] = {
	filters: [
		{
			fieldname: "period",
			label: __("Costing Period"),
			fieldtype: "Link",
			options: "Costing Period",
			reqd: 1,
		},
		{
			fieldname: "production_phase",
			label: __("Production Phase"),
			fieldtype: "Link",
			options: "Production Phase",
		},
		{
			fieldname: "output_item",
			label: __("Output Item"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "show_ytd",
			label: __("Show YTD"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: "show_inputs",
			label: __("Show Input Breakdown"),
			fieldtype: "Check",
			default: 0,
		},
	],
	tree: true,
	name_field: "label",
	parent_field: "parent_label",
	initial_depth: 1,
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "cost_variance" && data && data.cost_variance) {
			if (data.cost_variance > 0) {
				value = `<span style="color: var(--red-500)">${value}</span>`;
			} else if (data.cost_variance < 0) {
				value = `<span style="color: var(--green-500)">${value}</span>`;
			}
		}
		if (column.fieldname === "variance_pct" && data && data.variance_pct) {
			if (data.variance_pct > 5) {
				value = `<span style="color: var(--red-500)">${value}</span>`;
			} else if (data.variance_pct < -5) {
				value = `<span style="color: var(--green-500)">${value}</span>`;
			}
		}
		return value;
	},
};
