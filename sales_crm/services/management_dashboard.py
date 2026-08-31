import frappe
from frappe.utils import add_days, add_months, date_diff, flt, get_first_day, getdate, today

from sales_crm.services.dashboard_utils import assert_management_access, crm_where, invoice_where, normalize_filters, percent, previous_period
from sales_crm.services.management_alerts import get_management_alerts


def get_management_dashboard(filters=None):
    assert_management_access()
    filters = normalize_filters(filters)
    return {
        "filters": dict(filters),
        "executive_kpis": get_executive_kpis(filters),
        "attention": get_attention_cards(filters),
        "pipeline": get_pipeline_metrics(filters),
        "coverage": get_pipeline_coverage(filters),
        "forecast": get_forecast_metrics(filters),
        "team": get_team_performance(filters),
        "leads": get_lead_metrics(filters),
        "accounts": get_account_metrics(filters),
        "activities": get_activity_metrics(filters),
        "revenue": get_revenue_metrics(filters),
        "intelligence": get_intelligence_metrics(filters),
        "alerts": get_management_alerts(filters),
    }


def get_executive_kpis(filters):
    revenue = get_revenue_total(filters)
    target = get_sales_target(filters)
    open_pipeline = sum_field("CRM Opportunity", "opportunity_value", filters, {"status": "Open"})
    weighted_pipeline = sum_field("CRM Opportunity", "weighted_value", filters, {"status": "Open"})
    closed_won = sum_field("CRM Opportunity", "opportunity_value", filters, {"status": "Won"})
    forecast = get_forecast_metrics(filters)["total_forecast"]
    outstanding = get_outstanding_receivables(filters)
    gross_margin = get_gross_margin(filters)
    return {
        "revenue_ytd": revenue,
        "sales_target_ytd": target,
        "achievement_percent": percent(revenue, target),
        "open_pipeline": open_pipeline,
        "weighted_pipeline": weighted_pipeline,
        "forecast": forecast,
        "target_gap": max(target - revenue, 0),
        "closed_won": closed_won,
        "gross_margin": gross_margin,
        "outstanding_receivables": outstanding,
    }


def get_attention_cards(filters):
    quote_warning = frappe.db.get_single_value("CRM Settings", "quote_expiry_warning_days") or 7
    return {
        "critical_deals": count_opps(filters, {"deal_health_status": "Critical"}),
        "deals_at_risk": count_opps(filters, {"deal_health_status": ["in", ["At Risk", "Critical"]]}),
        "stale_opportunities": count_opps(filters, {"stale": 1}),
        "expected_close_overdue": count_opps(filters, {"expected_close_date": ["<", today()], "status": "Open"}),
        "quotes_expiring_soon": frappe.db.count("Quotation", {"valid_till": ["between", [today(), add_days(today(), quote_warning)]], "docstatus": ["<", 2]}),
        "qualified_leads_uncontacted": frappe.db.count("CRM Lead", {"lead_status": "Qualified", "converted": 0, "last_activity_date": ["is", "not set"]}),
        "no_next_action": count_opps(filters, {"next_action": ["is", "not set"], "status": "Open"}),
        "high_value_without_decision_maker": high_value_without_decision_maker(filters),
    }


def get_pipeline_metrics(filters):
    where, params = crm_where(filters, "o")
    rows = frappe.db.sql(
        f"""
        select o.stage, count(*) opportunity_count,
               coalesce(sum(o.opportunity_value), 0) pipeline_value,
               coalesce(sum(o.weighted_value), 0) weighted_value,
               avg(o.probability) probability
        from `tabCRM Opportunity` o
        where {where} and o.status in ('Open', 'Won')
        group by o.stage
        order by min(o.current_stage_entered_on) asc
        """,
        params,
        as_dict=True,
    )
    total = sum(row.opportunity_count for row in rows) or 1
    for row in rows:
        row.stage_conversion_rate = percent(row.opportunity_count, total)
    return {"by_stage": rows, "top_deals": get_top_deals(filters), "aging": get_pipeline_aging(filters)}


