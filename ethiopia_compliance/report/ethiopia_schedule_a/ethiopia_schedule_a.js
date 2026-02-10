
frappe.query_reports["Ethiopia Schedule A"] = {
    "filters": [
        {"fieldname": "company", "label": "Company", "fieldtype": "Link", "options": "Company", "default": frappe.defaults.get_user_default("Company")},
        {"fieldname": "from_date", "label": "From Date", "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)},
        {"fieldname": "to_date", "label": "To Date", "fieldtype": "Date", "default": frappe.datetime.get_today()}
    ]
};
