frappe.ui.form.on("Costing Period", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || frm.doc.status === "Completed") {
			return;
		}

		// Step 1: Primary Mirror
		if (frm.doc.primary_mirror_status === "Pending") {
			frm.add_custom_button(
				__("Run Primary Mirror"),
				() => {
					frappe.confirm(
						__("This will mirror all GL Entries to CO Documents. Continue?"),
						() => {
							frappe.call({
								method: "std_manufacturing.std_manufacturing.doctype.costing_period.costing_period.run_primary_mirror",
								args: { costing_period: frm.doc.name },
								freeze: true,
								freeze_message: __("Creating CO Documents from GL..."),
								callback: (r) => {
									frm.reload_doc();
								},
							});
						}
					);
				},
				__("Period-End Close")
			);
		}

		// Step 3: Run Allocation
		if (frm.doc.allocation_status === "Pending" && frm.doc.primary_mirror_status === "Completed") {
			frm.add_custom_button(
				__("Run CO Allocation"),
				() => {
					frappe.confirm(
						__("This will execute all active allocation cycles. Continue?"),
						() => {
							frappe.call({
								method: "std_manufacturing.std_manufacturing.doctype.costing_period.costing_period.run_allocation",
								args: { costing_period: frm.doc.name },
								freeze: true,
								freeze_message: __("Running Allocation Cycles..."),
								callback: (r) => {
									frm.reload_doc();
								},
							});
						}
					);
				},
				__("Period-End Close")
			);
		}

		// Close Period
		if (frm.doc.status === "In Progress") {
			frm.add_custom_button(
				__("Close Period"),
				() => {
					frappe.confirm(
						__("This will mark the period as Completed. Continue?"),
						() => {
							frappe.call({
								method: "std_manufacturing.std_manufacturing.doctype.costing_period.costing_period.close_period",
								args: { costing_period: frm.doc.name },
								callback: (r) => {
									frm.reload_doc();
								},
							});
						}
					);
				},
				__("Period-End Close")
			);
		}

		// View links
		if (frm.doc.primary_mirror_status === "Completed") {
			frm.add_custom_button(
				__("View CO Documents"),
				() => {
					frappe.set_route("List", "CO Document", {
						period: frm.doc.name,
					});
				},
				__("View")
			);
		}

		if (frm.doc.allocation_status === "Completed") {
			frm.add_custom_button(
				__("View Allocation Run"),
				() => {
					frappe.set_route("List", "Allocation Run", {
						period: frm.doc.name,
					});
				},
				__("View")
			);
		}

		frm.add_custom_button(
			__("Cost Drilldown"),
			() => {
				frappe.set_route("query-report", "Cost Drilldown", {
					period: frm.doc.name,
				});
			},
			__("View")
		);
	},
});