def get_pipeline_coverage(filters):
    target = get_sales_target(filters)
    revenue = get_revenue_total(filters)
    remaining = max(target - revenue, 0)
    open_pipeline = sum_field("CRM Opportunity", "opportunity_value", filters, {"status": "Open"})
    weighted = sum_field("CRM Opportunity", "weighted_value", filters, {"status": "Open"})
    coverage = flt(open_pipeline) / flt(remaining or 1)
    weighted_coverage = flt(weighted) / flt(remaining or 1)
    good = flt(frappe.db.get_single_value("CRM Settings", "pipeline_coverage_good_threshold") or 3)
    watch = flt(frappe.db.get_single_value("CRM Settings", "pipeline_coverage_watch_threshold") or 2)
    status = "Good" if coverage >= good else "Watch" if coverage >= watch else "Risk"
    return {
        "remaining_target": remaining,
        "open_pipeline": open_pipeline,
        "weighted_pipeline": weighted,
        "pipeline_coverage": coverage,
        "weighted_pipeline_coverage": weighted_coverage,
        "coverage_status": status,
    }


def get_forecast_metrics(filters):
    where, params = crm_where(filters, "o")
    rows = frappe.db.sql(
        f"""
        select coalesce(o.forecast_category, 'Pipeline') forecast_category,
               count(*) opportunity_count,
               coalesce(sum(o.opportunity_value), 0) value
        from `tabCRM Opportunity` o
        where {where} and o.status in ('Open', 'Won')
        group by coalesce(o.forecast_category, 'Pipeline')
        """,
        params,
        as_dict=True,
    )
    summary = {row.forecast_category: row for row in rows}
    closed_won = summary.get("Closed Won", {}).get("value", 0) + sum_field("CRM Opportunity", "opportunity_value", filters, {"status": "Won"})
    commit = summary.get("Commit", {}).get("value", 0)
    best_case = summary.get("Best Case", {}).get("value", 0)
    pipeline = summary.get("Pipeline", {}).get("value", 0)
    target = get_sales_target(filters)
    total = closed_won + commit + best_case
    return {"categories": rows, "closed_won": closed_won, "commit": commit, "best_case": best_case, "pipeline": pipeline, "total_forecast": total, "target": target, "forecast_gap": max(target - total, 0), "by_salesperson": get_forecast_by_salesperson(filters)}


def get_team_performance(filters):
    where, params = crm_where(filters, "o")
    rows = frappe.db.sql(
        f"""
        select o.opportunity_owner salesperson,
               coalesce(sum(case when o.status='Open' then o.opportunity_value else 0 end), 0) open_pipeline,
               coalesce(sum(case when o.status='Open' then o.weighted_value else 0 end), 0) weighted_pipeline,
               coalesce(sum(case when o.status='Won' then o.opportunity_value else 0 end), 0) won_value,
               count(case when o.status='Won' then 1 end) won_deals,
               count(case when o.status='Lost' then 1 end) lost_deals,
               count(case when o.stale=1 then 1 end) stale_deals,
               count(case when o.deal_health_status in ('At Risk','Critical') then 1 end) at_risk_deals,
               avg(case when o.status='Won' then o.opportunity_value end) average_deal_size
        from `tabCRM Opportunity` o
        where {where}
        group by o.opportunity_owner
        order by won_value desc, weighted_pipeline desc
        limit 50
        """,
        params,
        as_dict=True,
    )
    for row in rows:
        row.target = get_sales_target(filters, row.salesperson)
        row.actual_revenue = get_revenue_total(filters, row.salesperson)
        row.achievement_percent = percent(row.actual_revenue, row.target)
        row.win_rate = percent(row.won_deals, (row.won_deals or 0) + (row.lost_deals or 0))
        row.activities = frappe.db.count("Sales Activity", {"assigned_to": row.salesperson, "activity_date": ["between", [filters.from_date, filters.to_date]]})
        row.meetings = frappe.db.count("Sales Activity", {"assigned_to": row.salesperson, "activity_type": ["in", ["Meeting", "Customer Visit", "Demo"]], "activity_date": ["between", [filters.from_date, filters.to_date]]})
        row.forecast = row.won_value + row.weighted_pipeline
        row.target_gap = max(row.target - row.actual_revenue, 0)
    return rows


