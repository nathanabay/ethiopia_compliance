
frappe.query_reports["Pension Remittance Status"] = {
	"filters": [
		{"fieldname": "company", "label": __("Company"), "fieldtype": "Link", "options": "Company", "default": frappe.defaults.get_user_default("Company"), "reqd": 1},
		{"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -12), "reqd": 1},
		{"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.get_today(), "reqd": 1}
	],
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "risk_level" && data) {
			if (data.risk_level && data.risk_level.indexOf("Red") > -1) {
				value = "<span style='color:white;background-color:#d9534f;padding:3px 8px;border-radius:3px;font-weight:bold;'>" + value + "</span>";
			} else if (data.risk_level && data.risk_level.indexOf("Orange") > -1) {
				value = "<span style='color:white;background-color:#f0ad4e;padding:3px 8px;border-radius:3px;font-weight:bold;'>" + value + "</span>";
			} else if (data.risk_level && data.risk_level.indexOf("Yellow") > -1) {
				value = "<span style='color:black;background-color:#ffc107;padding:3px 8px;border-radius:3px;font-weight:bold;'>" + value + "</span>";
			} else if (data.risk_level && data.risk_level.indexOf("Green") > -1) {
				value = "<span style='color:white;background-color:#5cb85c;padding:3px 8px;border-radius:3px;font-weight:bold;'>" + value + "</span>";
			}
		}
		return value;
	}
};
