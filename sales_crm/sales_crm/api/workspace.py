import frappe
from frappe.utils import add_days, getdate, today

from sales_crm.services.next_best_action import get_next_actions


@frappe.whitelist()
def get_sales_workspace(company=None):
    user = frappe.session.user
    return {
        "user": get_user(user),
        "kpis": get_kpis(user, company),
        "agenda": get_agenda(user),
        "next_actions": get_next_actions(user=user, company=company, limit=20),
        "pipeline_summary": get_pipeline_summary(user, company),
        "closing_soon": get_closing_soon(user, company),
        "activity_summary": get_activity_summary(user),
        "notifications": get_notifications(user, company),
    }


def get_user(user):
    full_name = frappe.db.get_value("User", user, "full_name") or user
    return {"name": user, "full_name": full_name, "date": today()}


def get_kpis(user, company=None):
    month_end = add_days(today(), 31)
    opp_filters = {"opportunity_owner": user, "status": "Open"}
    if company:
        opp_filters["company"] = company
    closing = frappe.get_all("CRM Opportunity", filters={**opp_filters, "expected_close_date": ["between", [today(), month_end]]}, fields=["opportunity_value"])
    return {
        "followups_due": frappe.db.count("Sales Task", {"assigned_to": user, "status": ["in", ["Open", "In Progress"]], "due_date": today()}),
        "overdue_activities": frappe.db.count("Sales Activity", {"assigned_to": user, "status": "Planned", "activity_date": ["<", today()]}),
        "meetings_today": frappe.db.count("Sales Activity", {"assigned_to": user, "activity_type": ["in", ["Meeting", "Customer Visit", "Demo"]], "activity_date": today()}),
        "hot_leads": frappe.db.count("CRM Lead", {"lead_owner": user, "lead_status": ["in", ["Qualified", "Qualifying"]], "converted": 0}),
        "open_opportunities": frappe.db.count("CRM Opportunity", opp_filters),
        "closing_this_month": sum(row.opportunity_value or 0 for row in closing),
        "quotes_expiring_soon": count_quotes_expiring(user),
        "deals_at_risk": frappe.db.count("CRM Opportunity", {**opp_filters, "risk_level": ["in", ["High", "Critical"]]}),
    }


def get_agenda(user):
    return frappe.get_all(
        "Sales Activity",
        filters={"assigned_to": user, "activity_date": today(), "status": ["in", ["Planned", "Completed"]]},
        fields=["name", "activity_type", "subject", "start_time", "customer", "crm_opportunity", "status"],
        order_by="start_time asc, modified asc",
        limit_page_length=50,
    )


def get_pipeline_summary(user, company=None):
    filters = ["opportunity_owner=%s", "status='Open'"]
    params = [user]
    if company:
        filters.append("company=%s")
        params.append(company)
    return frappe.db.sql(
        f"""
        select stage, count(*) as opportunity_count,
               coalesce(sum(opportunity_value), 0) as pipeline_value,
               coalesce(sum(weighted_value), 0) as weighted_value
        from `tabCRM Opportunity`
        where {' and '.join(filters)}
        group by stage
        order by min(current_stage_entered_on) asc
        """,
        params,
        as_dict=True,
    )


def get_closing_soon(user, company=None):
    filters = {"opportunity_owner": user, "status": "Open", "expected_close_date": ["<=", add_days(today(), 60)]}
    if company:
        filters["company"] = company
    rows = frappe.get_all(
        "CRM Opportunity",
        filters=filters,
        fields=["name", "opportunity_name", "customer", "opportunity_value", "currency", "stage", "probability", "expected_close_date", "deal_health_status"],
        order_by="expected_close_date asc",
        limit_page_length=25,
    )
    for row in rows:
        if getdate(row.expected_close_date) < getdate(today()):
            row.range = "Overdue"
        elif getdate(row.expected_close_date) <= getdate(add_days(today(), 7)):
            row.range = "This Week"
        elif getdate(row.expected_close_date) <= getdate(add_days(today(), 30)):
            row.range = "Next 30 Days"
        else:
            row.range = "Next 60 Days"
    return rows


def get_activity_summary(user):
    week_start = add_days(today(), -7)
    return {
        "activities_completed_week": frappe.db.count("Sales Activity", {"assigned_to": user, "status": "Completed", "activity_date": [">=", week_start]}),
        "meetings_week": frappe.db.count("Sales Activity", {"assigned_to": user, "activity_type": ["in", ["Meeting", "Customer Visit", "Demo"]], "activity_date": [">=", week_start]}),
        "followups_overdue": frappe.db.count("Sales Task", {"assigned_to": user, "status": ["in", ["Open", "In Progress"]], "due_date": ["<", today()]}),
    }


def count_quotes_expiring(user):
    warning_days = frappe.db.get_single_value("CRM Settings", "quote_expiry_warning_days") or 7
    rows = frappe.get_all(
        "Quotation",
        filters={"custom_crm_opportunity": ["is", "set"], "valid_till": ["between", [today(), add_days(today(), warning_days)]], "docstatus": ["<", 2]},
        fields=["custom_crm_opportunity"],
        limit_page_length=100,
    )
    count = 0
    for row in rows:
        if frappe.db.get_value("CRM Opportunity", row.custom_crm_opportunity, "opportunity_owner") == user:
            count += 1
    return count


def get_notifications(user, company=None):
    actions = get_next_actions(user=user, company=company, limit=10)
    notifications = []
    for action in actions:
        if action["priority"] in ("Critical", "High"):
            notifications.append(
                {
                    "title": action["reason"],
                    "message": action["recommended_action"],
                    "doctype": action["record_type"],
                    "docname": action["record_name"],
                    "priority": action["priority"],
                    "due_date": action["due_date"],
                }
            )
    return notifications
