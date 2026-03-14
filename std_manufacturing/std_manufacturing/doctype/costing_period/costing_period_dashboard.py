from frappe import _


def get_data():
	return {
		"fieldname": "costing_period",
		"non_standard_fieldnames": {
			"Allocation Run": "period",
			"SKF Entry": "period",
			"CO Document": "period",
		},
		"transactions": [
			{
				"label": _("Cost Objects"),
				"items": ["CO Document", "Cost Pool", "Process Order"],
			},
			{
				"label": _("Allocation"),
				"items": ["Allocation Run", "SKF Entry"],
			},
			{
				"label": _("Production"),
				"items": ["Power Production Record", "PLCV Entry"],
			},
			{
				"label": _("Revaluation"),
				"items": ["Standard Cost Rate", "Standard Cost Revaluation"],
			},
		],
	}
