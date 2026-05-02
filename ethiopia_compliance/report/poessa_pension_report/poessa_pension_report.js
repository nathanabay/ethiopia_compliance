// Copyright (c) 2026, Bespo and contributors
// For license information, please see license.txt

frappe.query_reports["POESSA Pension Report"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname": "month",
			"label": __("Month"),
			"fieldtype": "Select",
			"options": [
				"January", "February", "March", "April", "May", "June",
				"July", "August", "September", "October", "November", "December"
			],
			"default": ["January", "February", "March", "April", "May", "June",
				"July", "August", "September", "October", "November", "December"
			][frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth()],
			"reqd": 1
		},
		{
			"fieldname": "year",
			"label": __("Year"),
			"fieldtype": "Select",
			"options": Array.from({length: 7}, (_, i) => String(new Date().getFullYear() - 3 + i)),
			"default": String(new Date().getFullYear()),
			"reqd": 1
		}
	]
};
