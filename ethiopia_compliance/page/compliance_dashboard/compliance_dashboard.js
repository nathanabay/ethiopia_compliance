frappe.pages['compliance-dashboard'].on_page_load = function (wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Compliance Dashboard',
        single_column: true
    });

    let dashboard = new ComplianceDashboard(page);
    dashboard.show();
};

class ComplianceDashboard {
    constructor(page) {
        this.page = page;
        this.parent = $(this.page.body);
        this.selected_period = 'this_month';
        this.custom_from_date = null;
        this.custom_to_date = null;
    }

    show() {
        this.render_skeleton();
        this.init_date_range_picker();
        this.load_data();
    }

    init_date_range_picker() {
        let preset_filters = [
            { label: __('This Month'), value: 'this_month' },
            { label: __('Last Month'), value: 'last_month' },
            { label: __('Last Quarter'), value: 'last_quarter' },
            { label: __('This Year'), value: 'this_year' },
            { label: __('Custom'), value: 'custom' }
        ];

        let filter_html = '<div class="period-selector" style="display: flex; align-items: center; gap: 10px;">';
        filter_html += '<label style="margin: 0; white-space: nowrap; font-weight: 500;">' + __('Period') + ':</label>';

        filter_html += '<select id="period-preset" class="form-control" style="width: 150px;">';
        preset_filters.forEach(function (pf) {
            filter_html += '<option value="' + pf.value + '">' + pf.label + '</option>';
        });
        filter_html += '</select>';

        filter_html += '<div id="custom-date-range" style="display: none; gap: 8px; align-items: center;">';
        filter_html += '<input type="text" id="custom-from-date" class="form-control" placeholder="' + __('From') + '" style="width: 130px;">';
        filter_html += '<span>' + __('to') + '</span>';
        filter_html += '<input type="text" id="custom-to-date" class="form-control" placeholder="' + __('To') + '" style="width: 130px;">';
        filter_html += '</div>';

        filter_html += '<button id="refresh-dashboard" class="btn btn-primary btn-sm">' + __('Refresh') + '</button>';
        filter_html += '</div>';

        this.parent.find('#period-selector-container').html(filter_html);

        let self = this;

        this.parent.find('#period-preset').on('change', function () {
            let val = $(this).val();
            self.selected_period = val;
            if (val === 'custom') {
                self.parent.find('#custom-date-range').show();
            } else {
                self.parent.find('#custom-date-range').hide();
                self.load_data();
            }
        });

        this.parent.find('#custom-from-date').datepicker({
            dateFormat: 'yyyy-mm-dd',
            onSelect: function () {
                self.custom_from_date = $(this).val();
            }
        });

        this.parent.find('#custom-to-date').datepicker({
            dateFormat: 'yyyy-mm-dd',
            onSelect: function () {
                self.custom_to_date = $(this).val();
            }
        });

        this.parent.find('#refresh-dashboard').on('click', function () {
            if (self.selected_period === 'custom') {
                self.custom_from_date = self.parent.find('#custom-from-date').val();
                self.custom_to_date = self.parent.find('#custom-to-date').val();
                if (!self.custom_from_date || !self.custom_to_date) {
                    frappe.show_alert({
                        message: __('Please select both From and To dates'),
                        indicator: 'orange'
                    });
                    return;
                }
            }
            self.load_data();
        });
    }

    render_skeleton() {
        this.parent.html(`
            <div class="compliance-dashboard">
                <div class="row" style="margin-bottom: 20px;">
                    <div class="col-md-8">
                        <div id="date-widget" class="card">
                            <div class="card-body text-center">
                                <h3 id="ethiopian-date-display">Loading...</h3>
                                <p id="gregorian-date-display" class="text-muted"></p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card" style="height: 100%;">
                            <div class="card-body" style="display: flex; align-items: center; justify-content: center;">
                                <div id="period-selector-container"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row" style="margin-bottom: 20px;">
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-header">
                                <h5 id="wht-title">WHT This Month</h5>
                            </div>
                            <div class="card-body">
                                <h3 id="wht-amount">--</h3>
                                <p class="text-muted" id="wht-purchases">Purchases: --</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-header">
                                <h5 id="vat-title">VAT This Month</h5>
                            </div>
                            <div class="card-body">
                                <h3 id="vat-amount">--</h3>
                                <p class="text-muted" id="vat-sales">Sales: --</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-header">
                                <h5 id="tot-title">TOT This Month</h5>
                            </div>
                            <div class="card-body">
                                <h3 id="tot-amount">--</h3>
                                <p class="text-muted" id="tot-turnover">Turnover: --</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-header">
                                <h5>Compliance Status</h5>
                            </div>
                            <div class="card-body">
                                <div id="compliance-status">--</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row" style="margin-bottom: 20px;">
                    <div class="col-md-12">
                        <div class="card">
                            <div class="card-header">
                                <h5>Tax Calendar & Alerts</h5>
                            </div>
                            <div class="card-body">
                                <div id="tax-calendar-widget">Loading...</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-12">
                        <div class="card">
                            <div class="card-header">
                                <h5>Recent Documents</h5>
                            </div>
                            <div class="card-body">
                                <div id="recent-documents">Loading...</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `);
    }