def get_lead_metrics(filters):
    rows = frappe.db.sql(
        """
        select lead_status, count(*) lead_count, coalesce(sum(estimated_value), 0) estimated_value
        from `tabCRM Lead`
        where creation between %(from_date)s and %(to_date)s
        group by lead_status
        """,
        {"from_date": filters.from_date, "to_date": filters.to_date},
        as_dict=True,
    )
    total = sum(row.lead_count for row in rows) or 1
    for row in rows:
        row.conversion_percent = percent(row.lead_count, total)
    source = frappe.db.sql(
        """
        select coalesce(lead_source, 'Unknown') lead_source, count(*) leads,
               count(case when lead_status='Qualified' then 1 end) qualified,
               count(case when converted=1 then 1 end) converted,
               coalesce(sum(estimated_value), 0) estimated_value
        from `tabCRM Lead`
        where creation between %(from_date)s and %(to_date)s
        group by coalesce(lead_source, 'Unknown')
        order by leads desc
        limit 20
        """,
        {"from_date": filters.from_date, "to_date": filters.to_date},
        as_dict=True,
    )
    return {"funnel": rows, "lead_source": source}


def get_account_metrics(filters):
    rows = frappe.db.sql(
        """
        select p.name, p.customer, p.account_tier, p.account_owner, p.account_health_score,
               p.last_activity_date, p.engagement_status, p.outstanding_receivable,
               count(o.name) open_opportunities,
               coalesce(sum(o.opportunity_value), 0) pipeline
        from `tabCRM Account Profile` p
        left join `tabCRM Opportunity` o on o.customer=p.customer and o.status='Open'
        group by p.name, p.customer, p.account_tier, p.account_owner, p.account_health_score,
                 p.last_activity_date, p.engagement_status, p.outstanding_receivable
        order by pipeline desc
        limit 50
        """,
        as_dict=True,
    )
    return {"accounts": rows, "concentration": get_account_concentration(filters), "commercial_risk": get_commercial_risk(filters)}


def get_activity_metrics(filters):
    return frappe.db.sql(
        """
        select activity_type, assigned_to, count(*) activity_count,
               count(distinct crm_opportunity) opportunities_touched
        from `tabSales Activity`
        where activity_date between %(from_date)s and %(to_date)s
        group by activity_type, assigned_to
        order by activity_count desc
        limit 50
        """,
        {"from_date": filters.from_date, "to_date": filters.to_date},
        as_dict=True,
    )


def get_revenue_metrics(filters):
    return {
        "trend": get_sales_trend(filters),
        "lead_to_cash": get_lead_to_cash(filters),
        "quotation": get_quotation_metrics(filters),
        "product": get_product_performance(filters),
        "territory": get_territory_performance(filters),
        "receivables": get_receivables(filters),
    }


def get_intelligence_metrics(filters):
    return {
        "win_loss": get_win_loss(filters),
        "lost_reasons": get_lost_reasons(filters),
        "competitors": get_competitors(filters),
        "velocity": get_sales_velocity(filters),
        "slipping_deals": get_slipping_deals(filters),
        "pipeline_movement": get_pipeline_movement(filters),
        "forecast_accuracy": get_forecast_accuracy(filters),
    }


def get_top_deals(filters, limit=10):
    where, params = crm_where(filters, "o")
    return frappe.db.sql(
        f"""
        select name, opportunity_name, customer, opportunity_owner, stage, opportunity_value,
               probability, weighted_value, expected_close_date, deal_health_status,
               last_activity_date, next_action
        from `tabCRM Opportunity` o
        where {where} and status='Open'
        order by opportunity_value desc
        limit {int(limit)}
        """,
        params,
        as_dict=True,
    )


