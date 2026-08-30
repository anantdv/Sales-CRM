import frappe
from frappe import _
from frappe.utils import now, time_diff_in_hours, today


def validate_activity(doc, method=None):
    if not (doc.crm_lead or doc.customer or doc.crm_opportunity):
        frappe.throw(_("Link at least one CRM Lead, Customer, or CRM Opportunity."))

    if not doc.created_by:
        doc.created_by = frappe.session.user

    if doc.start_time and doc.end_time:
        doc.duration_minutes = int(time_diff_in_hours(doc.end_time, doc.start_time) * 60)

    if doc.status == "Completed" and not doc.completed_on:
        doc.completed_on = now()


def update_linked_records(doc, method=None):
    if doc.crm_lead:
        update_lead(doc)
    if doc.crm_opportunity:
        update_opportunity(doc)
    if doc.crm_account_profile:
        frappe.db.set_value("CRM Account Profile", doc.crm_account_profile, "last_activity_date", doc.activity_date or today(), update_modified=False)


def update_lead(doc):
    count = frappe.db.count("Sales Activity", {"crm_lead": doc.crm_lead})
    frappe.db.set_value(
        "CRM Lead",
        doc.crm_lead,
        {
            "last_activity_date": doc.activity_date or today(),
            "next_action": doc.next_action,
            "next_action_date": doc.next_action_date,
            "number_of_activities": count,
        },
        update_modified=False,
    )


def update_opportunity(doc):
    frappe.db.set_value(
        "CRM Opportunity",
        doc.crm_opportunity,
        {
            "last_activity_date": doc.activity_date or today(),
            "next_action": doc.next_action,
            "next_action_date": doc.next_action_date,
        },
        update_modified=False,
    )
