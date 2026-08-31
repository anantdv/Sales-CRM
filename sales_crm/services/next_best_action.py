import frappe
from frappe.utils import add_days, cint, date_diff, flt, getdate, today

from sales_crm.services.pipeline import get_stage


def get_next_actions(user=None, company=None, limit=20):
    if not frappe.db.get_single_value("CRM Settings", "enable_next_best_action"):
        return []
    user = user or frappe.session.user
    actions = []
    actions.extend(opportunity_actions(user, company))
    actions.extend(lead_actions(user))
    actions.extend(task_actions(user))
    actions.extend(quotation_actions(user))
    return sorted(actions, key=lambda row: (-row["severity_score"], row.get("due_date") or today()))[: cint(limit or 20)]


def opportunity_actions(user, company=None):
    settings = frappe.get_single("CRM Settings")
    filters = {"status": "Open", "opportunity_owner": user}
    if company:
        filters["company"] = company
    rows = frappe.get_all(
        "CRM Opportunity",
        filters=filters,
        fields=["name", "opportunity_name", "customer", "lead", "opportunity_owner", "opportunity_value", "currency", "next_action", "next_action_date", "expected_close_date", "last_activity_date", "pipeline", "stage", "days_in_stage"],
        limit_page_length=200,
    )
    out = []
    stale_days = cint(settings.stale_opportunity_days or 30)
    high_value = flt(settings.high_value_opportunity_threshold or 250000)
    close_warning = cint(settings.expected_close_warning_days or 7)
    for row in rows:
        reasons = []
        score = 0
        due_date = row.next_action_date or row.expected_close_date
        if row.next_action_date and getdate(row.next_action_date) < getdate(today()):
            score += 30
            reasons.append("Overdue next action")
        if row.expected_close_date and getdate(row.expected_close_date) < getdate(today()):
            score += 30
            reasons.append("Expected close overdue")
        elif row.expected_close_date and getdate(row.expected_close_date) <= getdate(add_days(today(), close_warning)):
            score += 15
            reasons.append("Expected close approaching")
        if not row.last_activity_date or date_diff(today(), row.last_activity_date) > stale_days:
            score += 25
            reasons.append(f"No activity beyond {stale_days} days")
        if flt(row.opportunity_value) >= high_value:
            score += 20
            reasons.append("High-value opportunity")
        if not row.next_action:
            score += 15
            reasons.append("Opportunity has no next action")
        stage = get_stage(row.pipeline, row.stage)
        if stage and stage.maximum_age_days and cint(row.days_in_stage) > cint(stage.maximum_age_days):
            score += 20
            reasons.append("Opportunity has been in stage too long")
        if reasons:
            out.append(action("Opportunity", row.name, row.customer, row.name, None, row.opportunity_owner, row.opportunity_value, row.currency, due_date, score, "; ".join(reasons), "Contact stakeholder and schedule the next activity"))
    return out


def lead_actions(user):
    settings = frappe.get_single("CRM Settings")
    rows = frappe.get_all(
        "CRM Lead",
        filters={"lead_owner": user, "converted": 0},
        fields=["name", "organization_name", "lead_name", "lead_owner", "lead_status", "next_action_date", "estimated_value", "currency", "last_activity_date"],
        limit_page_length=100,
    )
    out = []
    for row in rows:
        score = 0
        reasons = []
        if row.next_action_date and getdate(row.next_action_date) <= getdate(today()):
            score += 30
            reasons.append("Lead has next action due")
        if row.lead_status == "Qualified":
            score += 15
            reasons.append("Qualified Lead not converted")
        if row.last_activity_date and date_diff(today(), row.last_activity_date) > cint(settings.stale_lead_days or 14):
            score += 15
            reasons.append("Lead has gone quiet")
        if reasons:
            out.append(action("Lead", row.name, row.organization_name, None, row.name, row.lead_owner, row.estimated_value, row.currency, row.next_action_date, score, "; ".join(reasons), "Qualify or convert the lead"))
    return out


def task_actions(user):
    rows = frappe.get_all("Sales Task", filters={"assigned_to": user, "status": ["in", ["Open", "In Progress"]]}, fields=["name", "subject", "customer", "crm_opportunity", "crm_lead", "assigned_to", "due_date"], limit_page_length=100)
    out = []
    for row in rows:
        if row.due_date and getdate(row.due_date) < getdate(today()):
            out.append(action("Sales Task", row.name, row.customer, row.crm_opportunity, row.crm_lead, row.assigned_to, None, None, row.due_date, 30, "Overdue Sales Task", row.subject))
    return out


def quotation_actions(user):
    warning_days = cint(frappe.db.get_single_value("CRM Settings", "quote_expiry_warning_days") or 7)
    rows = frappe.get_all(
        "Quotation",
        filters={"custom_crm_opportunity": ["is", "set"], "valid_till": ["<=", add_days(today(), warning_days)], "docstatus": ["<", 2]},
        fields=["name", "party_name", "custom_crm_opportunity", "valid_till", "grand_total", "currency"],
        limit_page_length=100,
    )
    out = []
    for row in rows:
        owner = frappe.db.get_value("CRM Opportunity", row.custom_crm_opportunity, "opportunity_owner")
        if owner != user:
            continue
        score = 30 if row.valid_till and getdate(row.valid_till) < getdate(today()) else 20
        out.append(action("Quotation", row.name, row.party_name, row.custom_crm_opportunity, None, owner, row.grand_total, row.currency, row.valid_till, score, "Quotation expires soon" if score == 20 else "Quotation expired", "Commercial follow-up"))
    return out


def action(record_type, record_name, customer, opportunity, lead, owner, value, currency, due_date, score, reason, recommended_action):
    return {
        "record_type": record_type,
        "record_name": record_name,
        "customer": customer,
        "opportunity": opportunity,
        "lead": lead,
        "priority": priority(score),
        "reason": reason,
        "recommended_action": recommended_action,
        "due_date": due_date,
        "owner": owner,
        "value": value,
        "currency": currency,
        "severity_score": min(100, score),
    }


def priority(score):
    if score >= 70:
        return "Critical"
    if score >= 45:
        return "High"
    if score >= 20:
        return "Medium"
    return "Low"
