import frappe
from frappe.utils import add_days, date_diff, flt, getdate, today

from sales_crm.services.dashboard_utils import normalize_filters


def get_management_alerts(filters=None, limit=30):
    filters = normalize_filters(filters)
    alerts = []
    alerts.extend(deal_alerts(filters))
    alerts.extend(commercial_risk_alerts(filters))
    alerts.extend(coverage_alerts(filters))
    severity_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    return sorted(alerts, key=lambda row: (-severity_order.get(row["severity"], 0), -(row.get("value") or 0)))[:limit]


def deal_alerts(filters):
    clauses = ["status='Open'"]
    params = {}
    for key in ("company", "pipeline", "territory", "opportunity_type"):
        if filters.get(key):
            clauses.append(f"{key}=%({key})s")
            params[key] = filters.get(key)
    rows = frappe.db.sql(
        f"""
        select name, opportunity_name, customer, opportunity_owner, opportunity_value, currency,
               expected_close_date, last_activity_date, next_action, risk_level, deal_health_status
        from `tabCRM Opportunity`
        where {' and '.join(clauses)}
        order by opportunity_value desc
        limit 100
        """,
        params,
        as_dict=True,
    )
    alerts = []
    high_value = frappe.db.get_single_value("CRM Settings", "high_value_opportunity_threshold") or 250000
    stale_days = frappe.db.get_single_value("CRM Settings", "stale_opportunity_days") or 30
    for row in rows:
        reasons = []
        severity = "Medium"
        if row.expected_close_date and getdate(row.expected_close_date) < getdate(today()):
            reasons.append(f"Expected close overdue by {date_diff(today(), row.expected_close_date)} days")
            severity = "Critical"
        if not row.last_activity_date or date_diff(today(), row.last_activity_date) > stale_days:
            reasons.append("No recent activity")
            severity = "Critical" if flt(row.opportunity_value) >= high_value else max_severity(severity, "High")
        if not row.next_action:
            reasons.append("No next action")
            severity = max_severity(severity, "High")
        if row.risk_level in ("High", "Critical") or row.deal_health_status in ("At Risk", "Critical"):
            reasons.append("Deal health requires attention")
            severity = max_severity(severity, row.risk_level if row.risk_level == "Critical" else "High")
        if reasons:
            alerts.append(alert(severity, "Deal", row.opportunity_name, "CRM Opportunity", row.name, row.opportunity_owner, row.opportunity_value, "; ".join(reasons), "Review opportunity and confirm next management action"))
    return alerts


def commercial_risk_alerts(filters):
    if filters.get("salesperson"):
        return []
    rows = frappe.db.sql(
        """
        select o.customer, sum(o.opportunity_value) as pipeline, max(o.name) as opportunity
        from `tabCRM Opportunity` o
        where o.status='Open' and (%(company)s is null or o.company=%(company)s)
        group by o.customer
        having pipeline > 0
        order by pipeline desc
        limit 30
        """,
        {"company": filters.get("company")},
        as_dict=True,
    )
    out = []
    for row in rows:
        outstanding = frappe.db.get_value("Customer", row.customer, "outstanding_amount") or 0
        if outstanding > 0:
            out.append(alert("High", "Commercial Risk", row.customer, "Customer", row.customer, None, row.pipeline, f"Customer has open pipeline and outstanding receivables of {outstanding}", "Review credit and commercial exposure"))
    return out


def coverage_alerts(filters):
    from sales_crm.services.management_dashboard import get_pipeline_coverage

    coverage = get_pipeline_coverage(filters)
    if coverage["coverage_status"] == "Risk":
        return [alert("High", "Pipeline Coverage", "Coverage below threshold", None, None, None, coverage["open_pipeline"], f"Pipeline coverage is {coverage['pipeline_coverage']:.1f}x", "Review pipeline generation plan")]
    return []


def alert(severity, category, message, record_type, record_name, owner, value, reason, recommended_action):
    return {
        "severity": severity,
        "category": category,
        "message": message,
        "record_type": record_type,
        "record_name": record_name,
        "owner": owner,
        "value": value,
        "reason": reason,
        "recommended_action": recommended_action,
    }


def max_severity(a, b):
    order = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
    return a if order.get(a, 0) >= order.get(b, 0) else b
