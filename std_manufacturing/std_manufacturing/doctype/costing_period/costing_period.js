frappe.ui.form.on("Costing Period", {
	refresh(frm) {
		// Dashboard indicators for step statuses
		if (frm.doc.docstatus === 1) {
			const status_color = (val) => {
				if (val === "Completed" || val === "Calculated" || val === "Closed" || val === "Submitted") return "green";
				if (val === "Running") return "orange";
				if (val === "Pending") return "yellow";
				return "blue";
			};
			const steps = [
				["Primary Mirror", frm.doc.primary_mirror_status],
				["Revaluation", frm.doc.revaluation_status],
				["Allocation", frm.doc.allocation_status],
				["Process Orders", frm.doc.process_order_status],
				["Production Cost", frm.doc.production_cost_status],
				["Purchased CPU", frm.doc.purchased_cpu_status],
				["Produced CPU", frm.doc.produced_cpu_status],
				["PLCV", frm.doc.plcv_status],
			];
			steps.forEach(([label, val]) => {
				if (val) {
					frm.dashboard.add_indicator(__(label + ": " + val), status_color(val));
				}
			});
		}

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

		// Step 2: Create Process Orders
		if (frm.doc.process_order_status === "Pending" && frm.doc.primary_mirror_status === "Completed") {
			frm.add_custom_button(
				__("Create Process Orders"),
				() => {
					frappe.confirm(
						__("This will create draft Process Orders for all active recipes. Continue?"),
						() => {
							frappe.call({
								method: "std_manufacturing.std_manufacturing.doctype.costing_period.costing_period.run_production_entry",
								args: { costing_period: frm.doc.name },
								freeze: true,
								freeze_message: __("Creating Process Orders..."),
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

		// Step 5: Production Costing (after allocation)
		if (frm.doc.production_cost_status === "Pending" && frm.doc.allocation_status === "Completed") {
			frm.add_custom_button(
				__("Calculate Production Costs"),
				() => {
					frappe.confirm(
						__("This will calculate unit costs for all Process Orders. Continue?"),
						() => {
							frappe.call({
								method: "std_manufacturing.std_manufacturing.doctype.costing_period.costing_period.run_production_costing",
								args: { costing_period: frm.doc.name },
								freeze: true,
								freeze_message: __("Calculating production costs..."),
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

		if (frm.doc.process_order_status !== "Pending") {
			frm.add_custom_button(
				__("View Process Orders"),
				() => {
					frappe.set_route("List", "Process Order", {
						costing_period: frm.doc.name,
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
