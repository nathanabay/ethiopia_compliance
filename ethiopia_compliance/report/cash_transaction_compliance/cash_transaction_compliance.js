
frappe.query_reports["Cash Transaction Compliance"] = {
	"filters": [
		{"fieldname": "company", "label": __("Company"), "fieldtype": "Link", "options": "Company", "default": frappe.defaults.get_user_default("Company"), "reqd": 1},
		{"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -3), "reqd": 1},
		{"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.get_today(), "reqd": 1}
	],
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "status" && data) {
			value = "<span style='color:white;background-color:#d9534f;padding:3px 8px;border-radius:3px;font-weight:bold;'>"
				+ value + " - " + __("Penalty: amount equals disallowed deduction") + "</span>";
		}
		if (column.fieldname === "amount" && data) {
			value = "<span style='font-weight:bold;color:#d9534f;'>" + value + "</span>";
		}
		return value;
	}
};