def get_pipeline_aging(filters):
    where, params = crm_where(filters, "o")
    rows = frappe.db.sql(
        f"""
        select name, opportunity_name, customer, opportunity_owner, stage, days_in_stage,
               opportunity_age_days, opportunity_value, expected_close_date, deal_health_status
        from `tabCRM Opportunity` o
        where {where} and status='Open'
        order by days_in_stage desc
        limit 25
        """,
        params,
        as_dict=True,
    )
    buckets = {"0-7": {"count": 0, "value": 0}, "8-14": {"count": 0, "value": 0}, "15-30": {"count": 0, "value": 0}, "31-60": {"count": 0, "value": 0}, "61-90": {"count": 0, "value": 0}, "90+": {"count": 0, "value": 0}}
    for row in rows:
        days = row.days_in_stage or 0
        bucket = "0-7" if days <= 7 else "8-14" if days <= 14 else "15-30" if days <= 30 else "31-60" if days <= 60 else "61-90" if days <= 90 else "90+"
        buckets[bucket]["count"] += 1
        buckets[bucket]["value"] += row.opportunity_value or 0
    return {"buckets": buckets, "oldest": rows}


def get_forecast_by_salesperson(filters):
    where, params = crm_where(filters, "o")
    rows = frappe.db.sql(
        f"""
        select opportunity_owner salesperson,
               coalesce(sum(case when status='Won' then opportunity_value else 0 end), 0) closed_won,
               coalesce(sum(case when forecast_category='Commit' then opportunity_value else 0 end), 0) commit,
               coalesce(sum(case when forecast_category='Best Case' then opportunity_value else 0 end), 0) best_case,
               coalesce(sum(case when forecast_category='Pipeline' then opportunity_value else 0 end), 0) pipeline
        from `tabCRM Opportunity` o
        where {where}
        group by opportunity_owner
        """,
        params,
        as_dict=True,
    )
    for row in rows:
        row.target = get_sales_target(filters, row.salesperson)
        row.forecast = (row.closed_won or 0) + (row.commit or 0) + (row.best_case or 0)
        row.achievement = percent(row.closed_won, row.target)
        row.gap = max(row.target - row.forecast, 0)
    return rows


def get_sales_trend(filters):
    return frappe.db.sql(
        """
        select date_format(posting_date, '%%Y-%%m') period,
               coalesce(sum(grand_total), 0) revenue,
               null gross_margin
        from `tabSales Invoice`
        where docstatus=1 and posting_date >= %(start)s and posting_date <= %(end)s
        group by date_format(posting_date, '%%Y-%%m')
        order by period desc
        limit 12
        """,
        {"start": add_months(get_first_day(today()), -11), "end": today()},
        as_dict=True,
    )


def get_lead_to_cash(filters):
    opps = count_opps(filters, {})
    quotes = frappe.db.count("Quotation", {"transaction_date": ["between", [filters.from_date, filters.to_date]], "docstatus": ["<", 2]})
    orders = frappe.db.count("Sales Order", {"transaction_date": ["between", [filters.from_date, filters.to_date]], "docstatus": 1})
    invoices = frappe.db.count("Sales Invoice", {"posting_date": ["between", [filters.from_date, filters.to_date]], "docstatus": 1})
    collected = frappe.db.sql("select coalesce(sum(paid_amount),0) from `tabPayment Entry` where docstatus=1 and posting_date between %s and %s", (filters.from_date, filters.to_date))[0][0] if frappe.db.exists("DocType", "Payment Entry") else 0
    leads = frappe.db.count("CRM Lead", {"creation": ["between", [filters.from_date, filters.to_date]]})
    return {"leads": leads, "opportunities": opps, "quotations": quotes, "sales_orders": orders, "invoices": invoices, "collected": collected}


def get_quotation_metrics(filters):
    rows = frappe.get_all("Quotation", filters={"transaction_date": ["between", [filters.from_date, filters.to_date]], "docstatus": ["<", 2]}, fields=["name", "party_name", "custom_crm_opportunity", "grand_total", "currency", "valid_till", "status"], limit_page_length=50)
    converted = sum(1 for row in rows if row.status == "Ordered")
    return {"open_count": len(rows), "quotation_value": sum(row.grand_total or 0 for row in rows), "converted_count": converted, "conversion_rate": percent(converted, len(rows)), "rows": rows}


