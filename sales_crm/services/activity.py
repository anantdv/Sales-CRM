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
        update_account_profile(doc)
    create_follow_up_task(doc)


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


def update_account_profile(doc):
    values = {"last_activity_date": doc.activity_date or today()}
    customer = doc.customer or frappe.db.get_value("CRM Account Profile", doc.crm_account_profile, "customer")
    if customer:
        values.update(get_engagement_summary(customer))
    frappe.db.set_value("CRM Account Profile", doc.crm_account_profile, values, update_modified=False)


def get_engagement_summary(customer):
    from frappe.utils import add_days, date_diff, getdate

    last_activity = frappe.db.get_value("Sales Activity", {"customer": customer}, "activity_date", order_by="activity_date desc")
    settings = frappe.get_single("CRM Settings")
    if last_activity and date_diff(today(), getdate(last_activity)) <= (settings.engagement_active_days or 7):
        status = "Active"
    elif last_activity and date_diff(today(), getdate(last_activity)) <= (settings.engagement_moderate_days or 30):
        status = "Moderate"
    elif last_activity and date_diff(today(), getdate(last_activity)) <= (settings.engagement_low_days or 60):
        status = "Low"
    else:
        status = "Dormant"
    return {
        "activities_last_30_days": frappe.db.count("Sales Activity", {"customer": customer, "activity_date": [">=", add_days(today(), -30)]}),
        "meetings_last_90_days": frappe.db.count("Sales Activity", {"customer": customer, "activity_type": ["in", ["Meeting", "Customer Visit", "Demo"]], "activity_date": [">=", add_days(today(), -90)]}),
        "open_follow_ups": frappe.db.count("Sales Task", {"customer": customer, "status": ["in", ["Open", "In Progress"]]}),
        "active_opportunities": frappe.db.count("CRM Opportunity", {"customer": customer, "status": "Open"}),
        "stale_opportunities": frappe.db.count("CRM Opportunity", {"customer": customer, "status": "Open", "stale": 1}),
        "engagement_status": status,
    }


def create_follow_up_task(doc):
    if doc.status != "Completed" or not doc.follow_up_required or not doc.follow_up_date:
        return
    if frappe.db.exists("Sales Task", {"sales_activity": doc.name}):
        return
    task = frappe.new_doc("Sales Task")
    task.subject = doc.next_action or f"Follow up: {doc.subject}"
    task.task_type = "Follow-up"
    task.priority = "Medium"
    task.assigned_to = doc.assigned_to or frappe.session.user
    task.due_date = doc.follow_up_date
    task.crm_lead = doc.crm_lead
    task.customer = doc.customer
    task.contact = doc.contact
    task.crm_opportunity = doc.crm_opportunity
    task.sales_activity = doc.name
    task.description = doc.outcome or doc.notes
    task.insert(ignore_permissions=True)
