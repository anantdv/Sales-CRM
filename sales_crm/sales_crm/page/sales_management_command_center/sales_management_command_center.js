frappe.pages["sales-management-command-center"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __("Sales Management Command Center"),
        single_column: true,
    });

    const state = { data: null };
    page.main.addClass("sales-command-center");
    add_filters(page);
    page.set_primary_action(__("Refresh"), () => load_dashboard(page, state));
    page.add_action_item(__("Reset Filters"), () => {
        page.fields_dict.company.set_value("");
        page.fields_dict.pipeline.set_value("");
        page.fields_dict.salesperson.set_value("");
        page.fields_dict.territory.set_value("");
        page.fields_dict.opportunity_type.set_value("");
        load_dashboard(page, state);
    });
    page.add_action_item(__("Export"), () => export_current(state));
    inject_command_center_css();
    load_dashboard(page, state);
};

function add_filters(page) {
    page.add_field({ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", change: () => page.set_indicator(__("Filters changed"), "orange") });
    page.add_field({ fieldname: "from_date", label: __("From"), fieldtype: "Date" });
    page.add_field({ fieldname: "to_date", label: __("To"), fieldtype: "Date", default: frappe.datetime.nowdate() });
    page.add_field({ fieldname: "sales_team", label: __("Sales Team"), fieldtype: "Data" });
    page.add_field({ fieldname: "pipeline", label: __("Pipeline"), fieldtype: "Link", options: "CRM Pipeline" });
    page.add_field({ fieldname: "salesperson", label: __("Salesperson"), fieldtype: "Link", options: "User" });
    page.add_field({ fieldname: "territory", label: __("Territory"), fieldtype: "Link", options: "Territory" });
    page.add_field({ fieldname: "opportunity_type", label: __("Opportunity Type"), fieldtype: "Select", options: "\nNew Business\nExisting Customer\nUpsell\nCross-sell\nRenewal\nRental\nManaged Service\nTender" });
    page.add_field({ fieldname: "account_tier", label: __("Account Tier"), fieldtype: "Select", options: "\nStrategic\nEnterprise\nMajor\nGrowth\nStandard" });
    page.add_field({ fieldname: "product_group", label: __("Product Group"), fieldtype: "Link", options: "Item Group" });
    page.add_field({ fieldname: "lead_source", label: __("Lead Source"), fieldtype: "Link", options: "Lead Source" });
    page.add_field({ fieldname: "currency", label: __("Currency"), fieldtype: "Link", options: "Currency" });
}

function get_filters(page) {
    const fields = page.fields_dict;
    return {
        company: fields.company.get_value(),
        from_date: fields.from_date.get_value(),
        to_date: fields.to_date.get_value(),
        pipeline: fields.pipeline.get_value(),
        salesperson: fields.salesperson.get_value(),
        territory: fields.territory.get_value(),
        opportunity_type: fields.opportunity_type.get_value(),
        sales_team: fields.sales_team.get_value(),
        account_tier: fields.account_tier.get_value(),
        product_group: fields.product_group.get_value(),
        lead_source: fields.lead_source.get_value(),
        currency: fields.currency.get_value(),
    };
}

function load_dashboard(page, state) {
    page.main.html(`<div class="text-muted cc-loading">${__("Loading command center...")}</div>`);
    frappe.call({
        method: "sales_crm.api.management.get_dashboard",
        args: { filters: get_filters(page) },
        callback(r) {
            state.data = r.message || {};
            page.clear_indicator();
            render_dashboard(page.main, state.data);
        },
    });
}

function render_dashboard(root, data) {
    root.html(`
        <div class="cc-tabs">
            ${["Overview", "Pipeline", "Forecast", "Team", "Leads", "Accounts", "Activities", "Revenue", "Intelligence"].map((tab, i) => `<button class="cc-tab ${i === 0 ? "active" : ""}" data-tab="${tab}">${__(tab)}</button>`).join("")}
        </div>
        <div class="cc-tab-body"></div>
    `);
    root.find(".cc-tab").on("click", function () {
        root.find(".cc-tab").removeClass("active");
        $(this).addClass("active");
        render_tab(root.find(".cc-tab-body"), $(this).data("tab"), data);
    });
    render_tab(root.find(".cc-tab-body"), "Overview", data);
}

function render_tab(body, tab, data) {
    const k = data.executive_kpis || {};
    const attention = data.attention || {};
    const revenue = data.revenue || {};
    const intelligence = data.intelligence || {};
    const pipeline = data.pipeline || {};
    const forecast = data.forecast || {};

    const commonKpis = kpi_grid([
        ["Revenue YTD", money(k.revenue_ytd)],
        ["Target", money(k.sales_target_ytd)],
        ["Achievement", pct(k.achievement_percent)],
        ["Open Pipeline", money(k.open_pipeline)],
        ["Weighted Pipeline", money(k.weighted_pipeline)],
        ["Forecast", money(k.forecast)],
        ["Target Gap", money(k.target_gap)],
        ["Closed Won", money(k.closed_won)],
        ["Gross Margin", k.gross_margin == null ? __("Unavailable") : money(k.gross_margin)],
        ["Outstanding AR", money(k.outstanding_receivables)],
    ]);

    const attentionCards = kpi_grid(Object.entries(attention).map(([key, value]) => [frappe.unscrub(key), value]));

    const html = {
        Overview: `
            ${commonKpis}
            ${panel("Attention Required", attentionCards)}
            ${panel("Pipeline Funnel", funnel(pipeline.by_stage || []))}
            ${panel("Forecast", forecast_box(forecast))}
            ${panel("Top Deals", table(pipeline.top_deals || [], ["opportunity_name", "customer", "opportunity_owner", "stage", "opportunity_value", "deal_health_status"], "CRM Opportunity", "name"))}
            ${panel("Management Alerts", table(data.alerts || [], ["severity", "category", "message", "reason", "recommended_action"], null, null))}
        `,
        Pipeline: `
            ${panel("Pipeline Coverage", coverage_box(data.coverage || {}))}
            ${panel("Pipeline by Stage", table(pipeline.by_stage || [], ["stage", "opportunity_count", "pipeline_value", "weighted_value", "stage_conversion_rate"], "CRM Opportunity", "stage"))}
            ${panel("Pipeline Aging", aging_box(pipeline.aging || {}))}
            ${panel("Slipping Deals", table(intelligence.slipping_deals || [], ["opportunity_name", "opportunity_owner", "expected_close_date", "stage", "opportunity_value"], "CRM Opportunity", "name"))}
        `,
        Forecast: `
            ${panel("Forecast Summary", forecast_box(forecast))}
            ${panel("Forecast by Salesperson", table(forecast.by_salesperson || [], ["salesperson", "target", "closed_won", "commit", "best_case", "pipeline", "forecast", "gap"], null, null))}
        `,
        Team: `${panel("Team Performance", table(data.team || [], ["salesperson", "target", "actual_revenue", "achievement_percent", "open_pipeline", "weighted_pipeline", "won_deals", "win_rate", "activities", "stale_deals", "forecast"], null, null))}`,
        Leads: `${panel("Lead Funnel", table((data.leads || {}).funnel || [], ["lead_status", "lead_count", "estimated_value", "conversion_percent"], "CRM Lead", "lead_status"))}${panel("Lead Source Performance", table((data.leads || {}).lead_source || [], ["lead_source", "leads", "qualified", "converted", "estimated_value"], null, null))}`,
        Accounts: `${panel("Account Performance", table((data.accounts || {}).accounts || [], ["customer", "account_tier", "account_owner", "pipeline", "open_opportunities", "outstanding_receivable", "engagement_status"], "CRM Account Profile", "name"))}${panel("Commercial Risk", table((data.accounts || {}).commercial_risk || [], ["customer", "pipeline", "outstanding", "flag"], "Customer", "customer"))}${panel("Concentration", concentration((data.accounts || {}).concentration || {}))}`,
        Activities: `${panel("Activity Performance", table(data.activities || [], ["activity_type", "assigned_to", "activity_count", "opportunities_touched"], null, null))}`,
        Revenue: `${panel("Sales Trend", table(revenue.trend || [], ["period", "revenue", "gross_margin"], null, null))}${panel("Lead to Cash", lead_to_cash(revenue.lead_to_cash || {}))}${panel("Quotation Performance", quotation_box(revenue.quotation || {}))}${panel("Product Performance", table(revenue.product || [], ["item_group", "pipeline_value", "opportunity_count"], null, null))}${panel("Territory Performance", table(revenue.territory || [], ["territory", "pipeline", "weighted_pipeline", "customers", "opportunities", "won", "lost"], null, null))}`,
        Intelligence: `${panel("Win / Loss", win_loss(intelligence.win_loss || {}))}${panel("Lost Reasons", table(intelligence.lost_reasons || [], ["lost_reason", "count", "lost_value"], null, null))}${panel("Competitors", table(intelligence.competitors || [], ["competitor", "deals_faced", "wins", "losses", "lost_value"], null, null))}${panel("Sales Velocity", velocity(intelligence.velocity || {}))}${panel("Forecast Accuracy", forecast_accuracy(intelligence.forecast_accuracy || {}))}`,
    }[tab];
    body.html(`<div class="cc-section-grid">${html}</div>`);
}

function kpi_grid(items) {
    return `<div class="cc-kpis">${items.map(([label, value]) => `<div class="cc-kpi"><span>${__(label)}</span><strong>${value || 0}</strong></div>`).join("")}</div>`;
}

function panel(title, body) {
    return `<section class="cc-panel"><h3>${__(title)}</h3>${body || `<div class="text-muted">${__("No data")}</div>`}</section>`;
}

function table(rows, columns, doctype, key) {
    if (!rows.length) return `<div class="text-muted">${__("No data")}</div>`;
    return `<table class="table table-bordered cc-table"><thead><tr>${columns.map(c => `<th>${__(frappe.unscrub(c))}</th>`).join("")}</tr></thead><tbody>${rows.map(row => `<tr>${columns.map(c => `<td>${cell(row, c, doctype, key)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}

function cell(row, c, doctype, key) {
    let value = row[c];
    if (typeof value === "number" && (c.includes("value") || c.includes("revenue") || c.includes("target") || c.includes("pipeline") || c.includes("margin") || c.includes("gap"))) value = money(value);
    if (typeof value === "number" && (c.includes("percent") || c.includes("rate") || c.includes("achievement"))) value = pct(value);
    value = frappe.utils.escape_html(value == null ? "" : String(value));
    if (doctype && key && row[key]) {
        return `<a onclick="frappe.set_route('Form','${doctype}','${row[key]}')">${value}</a>`;
    }
    return value;
}

function funnel(rows) {
    return rows.map(row => `<div class="cc-funnel"><strong>${frappe.utils.escape_html(row.stage || "")}</strong><span>${row.opportunity_count || 0} deals</span><span>${money(row.pipeline_value)}</span><span>${pct(row.probability)}</span></div>`).join("");
}

function coverage_box(c) {
    return kpi_grid([["Remaining Target", money(c.remaining_target)], ["Coverage", `${(c.pipeline_coverage || 0).toFixed(1)}x`], ["Weighted Coverage", `${(c.weighted_pipeline_coverage || 0).toFixed(1)}x`], ["Status", c.coverage_status]]);
}

function forecast_box(f) {
    return kpi_grid([["Closed Won", money(f.closed_won)], ["Commit", money(f.commit)], ["Best Case", money(f.best_case)], ["Pipeline", money(f.pipeline)], ["Forecast", money(f.total_forecast)], ["Gap", money(f.forecast_gap)]]);
}

function aging_box(a) {
    const rows = Object.entries(a.buckets || {}).map(([bucket, row]) => ({ bucket, count: row.count, value: row.value }));
    return table(rows, ["bucket", "count", "value"], null, null) + table(a.oldest || [], ["opportunity_name", "customer", "opportunity_owner", "stage", "days_in_stage", "opportunity_value", "deal_health_status"], "CRM Opportunity", "name");
}

function lead_to_cash(flow) {
    return `<div class="cc-flow">${["leads", "opportunities", "quotations", "sales_orders", "invoices", "collected"].map(k => `<div><span>${__(frappe.unscrub(k))}</span><strong>${k === "collected" ? money(flow[k]) : (flow[k] || 0)}</strong></div>`).join("")}</div>`;
}

function quotation_box(q) {
    return kpi_grid([["Open Quotations", q.open_count], ["Quotation Value", money(q.quotation_value)], ["Converted", q.converted_count], ["Conversion", pct(q.conversion_rate)]]) + table(q.rows || [], ["name", "party_name", "custom_crm_opportunity", "grand_total", "valid_till", "status"], "Quotation", "name");
}

function concentration(c) {
    return kpi_grid([["Top 5 Customer Revenue", pct(c.top_5_percent)], ["Top 10 Customer Revenue", pct(c.top_10_percent)]]);
}

function win_loss(w) {
    return kpi_grid([["Won Count", w.won_count], ["Lost Count", w.lost_count], ["Win Rate", pct(w.win_rate)], ["Won Value", money(w.won_value)], ["Lost Value", money(w.lost_value)]]);
}

function velocity(v) {
    return kpi_grid([["Average Opportunity Age", Math.round(v.average_opportunity_age || 0)], ["Average Days to Win", Math.round(v.average_days_to_win || 0)]]) + table(v.stage_velocity || [], ["stage", "average_days", "max_days"], null, null);
}

function forecast_accuracy(f) {
    if (!f.available) return `<div class="text-muted">${__("Historical snapshots are not available yet")}</div>`;
    return kpi_grid([["Previous Forecast", money(f.previous_forecast)], ["Actual Revenue", money(f.actual_closed_revenue)], ["Variance", money(f.variance)], ["Accuracy", pct(f.forecast_accuracy_percent)]]);
}

function money(value) {
    return format_currency(value || 0);
}

function pct(value) {
    return `${Number(value || 0).toFixed(1)}%`;
}

function export_current(state) {
    const data = state.data || {};
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sales-management-command-center.json";
    a.click();
    URL.revokeObjectURL(url);
}

function inject_command_center_css() {
    if ($("#sales-command-center-css").length) return;
    $("head").append(`<style id="sales-command-center-css">
        .sales-command-center { padding: 14px; }
        .cc-loading { padding: 24px; }
        .cc-tabs { display:flex; gap:6px; flex-wrap:wrap; margin:10px 0 14px; }
        .cc-tab { border:1px solid var(--border-color); background:var(--card-bg); border-radius:6px; padding:7px 10px; }
        .cc-tab.active { background:var(--control-bg); font-weight:600; }
        .cc-section-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(420px,1fr)); gap:14px; align-items:start; }
        .cc-panel { border:1px solid var(--border-color); border-radius:8px; background:var(--card-bg); padding:14px; overflow:auto; }
        .cc-panel h3 { font-size:15px; margin:0 0 12px; }
        .cc-kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:8px; }
        .cc-kpi { border:1px solid var(--border-color); border-radius:8px; padding:10px; background:var(--fg-color); }
        .cc-kpi span { display:block; color:var(--text-muted); font-size:12px; }
        .cc-kpi strong { font-size:18px; }
        .cc-funnel, .cc-flow { display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:8px; border-top:1px solid var(--border-color); padding:8px 0; }
        .cc-flow div { border:1px solid var(--border-color); border-radius:8px; padding:10px; }
        .cc-table { min-width: 100%; font-size:12px; }
    </style>`);
}
