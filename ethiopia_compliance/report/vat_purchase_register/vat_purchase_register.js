
frappe.query_reports["VAT Purchase Register"] = {
	"filters": [
		{"fieldname": "company", "label": __("Company"), "fieldtype": "Link", "options": "Company", "default": frappe.defaults.get_user_default("Company"), "reqd": 1},
		{"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1), "reqd": 1},
		{"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.get_today(), "reqd": 1},
		{"fieldname": "use_ethiopian_calendar", "label": __("Use Ethiopian Calendar"), "fieldtype": "Check", "default": 0}
	],
	"onload": function(report) {
		report.page.add_inner_button(__("Download VAT XML"), function() {
			var filters = report.get_filter_values();
			var query = $.param({
				report_name: report.report_name,
				filters: JSON.stringify(filters)
			});
			window.open(
				'/api/method/ethiopia_compliance.utils.export_engine.download_vat_xml?' + query,
				'_blank'
			);
			frappe.show_alert(__("VAT XML export initiated"), 5);
		});
	}
};
