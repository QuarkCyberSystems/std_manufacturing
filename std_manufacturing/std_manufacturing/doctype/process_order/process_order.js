frappe.ui.form.on("Process Order", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.status === "Open") {
			// Calculate Unit Costs button
			frm.add_custom_button(
				__("Calculate Unit Costs"),
				() => {
					frappe.call({
						method: "std_manufacturing.api.process_order.calculate_unit_costs",
						args: { process_order: frm.doc.name },
						freeze: true,
						freeze_message: __("Calculating unit costs..."),
						callback: (r) => {
							frm.reload_doc();
						},
					});
				},
				__("Actions")
			);

			// Close Process Order
			frm.add_custom_button(
				__("Close"),
				() => {
					frappe.confirm(
						__("Close this Process Order? This marks production as finalized for this period."),
						() => {
							frappe.call({
								method: "frappe.client.set_value",
								args: {
									doctype: "Process Order",
									name: frm.doc.name,
									fieldname: "status",
									value: "Closed",
								},
								callback: (r) => {
									frm.reload_doc();
								},
							});
						}
					);
				},
				__("Actions")
			);
		}

		// View links
		if (frm.doc.costing_period) {
			frm.add_custom_button(
				__("Cost Drilldown"),
				() => {
					frappe.set_route("query-report", "Cost Drilldown", {
						period: frm.doc.costing_period,
					});
				},
				__("View")
			);
		}

		if (frm.doc.cost_center && frm.doc.costing_period) {
			frm.add_custom_button(
				__("CO Documents"),
				() => {
					frappe.set_route("List", "CO Document", {
						period: frm.doc.costing_period,
					});
				},
				__("View")
			);
		}
	},

	production_recipe(frm) {
		if (frm.doc.production_recipe && !frm.doc.docstatus) {
			// Pre-populate input rows from recipe when recipe is selected
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Production Recipe",
					name: frm.doc.production_recipe,
				},
				callback: (r) => {
					if (r.message && r.message.input_items) {
						frm.clear_table("input_entries");
						r.message.input_items.forEach((item) => {
							let row = frm.add_child("input_entries");
							row.item_code = item.item_code;
							row.item_name = item.item_name;
							row.uom = item.uom;
							row.source_warehouse = item.source_warehouse;
							row.movement_type = "Consumption";
						});
						frm.refresh_field("input_entries");
					}

					// Pre-populate output row
					if (r.message && r.message.output_item) {
						if (frm.doc.output_entries.length === 0) {
							let row = frm.add_child("output_entries");
							row.item_code = r.message.output_item;
							row.uom = r.message.output_uom;
							row.movement_type = "Production";
							frm.refresh_field("output_entries");
						}
					}
				},
			});
		}
	},
});
