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
    }

    show() {
        this.render_skeleton();
        this.load_data();
    }

    render_skeleton() {
        this.parent.html(`
            <div class="compliance-dashboard">
                <div class="row" style="margin-bottom: 20px;">
                    <div class="col-md-12">
                        <div id="date-widget" class="card">
                            <div class="card-body text-center">
                                <h3 id="ethiopian-date-display">Loading...</h3>
                                <p id="gregorian-date-display" class="text-muted"></p>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row" style="margin-bottom: 20px;">
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-header">
                                <h5>WHT This Month</h5>
                            </div>
                            <div class="card-body">
                                <h3 id="wht-amount">--</h3>
                                <p class="text-muted" id="wht-purchases">Purchases: --</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-header">
                                <h5>VAT This Month</h5>
                            </div>
                            <div class="card-body">
                                <h3 id="vat-amount">--</h3>
                                <p class="text-muted" id="vat-sales">Sales: --</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
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
        frappe.call({
            method: 'ethiopia_compliance.page.compliance_dashboard.compliance_dashboard.get_dashboard_data',
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
        // Date Widget
        this.parent.find('#ethiopian-date-display').text(
            data.ethiopian_date || 'N/A'
        );
        this.parent.find('#gregorian-date-display').text(
            'Gregorian: ' + frappe.datetime.str_to_user(data.gregorian_date)
        );

        // WHT Summary
        if (data.tax_summary && data.tax_summary.wht) {
            this.parent.find('#wht-amount').text(
                format_currency(data.tax_summary.wht.total_wht, 'ETB')
            );
            this.parent.find('#wht-purchases').text(
                'Purchases: ' + format_currency(data.tax_summary.wht.total_purchases, 'ETB')
            );
        }

        // VAT Summary
        if (data.tax_summary && data.tax_summary.vat) {
            this.parent.find('#vat-amount').text(
                format_currency(data.tax_summary.vat.total_vat, 'ETB')
            );
            this.parent.find('#vat-sales').text(
                'Sales: ' + format_currency(data.tax_summary.vat.total_sales, 'ETB')
            );
        }

        // Compliance Status
        this.render_compliance_status(data.compliance_status);

        // Recent Documents
        this.render_recent_documents(data.recent_documents);
    }

    render_compliance_status(status) {
        let html = '<ul class="list-unstyled">';
        html += this.status_item(__('Settings Configured'), status.settings_configured);
        html += this.status_item(__('Calendar Enabled'), status.calendar_enabled);
        html += this.status_item(__('Fiscal Year Set'), status.fiscal_year_set);
        html += '</ul>';
        this.parent.find('#compliance-status').html(html);
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