def get_product_performance(filters):
    return frappe.db.sql(
        """
        select coalesce(p.item_group, 'Unknown') item_group,
               coalesce(sum(p.amount), 0) pipeline_value,
               count(distinct p.parent) opportunity_count
        from `tabCRM Opportunity Product` p
        join `tabCRM Opportunity` o on o.name=p.parent
        where o.status='Open'
        group by coalesce(p.item_group, 'Unknown')
        order by pipeline_value desc
        limit 25
        """,
        as_dict=True,
    )


def get_territory_performance(filters):
    where, params = crm_where(filters, "o")
    return frappe.db.sql(
        f"""
        select coalesce(o.territory, 'Unassigned') territory,
               coalesce(sum(case when o.status='Open' then o.opportunity_value else 0 end), 0) pipeline,
               coalesce(sum(case when o.status='Open' then o.weighted_value else 0 end), 0) weighted_pipeline,
               count(distinct o.customer) customers,
               count(*) opportunities,
               count(case when o.status='Won' then 1 end) won,
               count(case when o.status='Lost' then 1 end) lost
        from `tabCRM Opportunity` o
        where {where}
        group by coalesce(o.territory, 'Unassigned')
        order by pipeline desc
        limit 50
        """,
        params,
        as_dict=True,
    )


def get_receivables(filters):
    rows = frappe.get_all("Customer", fields=["name", "customer_name", "territory", "outstanding_amount"], filters={"outstanding_amount": [">", 0]}, limit_page_length=50)
    return {"outstanding": sum(row.outstanding_amount or 0 for row in rows), "rows": rows}


def get_win_loss(filters):
    won = count_opps(filters, {"status": "Won"})
    lost = count_opps(filters, {"status": "Lost"})
    won_value = sum_field("CRM Opportunity", "opportunity_value", filters, {"status": "Won"})
    lost_value = sum_field("CRM Opportunity", "opportunity_value", filters, {"status": "Lost"})
    return {"won_count": won, "lost_count": lost, "win_rate": percent(won, won + lost), "won_value": won_value, "lost_value": lost_value}


def get_lost_reasons(filters):
    where, params = crm_where(filters, "o")
    return frappe.db.sql(f"select coalesce(lost_reason,'Unknown') lost_reason, count(*) count, coalesce(sum(opportunity_value),0) lost_value from `tabCRM Opportunity` o where {where} and status='Lost' group by coalesce(lost_reason,'Unknown') order by lost_value desc limit 20", params, as_dict=True)


def get_competitors(filters):
    where, params = crm_where(filters, "o")
    return frappe.db.sql(f"select coalesce(competitor,'Unknown') competitor, count(*) deals_faced, count(case when status='Won' then 1 end) wins, count(case when status='Lost' then 1 end) losses, coalesce(sum(case when status='Lost' then opportunity_value else 0 end),0) lost_value from `tabCRM Opportunity` o where {where} and competitor is not null group by coalesce(competitor,'Unknown') limit 20", params, as_dict=True)


def get_sales_velocity(filters):
    return {
        "average_opportunity_age": frappe.db.sql("select avg(opportunity_age_days) from `tabCRM Opportunity` where status='Open'")[0][0] or 0,
        "average_days_to_win": frappe.db.sql("select avg(datediff(won_date, creation)) from `tabCRM Opportunity` where status='Won' and won_date is not null")[0][0] or 0,
        "stage_velocity": frappe.db.sql("select stage, avg(days_in_stage) average_days, max(days_in_stage) max_days from `tabCRM Opportunity` where status='Open' group by stage order by average_days desc", as_dict=True),
    }


def get_slipping_deals(filters):
    return frappe.get_all("CRM Opportunity", filters={"status": "Open", "expected_close_date": ["<", today()]}, fields=["name", "opportunity_name", "opportunity_owner", "expected_close_date", "stage", "opportunity_value"], order_by="expected_close_date asc", limit_page_length=25)


def get_pipeline_movement(filters):
    return frappe.db.sql(
        """
        select status, count(*) count, coalesce(sum(value),0) value
        from `tabCRM Pipeline Snapshot`
        where snapshot_date between %(from_date)s and %(to_date)s
        group by status
        """,
        {"from_date": filters.from_date, "to_date": filters.to_date},
        as_dict=True,
    )