    load_data() {
        let args = { period: this.selected_period };
        if (this.selected_period === 'custom') {
            args.from_date = this.custom_from_date;
            args.to_date = this.custom_to_date;
        }

        frappe.call({
            method: 'ethiopia_compliance.page.compliance_dashboard.compliance_dashboard.get_dashboard_data',
            args: args,
            callback: (r) => {
                if (r.message) {
                    this.render_data(r.message);
                } else {
                    frappe.show_alert({message: __('No data available'), indicator: 'orange'});
                }
            },
            error: () => {
                frappe.show_alert({message: __('Failed to load dashboard data'), indicator: 'red'});
            }
        });
    }

    render_data(data) {
        let company = encodeURIComponent(data.company || '');
        let from_date = encodeURIComponent(data.month_start || '');
        let to_date = encodeURIComponent(data.month_end || '');

        // Update period labels
        let period_label = data.period_label || __('This Month');
        this.parent.find('#wht-title').text(__('WHT') + ' ' + period_label);
        this.parent.find('#vat-title').text(__('VAT') + ' ' + period_label);
        this.parent.find('#tot-title').text(__('TOT') + ' ' + period_label);

        // Date Widget
        this.parent.find('#ethiopian-date-display').text(
            data.ethiopian_date || 'N/A'
        );
        this.parent.find('#gregorian-date-display').text(
            'Gregorian: ' + frappe.datetime.str_to_user(data.gregorian_date)
        );

        // WHT Summary with drill-down
        if (data.tax_summary && data.tax_summary.wht) {
            let wht_url = this.build_report_url('tass_purchase_declaration', company, from_date, to_date);
            this.parent.find('#wht-amount').html(
                '<a href="' + wht_url + '" title="' + __('View WHT Report') + '">'
                + frappe.utils.escape_html(format_currency(data.tax_summary.wht.total_wht, 'ETB'))
                + '</a>'
            );
            this.parent.find('#wht-purchases').text(
                'Purchases: ' + format_currency(data.tax_summary.wht.total_purchases, 'ETB')
            );
        }

        // VAT Summary with drill-down
        if (data.tax_summary && data.tax_summary.vat) {
            let vat_url = this.build_report_url('tass_sales_declaration', company, from_date, to_date);
            this.parent.find('#vat-amount').html(
                '<a href="' + vat_url + '" title="' + __('View VAT Report') + '">'
                + frappe.utils.escape_html(format_currency(data.tax_summary.vat.total_vat, 'ETB'))
                + '</a>'
            );
            this.parent.find('#vat-sales').text(
                'Sales: ' + format_currency(data.tax_summary.vat.total_sales, 'ETB')
            );
        }

        // TOT Summary with drill-down
        if (data.tax_summary && data.tax_summary.tot) {
            let tot_url = this.build_report_url('tass_sales_declaration', company, from_date, to_date);
            this.parent.find('#tot-amount').html(
                '<a href="' + tot_url + '" title="' + __('View TOT Report') + '">'
                + frappe.utils.escape_html(format_currency(data.tax_summary.tot.total_tot, 'ETB'))
                + '</a>'
            );
            this.parent.find('#tot-turnover').text(
                'Turnover: ' + format_currency(data.tax_summary.tot.total_turnover, 'ETB')
            );
        }

        // Compliance Status
        this.render_compliance_status(data.compliance_status);

        // Tax Calendar & Alerts
        this.render_tax_calendar(data.tax_calendar);

        // Recent Documents
        this.render_recent_documents(data.recent_documents);
    }

