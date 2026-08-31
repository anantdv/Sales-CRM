import frappe
from frappe.utils import date_diff, getdate, now, today


def validate_lead(doc, method=None):
    if not doc.lead_status:
        doc.lead_status = frappe.db.get_single_value("CRM Settings", "default_lead_status") or "New"

    if doc.creation:
        doc.lead_age_days = date_diff(today(), getdate(doc.creation))

    if not doc.lead_owner and frappe.db.get_single_value("CRM Settings", "default_lead_owner"):
        doc.lead_owner = frappe.db.get_single_value("CRM Settings", "default_lead_owner")
        doc.assigned_date = now()

    doc.duplicate_warning = get_duplicate_warning(doc)


def get_duplicate_warning(doc):
    settings = frappe.get_single("CRM Settings")
    if not settings.lead_duplicate_check:
        return ""

    warnings = []
    if settings.duplicate_check_email and doc.email:
        if frappe.db.exists("Contact Email", {"email_id": doc.email}) or frappe.db.exists(
            "CRM Lead", {"email": doc.email, "name": ["!=", doc.name]}
        ):
            warnings.append("Email matches an existing lead/contact")

    if settings.duplicate_check_mobile and doc.mobile_no:
        if frappe.db.exists("CRM Lead", {"mobile_no": doc.mobile_no, "name": ["!=", doc.name]}):
            warnings.append("Mobile number matches an existing lead")

    if settings.duplicate_check_company and doc.organization_name:
        if frappe.db.exists("Customer", {"customer_name": doc.organization_name}):
            warnings.append("Organization matches an existing customer")

    return "\n".join(warnings)
