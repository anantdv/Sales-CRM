import frappe
from frappe.utils import now


def validate_task(doc, method=None):
    if doc.status == "Completed" and not doc.completed_on:
        doc.completed_on = now()


def update_linked_records(doc, method=None):
    if doc.crm_opportunity and doc.status in ("Open", "In Progress"):
        frappe.db.set_value(
            "CRM Opportunity",
            doc.crm_opportunity,
            {"next_action": doc.subject, "next_action_date": doc.due_date},
            update_modified=False,
        )