def get_forecast_accuracy(filters):
    snapshots = frappe.db.count("CRM Pipeline Snapshot", {"snapshot_date": ["<", filters.from_date]})
    if not snapshots:
        return {"available": False}
    previous_forecast = frappe.db.sql("select coalesce(sum(weighted_value),0) from `tabCRM Pipeline Snapshot` where snapshot_date < %s", filters.from_date)[0][0]
    actual = get_revenue_total(filters)
    variance = actual - previous_forecast
    return {"available": True, "previous_forecast": previous_forecast, "actual_closed_revenue": actual, "variance": variance, "forecast_accuracy_percent": 100 - abs(percent(variance, previous_forecast))}


def get_account_concentration(filters):
    rows = frappe.db.sql("select customer, coalesce(sum(grand_total),0) revenue from `tabSales Invoice` where docstatus=1 and posting_date between %s and %s group by customer order by revenue desc", (filters.from_date, filters.to_date), as_dict=True)
    total = sum(row.revenue for row in rows) or 1
    return {"top_5_percent": percent(sum(row.revenue for row in rows[:5]), total), "top_10_percent": percent(sum(row.revenue for row in rows[:10]), total)}


def get_commercial_risk(filters):
    rows = frappe.db.sql("select customer, coalesce(sum(opportunity_value),0) pipeline from `tabCRM Opportunity` where status='Open' group by customer having pipeline > 0 order by pipeline desc limit 20", as_dict=True)
    out = []
    for row in rows:
        outstanding = frappe.db.get_value("Customer", row.customer, "outstanding_amount") or 0
        if outstanding:
            row.outstanding = outstanding
            row.flag = "Commercial Risk"
            out.append(row)
    return out


def get_revenue_total(filters, salesperson=None):
    where, params = invoice_where(filters, "si")
    if salesperson:
        where += " and si.owner=%(salesperson)s"
        params["salesperson"] = salesperson
    return frappe.db.sql(f"select coalesce(sum(si.grand_total),0) from `tabSales Invoice` si where {where}", params)[0][0] or 0


def get_gross_margin(filters):
    return None


def get_outstanding_receivables(filters):
    rows = frappe.get_all("Customer", fields=["outstanding_amount"], filters={"outstanding_amount": [">", 0]}, limit_page_length=500)
    return sum(row.outstanding_amount or 0 for row in rows)


def get_sales_target(filters, salesperson=None):
    target_filters = {"active": 1, "from_date": ["<=", filters.to_date], "to_date": [">=", filters.from_date]}
    if filters.get("company"):
        target_filters["company"] = filters.company
    if salesperson or filters.get("salesperson"):
        target_filters["salesperson"] = salesperson or filters.salesperson
    if filters.get("territory"):
        target_filters["territory"] = filters.territory
    if filters.get("product_group"):
        target_filters["product_group"] = filters.product_group
    return frappe.db.get_value("CRM Sales Target", target_filters, "sum(target_amount)") or 0


def sum_field(doctype, fieldname, filters, extra=None):
    query_filters = dict(extra or {})
    for key, column in {"company": "company", "pipeline": "pipeline", "salesperson": "opportunity_owner", "territory": "territory", "opportunity_type": "opportunity_type"}.items():
        if filters.get(key):
            query_filters[column] = filters.get(key)
    return frappe.db.get_value(doctype, query_filters, f"sum({fieldname})") or 0


def count_opps(filters, extra):
    query_filters = dict(extra or {})
    for key, column in {"company": "company", "pipeline": "pipeline", "salesperson": "opportunity_owner", "territory": "territory", "opportunity_type": "opportunity_type"}.items():
        if filters.get(key):
            query_filters[column] = filters.get(key)
    return frappe.db.count("CRM Opportunity", query_filters)


def high_value_without_decision_maker(filters):
    high_value = frappe.db.get_single_value("CRM Settings", "high_value_opportunity_threshold") or 250000
    rows = frappe.get_all("CRM Opportunity", filters={"status": "Open", "opportunity_value": [">=", high_value]}, fields=["name"])
    count = 0
    for row in rows:
        if not frappe.db.exists("CRM Opportunity Contact", {"parent": row.name, "role": "Decision Maker"}):
            count += 1
    return count
