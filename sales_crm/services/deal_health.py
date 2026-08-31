import frappe
from frappe.utils import add_days, cint, date_diff, flt, getdate, today

from sales_crm.services.pipeline import get_stage


def evaluate_deal_health(doc):
    score = 30
    positives = []
    risks = []
    settings = frappe.get_single("CRM Settings")
    stale_days = cint(settings.stale_opportunity_days or 30)

    if doc.expected_close_date:
        score += 10
        positives.append("Expected close date exists")
        if getdate(doc.expected_close_date) < getdate(today()):
            score -= 20
            risks.append("Expected close is overdue")
    else:
        risks.append("Expected close date is missing")

    if doc.next_action and doc.next_action_date:
        score += 10
        positives.append("Next action scheduled")
    else:
        score -= 15
        risks.append("No next action scheduled")

    if doc.last_activity_date and date_diff(today(), doc.last_activity_date) <= 7:
        score += 15
        positives.append("Recent activity")
    elif doc.last_activity_date and date_diff(today(), doc.last_activity_date) > stale_days:
        score -= 20
        risks.append(f"No activity for {date_diff(today(), doc.last_activity_date)} days")

    if doc.primary_contact:
        score += 10
        positives.append("Primary contact identified")
    else:
        score -= 10
        risks.append("No primary contact")

    roles = [row.role for row in doc.get("contacts") or []]
    if "Decision Maker" in roles:
        score += 10
        positives.append("Decision maker identified")
    else:
        risks.append("No Decision Maker identified")
    if "Champion" not in roles:
        risks.append("No internal Champion identified")
    if len(roles) > 1:
        score += 10
        positives.append("Multiple stakeholders mapped")

    if flt(doc.qualification_score) >= 70:
        score += 15
        positives.append("Qualification complete")
    elif flt(doc.qualification_score) < 50:
        score -= 10
        risks.append("Qualification below 50%")

    if doc.quotation:
        score += 10
        positives.append("Quotation created")

    stage = get_stage(doc.pipeline, doc.stage)
    if stage and stage.maximum_age_days and cint(doc.days_in_stage) > cint(stage.maximum_age_days):
        score -= 15
        risks.append(f"Opportunity has spent {doc.days_in_stage} days in {doc.stage}")

    if doc.risk_level in ("High", "Critical"):
        score -= 15
        risks.append(f"Risk marked {doc.risk_level}")

    score = max(0, min(100, score))
    if score >= 75:
        status = "Healthy"
    elif score >= 55:
        status = "Watch"
    elif score >= 35:
        status = "At Risk"
    else:
        status = "Critical"
    return {"score": score, "status": status, "positives": positives, "risks": risks}


def apply_deal_health(doc):
    if not frappe.db.get_single_value("CRM Settings", "enable_deal_health"):
        return
    result = evaluate_deal_health(doc)
    doc.deal_health_score = result["score"]
    doc.deal_health_status = result["status"]
    if result["status"] == "Critical":
        doc.risk_level = "Critical"
    elif result["status"] == "At Risk" and doc.risk_level not in ("Critical",):
        doc.risk_level = "High"


def update_stale_opportunities():
    settings = frappe.get_single("CRM Settings")
    stale_days = cint(settings.stale_opportunity_days or 30)
    cutoff = add_days(today(), -stale_days)
    rows = frappe.get_all(
        "CRM Opportunity",
        filters={"status": "Open"},
        fields=["name", "last_activity_date", "expected_close_date", "next_action_date"],
        limit_page_length=500,
    )
    for row in rows:
        stale = not row.last_activity_date or getdate(row.last_activity_date) < getdate(cutoff)
        risk = None
        if stale or (row.expected_close_date and getdate(row.expected_close_date) < getdate(today())):
            risk = "High"
        if row.next_action_date and getdate(row.next_action_date) < getdate(today()):
            risk = "Critical"
        values = {"stale": 1 if stale else 0}
        if risk:
            values["risk_level"] = risk
        frappe.db.set_value("CRM Opportunity", row.name, values, update_modified=False)


def get_deal_room(opportunity):
    doc = frappe.get_doc("CRM Opportunity", opportunity)
    health = evaluate_deal_health(doc)
    playbooks = frappe.get_all(
        "CRM Sales Playbook",
        filters={"active": 1, "pipeline": doc.pipeline, "applicable_stage": doc.stage},
        fields=["name", "playbook_name", "description"],
        limit_page_length=5,
    )
    checklist = frappe.get_all(
        "CRM Stage Checklist",
        filters={"pipeline": doc.pipeline, "stage": doc.stage, "active": 1},
        fields=["name", "checklist_item", "mandatory", "sequence"],
        order_by="sequence asc",
    )
    return {"health": health, "playbooks": playbooks, "checklist": checklist}
