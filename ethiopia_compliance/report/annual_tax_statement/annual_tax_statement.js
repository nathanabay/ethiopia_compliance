// Copyright (c) 2026, Bespo and contributors
// For license information, please see license.txt

frappe.query_reports["Annual Tax Statement"] = {
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
            "fieldname": "year",
            "label": __("Year"),
            "fieldtype": "Select",
            "options": Array.from({length: 5}, (_, i) => String(new Date().getFullYear() - 2 + i)),
            "default": new Date().getFullYear(),
            "reqd": 1
        }
    ]
};
