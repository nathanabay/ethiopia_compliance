
// ethiopian_calendar.js
// Standardized UI logic for Ethiopian Calendar integration

frappe.provide('ethiopia_compliance.calendar');

ethiopia_compliance.calendar.enabled = null;

ethiopia_compliance.calendar.check_enabled = function (callback) {
    if (ethiopia_compliance.calendar.enabled !== null) {
        callback(ethiopia_compliance.calendar.enabled);
        return;
    }

    frappe.call({
        method: 'ethiopia_compliance.utils.get_calendar_settings',
        callback: function (r) {
            if (r.message && r.message.enable_ethiopian_calendar !== undefined) {
                ethiopia_compliance.calendar.enabled = r.message.enable_ethiopian_calendar;
            } else {
                ethiopia_compliance.calendar.enabled = 1;
            }
            callback(ethiopia_compliance.calendar.enabled);
        },
        error: function () {
            ethiopia_compliance.calendar.enabled = 1;
            callback(ethiopia_compliance.calendar.enabled);
        }
    });
};

ethiopia_compliance.calendar.show_selector = function (frm) {
    frm.selector_open = true;
    let d = new frappe.ui.Dialog({
        title: __('Select Ethiopian Date'),
        fields: [
            { label: __('Year'), fieldname: 'year', fieldtype: 'Int', default: 2017, reqd: 1 },
            {
                label: __('Month'), fieldname: 'month', fieldtype: 'Select', reqd: 1,
                options: [
                    { label: 'Meskerem (1)', value: '01' }, { label: 'Tikimt (2)', value: '02' },
                    { label: 'Hidar (3)', value: '03' }, { label: 'Tahsas (4)', value: '04' },
                    { label: 'Tir (5)', value: '05' }, { label: 'Yekatit (6)', value: '06' },
                    { label: 'Megabit (7)', value: '07' }, { label: 'Miazia (8)', value: '08' },
                    { label: 'Genbot (9)', value: '09' }, { label: 'Sene (10)', value: '10' },
                    { label: 'Hamle (11)', value: '11' }, { label: 'Nehase (12)', value: '12' },
                    { label: 'Pagume (13)', value: '13' }
                ],
                default: '01'
            },
            {
                label: __('Day'), fieldname: 'day', fieldtype: 'Select', reqd: 1,
                options: Array.from({ length: 30 }, (_, i) => (i + 1).toString()), default: '1'
            }
        ],
        primary_action_label: __('Set Date'),
        primary_action: function (values) {
            let day = values.day.toString().padStart(2, '0');
            let date_str = day + '-' + values.month + '-' + values.year;
            frm.set_value('custom_ethiopian_date', date_str);
            d.hide();
        },
        onhide: function () { frm.selector_open = false; }
    });
    d.show();
};

ethiopia_compliance.calendar.sync = function (frm, fieldname) {
    if (frm.doc[fieldname]) {
        frappe.call({
            method: "ethiopia_compliance.utils.get_ec_date",
            args: { date: frm.doc[fieldname] },
            callback: function (r) {
                if (r.message && r.message !== frm.doc.custom_ethiopian_date) {
                    frm.set_value('custom_ethiopian_date', r.message);
                }
            }
        });
    }
};

$(document).on('app_ready', function () {
    ethiopia_compliance.calendar.check_enabled(function (is_enabled) {
        if (!is_enabled) {
            return;
        }

        const date_field_map = {
            "Sales Invoice": "posting_date",
            "Purchase Invoice": "posting_date",
            "Journal Entry": "posting_date",
            "Payment Entry": "posting_date",
            "Purchase Order": "transaction_date",
            "Sales Order": "transaction_date",
            "Leave Application": "from_date",
            "Attendance": "attendance_date",
            "Salary Slip": "start_date",
            "Employee": "date_of_joining",
            "Expense Claim": "posting_date",
            "Job Offer": "date_of_joining",
            "Stock Entry": "posting_date",
            "Delivery Note": "posting_date",
            "Purchase Receipt": "posting_date",
            "Material Request": "transaction_date",
            "Stock Reconciliation": "posting_date",
            "Project": "expected_start_date",
            "Asset": "purchase_date"
        };

        const target_doctypes = Object.keys(date_field_map);

        target_doctypes.forEach(function (dt) {
            frappe.ui.form.on(dt, {
                refresh: function (frm) {
                    if (frm.fields_dict['custom_ethiopian_date']) {
                        frm.fields_dict['custom_ethiopian_date'].$input.on('click', function () {
                            if (!frm.selector_open) {
                                ethiopia_compliance.calendar.show_selector(frm);
                            }
                        });
                    }

                    let fieldname = date_field_map[dt];
                    if (frm.doc[fieldname] && !frm.doc.custom_ethiopian_date) {
                        ethiopia_compliance.calendar.sync(frm, fieldname);
                    }
                },

                posting_date: function (frm) { ethiopia_compliance.calendar.sync(frm, 'posting_date'); },
                transaction_date: function (frm) { ethiopia_compliance.calendar.sync(frm, 'transaction_date'); },
                attendance_date: function (frm) { ethiopia_compliance.calendar.sync(frm, 'attendance_date'); },
                from_date: function (frm) { ethiopia_compliance.calendar.sync(frm, 'from_date'); },
                date_of_joining: function (frm) { ethiopia_compliance.calendar.sync(frm, 'date_of_joining'); },
                purchase_date: function (frm) { ethiopia_compliance.calendar.sync(frm, 'purchase_date'); },
                start_date: function (frm) { ethiopia_compliance.calendar.sync(frm, 'start_date'); },
                expected_start_date: function (frm) { ethiopia_compliance.calendar.sync(frm, 'expected_start_date'); },

                custom_ethiopian_date: function (frm) {
                    if (frm.doc.custom_ethiopian_date && frm.doc.custom_ethiopian_date.length >= 8) {
                        frappe.call({
                            method: "ethiopia_compliance.utils.get_gc_date",
                            args: { custom_ethiopian_date: frm.doc.custom_ethiopian_date },
                            callback: function (r) {
                                if (r.message) {
                                    let target = date_field_map[dt];
                                    if (frm.doc[target] !== r.message) {
                                        frm.set_value(target, r.message);
                                        frappe.show_alert({ message: __("Synced to Gregorian"), indicator: "green" });
                                    }
                                }
                            }
                        });
                    }
                }
            });
        });
    });
});
