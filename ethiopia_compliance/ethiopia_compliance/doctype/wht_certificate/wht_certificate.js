// Copyright (c) 2026, Bespo and contributors
// For license information, please see license.txt

frappe.ui.form.on('WHT Certificate', {
	refresh: function (frm) {
		// Visual warning when penalty rate applies
		if (frm.doc.penalty_rate_applies) {
			frm.set_df_property('wht_rate', 'description',
				__('30% penalty rate applied — Supplier TIN is missing (Proclamation 1395/2025)'));
		}

		if (frm.doc.docstatus === 0 && !frm.is_new()) {
			frm.add_custom_button(__('Generate Data'), function () {
				frm.call({
					method: 'generate_certificate_data',
					doc: frm.doc,
					callback: function (r) {
						frm.refresh();
						frappe.msgprint(__('Certificate data generated successfully'));
					}
				});
			});
		}

		// Add print button
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__('Print'), function () {
				frm.print_doc();
			});
		}
	},

	supplier: function (frm) {
		// Auto-fetch supplier TIN
		if (frm.doc.supplier) {
			frappe.db.get_value('Supplier', frm.doc.supplier, 'tax_id', (r) => {
				if (r && r.tax_id) {
					frm.set_value('supplier_tin', r.tax_id);
					frm.set_value('penalty_rate_applies', 0);
					if (frm.doc.wht_rate === 30.0 || !frm.doc.wht_rate) {
						frm.set_value('wht_rate', 3.0);
					}
				} else {
					frm.set_value('supplier_tin', '');
					frm.set_value('penalty_rate_applies', 1);
					frm.set_value('wht_rate', 30.0);
					frappe.msgprint({
						title: __('TIN Missing'),
						indicator: 'red',
						message: __('Supplier does not have a TIN. Penalty rate of 30% will be applied per Proclamation 1395/2025.')
					});
				}
			});
		}
	},

	penalty_rate_applies: function (frm) {
		if (frm.doc.penalty_rate_applies) {
			frm.set_value('wht_rate', 30.0);
		} else {
			frm.set_value('wht_rate', 3.0);
		}
	}
});