    render_tax_calendar(calendar) {
        if (!calendar || calendar.length === 0) {
            this.parent.find('#tax-calendar-widget').html(
                '<p class="text-muted">' + __('No upcoming deadlines') + '</p>'
            );
            return;
        }

        let urgency_cfg = {
            'overdue':  { color: '#dc3545', bg: '#fff5f5', border: '#dc3545', icon: '&#9888;' },
            'due_soon': { color: '#e67e00', bg: '#fff8f0', border: '#e67e00', icon: '&#9200;' },
            'upcoming': { color: '#1e6fde', bg: '#f0f7ff', border: '#1e6fde', icon: '&#128197;' },
            'future':   { color: '#28a745', bg: '#f0fff4', border: '#28a745', icon: '&#10003;' }
        };

        let html = '<div style="display: flex; flex-wrap: wrap; gap: 12px;">';

        calendar.forEach(function (d) {
            let cfg = urgency_cfg[d.urgency] || urgency_cfg['future'];
            let days = d.days_remaining;
            let status_text;
            if (days < 0) {
                status_text = __('OVERDUE — {0} days ago').format([Math.abs(days)]);
            } else if (days === 0) {
                status_text = __('DUE TODAY');
            } else {
                status_text = __('Due in {0} days').format([days]);
            }

            html += `
                <div style="
                    flex: 1 1 220px; min-width: 200px;
                    border-left: 4px solid ${cfg.border};
                    background: ${cfg.bg};
                    padding: 12px 14px;
                    border-radius: 4px;
                    font-size: 13px;
                ">
                    <div style="font-weight: 600; color: #333; margin-bottom: 4px;">
                        ${frappe.utils.escape_html(d.label)}
                    </div>
                    <div style="color: #666; margin-bottom: 4px;">
                        ${frappe.datetime.str_to_user(d.due_date)}
                    </div>
                    <div style="color: ${cfg.color}; font-weight: 600;">
                        ${cfg.icon} ${status_text}
                    </div>
                </div>`;
        });

        html += '</div>';

        // Legend
        html += `
            <div style="margin-top: 14px; display: flex; gap: 16px; font-size: 12px; color: #666;">
                <span><span style="background:#dc3545;color:#fff;padding:1px 6px;border-radius:3px;">${__('Overdue')}</span></span>
                <span><span style="background:#e67e00;color:#fff;padding:1px 6px;border-radius:3px;">${__('Due in 5 days')}</span></span>
                <span><span style="background:#1e6fde;color:#fff;padding:1px 6px;border-radius:3px;">${__('Due in 14 days')}</span></span>
                <span><span style="background:#28a745;color:#fff;padding:1px 6px;border-radius:3px;">${__('Compliant')}</span></span>
            </div>`;

        this.parent.find('#tax-calendar-widget').html(html);
    }

    render_compliance_status(status) {
        let html = '<ul class="list-unstyled">';
        html += this.status_item(__('Settings Configured'), status.settings_configured);
        html += this.status_item(__('Calendar Enabled'), status.calendar_enabled);
        html += this.status_item(__('Fiscal Year Set'), status.fiscal_year_set);
        html += '</ul>';
        this.parent.find('#compliance-status').html(html);
    }

    build_report_url(report_name, company, from_date, to_date) {
        return '/app/query-report/' + report_name
            + '?company=' + company
            + '&from_date=' + from_date
            + '&to_date=' + to_date;
    }

    status_item(label, is_ok) {
        let icon = is_ok ? '&#10003;' : '&#10007;';
        let color = is_ok ? 'green' : 'red';
        return `<li style="color: ${color};">${icon} ${frappe.utils.escape_html(label)}</li>`;
    }

    render_recent_documents(documents) {
        if (!documents || documents.length === 0) {
            this.parent.find('#recent-documents').html(
                '<p class="text-muted">' + __('No recent documents') + '</p>'
            );
            return;
        }

        let html = `
            <table class="table table-sm">
                <thead>
                    <tr>
                        <th>${__('Type')}</th>
                        <th>${__('Document')}</th>
                        <th>${__('Date')}</th>
                        <th>${__('Party')}</th>
                        <th class="text-right">${__('Amount')}</th>
                    </tr>
                </thead>
                <tbody>
        `;

        documents.forEach(doc => {
            let type = frappe.utils.escape_html(doc.type || '');
            let name = frappe.utils.escape_html(doc.name || '');
            let party = frappe.utils.escape_html(doc.party || '');
            let slug = (doc.type || '').toLowerCase().replace(/ /g, '-');

            html += `
                <tr>
                    <td><span class="badge badge-secondary">${type}</span></td>
                    <td><a href="/app/${slug}/${encodeURIComponent(doc.name)}">${name}</a></td>
                    <td>${frappe.datetime.str_to_user(doc.date)}</td>
                    <td>${party}</td>
                    <td class="text-right">${format_currency(doc.amount, 'ETB')}</td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        this.parent.find('#recent-documents').html(html);
    }
}
