frappe.pages["sales-crm-workspace"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __("Sales Workspace"),
        single_column: true,
    });

    page.main.addClass("sales-crm-workspace");
    page.set_primary_action(__("New Lead"), () => frappe.new_doc("CRM Lead"));
    page.add_action_item(__("New Opportunity"), () => frappe.new_doc("CRM Opportunity"));
    page.add_action_item(__("Log Call"), () => frappe.new_doc("Sales Activity", { activity_type: "Call" }));
    page.add_action_item(__("Add Meeting"), () => frappe.new_doc("Sales Activity", { activity_type: "Meeting" }));
    page.add_action_item(__("Add Follow-up"), () => frappe.new_doc("Sales Task", { task_type: "Follow-up" }));

    render_loading(page.main);
    frappe.call({
        method: "sales_crm.api.workspace.get_sales_workspace",
        callback(r) {
            render_workspace(page.main, r.message || {});
        },
    });
};

function render_loading(root) {
    root.html(`<div class="text-muted" style="padding: 24px">${__("Loading Sales Workspace...")}</div>`);
}

function render_workspace(root, data) {
    const hour = new Date().getHours();
    const greeting = hour < 12 ? __("Good Morning") : hour < 17 ? __("Good Afternoon") : __("Good Evening");
    const k = data.kpis || {};

    root.html(`
        <div class="crm-ws">
            <div class="crm-ws-header">
                <div>
                    <div class="crm-ws-greeting">${greeting}, ${frappe.utils.escape_html(data.user?.full_name || frappe.session.user)}</div>
                    <div class="text-muted">${frappe.datetime.str_to_user(data.user?.date || frappe.datetime.nowdate())}</div>
                </div>
            </div>
            <div class="crm-kpis">
                ${kpi("Follow-ups Due", k.followups_due, "Sales Task", [["due_date", "=", frappe.datetime.nowdate()]])}
                ${kpi("Overdue Activities", k.overdue_activities, "Sales Activity", [["activity_date", "<", frappe.datetime.nowdate()]])}
                ${kpi("Meetings Today", k.meetings_today, "Sales Activity", [["activity_date", "=", frappe.datetime.nowdate()]])}
                ${kpi("Hot Leads", k.hot_leads, "CRM Lead", [["lead_status", "in", ["Qualified", "Qualifying"]]])}
                ${kpi("Open Opportunities", k.open_opportunities, "CRM Opportunity", [["status", "=", "Open"]])}
                ${kpi("Closing This Month", format_currency(k.closing_this_month || 0), "CRM Opportunity", [["status", "=", "Open"]])}
                ${kpi("Quotes Expiring Soon", k.quotes_expiring_soon, "Quotation", [])}
                ${kpi("Deals At Risk", k.deals_at_risk, "CRM Opportunity", [["risk_level", "in", ["High", "Critical"]]])}
            </div>
            <div class="crm-grid">
                ${section("Today's Agenda", agenda_rows(data.agenda || []))}
                ${section("Next Actions", next_action_rows(data.next_actions || []))}
                ${section("Notifications", notification_rows(data.notifications || []))}
                ${section("My Pipeline", pipeline_rows(data.pipeline_summary || []))}
                ${section("Closing Soon", closing_rows(data.closing_soon || []))}
            </div>
        </div>
    `);

    root.find("[data-doctype]").on("click", function () {
        frappe.set_route("List", $(this).data("doctype"), $(this).data("filters") || []);
    });
    inject_workspace_css();
}

function kpi(label, value, doctype, filters) {
    return `<button class="crm-kpi" data-doctype="${doctype}" data-filters='${JSON.stringify(filters)}'>
        <span>${__(label)}</span><strong>${value || 0}</strong>
    </button>`;
}

function section(title, body) {
    return `<div class="crm-panel"><h3>${__(title)}</h3><div>${body || `<div class="text-muted">${__("Nothing pending")}</div>`}</div></div>`;
}

function agenda_rows(rows) {
    return rows.map(row => `
        <div class="crm-row">
            <strong>${row.start_time || ""}</strong>
            <span>${row.activity_type}</span>
            <a onclick="frappe.set_route('Form','Sales Activity','${row.name}')">${frappe.utils.escape_html(row.subject || row.name)}</a>
            <button class="btn btn-xs btn-default" onclick="frappe.set_route('Form','Sales Activity','${row.name}')">${__("Open")}</button>
        </div>`).join("");
}

function next_action_rows(rows) {
    return rows.map(row => `
        <div class="crm-row crm-priority-${(row.priority || "").toLowerCase()}">
            <strong>${row.priority}</strong>
            <span>${frappe.utils.escape_html(row.customer || row.record_name)}</span>
            <span>${frappe.utils.escape_html(row.reason)}</span>
            <span>${frappe.utils.escape_html(row.recommended_action)}</span>
        </div>`).join("");
}

function pipeline_rows(rows) {
    return rows.map(row => `
        <div class="crm-row">
            <strong>${frappe.utils.escape_html(row.stage || "")}</strong>
            <span>${row.opportunity_count || 0}</span>
            <span>${format_currency(row.pipeline_value || 0)}</span>
            <span>${format_currency(row.weighted_value || 0)}</span>
        </div>`).join("");
}

function closing_rows(rows) {
    return rows.map(row => `
        <div class="crm-row">
            <strong>${frappe.utils.escape_html(row.range || "")}</strong>
            <a onclick="frappe.set_route('Form','CRM Opportunity','${row.name}')">${frappe.utils.escape_html(row.opportunity_name || row.name)}</a>
            <span>${format_currency(row.opportunity_value || 0, row.currency)}</span>
            <span>${frappe.datetime.str_to_user(row.expected_close_date)}</span>
            <span>${row.deal_health_status || ""}</span>
        </div>`).join("");
}

function notification_rows(rows) {
    return rows.map(row => `
        <div class="crm-row">
            <strong>${frappe.utils.escape_html(row.priority || "")}</strong>
            <a onclick="frappe.set_route('Form','${row.doctype}','${row.docname}')">${frappe.utils.escape_html(row.title || "")}</a>
            <span>${frappe.utils.escape_html(row.message || "")}</span>
            <span>${row.due_date ? frappe.datetime.str_to_user(row.due_date) : ""}</span>
        </div>`).join("");
}

function inject_workspace_css() {
    if ($("#sales-crm-workspace-css").length) return;
    $("head").append(`<style id="sales-crm-workspace-css">
        .crm-ws { padding: 16px; }
        .crm-ws-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
        .crm-ws-greeting { font-size: 22px; font-weight: 600; }
        .crm-kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:10px; margin-bottom:16px; }
        .crm-kpi { text-align:left; border:1px solid var(--border-color); background:var(--card-bg); border-radius:8px; padding:12px; }
        .crm-kpi span { display:block; color:var(--text-muted); font-size:12px; }
        .crm-kpi strong { font-size:22px; }
        .crm-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(360px,1fr)); gap:14px; }
        .crm-panel { border:1px solid var(--border-color); border-radius:8px; padding:14px; background:var(--card-bg); }
        .crm-panel h3 { font-size:15px; margin:0 0 10px; }
        .crm-row { display:grid; grid-template-columns:90px 1fr 1fr auto; gap:8px; align-items:center; padding:8px 0; border-top:1px solid var(--border-color); }
        .crm-row:first-child { border-top:0; }
        .crm-priority-critical strong { color: var(--red-600); }
        .crm-priority-high strong { color: var(--orange-600); }
    </style>`);
}
