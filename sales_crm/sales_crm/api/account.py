import frappe
from frappe.utils import get_year_start, today


@frappe.whitelist()
def get_account_360(account_profile):
    profile = frappe.get_doc("CRM Account Profile", account_profile)
    customer = profile.customer
    return {
        "profile": profile.as_dict(),
        "contacts": get_contacts(customer),
        "relationships": frappe.get_all("CRM Contact Relationship", filters={"customer": customer}, fields=["contact", "role", "decision_influence", "relationship_strength", "last_contact_date", "active"]),
        "opportunities": frappe.get_all("CRM Opportunity", filters={"customer": customer}, fields=["name", "opportunity_name", "stage", "status", "opportunity_value", "weighted_value", "expected_close_date"]),
        "activities": frappe.get_all("Sales Activity", filters={"customer": customer}, fields=["name", "activity_date", "activity_type", "subject", "status", "outcome"], order_by="activity_date desc", limit_page_length=20),
        "quotations": frappe.get_all("Quotation", filters={"party_name": customer}, fields=["name", "transaction_date", "status", "grand_total", "currency"], limit_page_length=20),
        "sales_orders": frappe.get_all("Sales Order", filters={"customer": customer}, fields=["name", "transaction_date", "status", "grand_total", "currency"], limit_page_length=20),
        "invoices": frappe.get_all("Sales Invoice", filters={"customer": customer}, fields=["name", "posting_date", "status", "grand_total", "outstanding_amount"], limit_page_length=20),
        "service": get_optional_service_data(customer),
        "summary": get_summary(customer),
    }


def get_contacts(customer):
    links = frappe.get_all("Dynamic Link", filters={"link_doctype": "Customer", "link_name": customer, "parenttype": "Contact"}, pluck="parent")
    if not links:
        return []
    return frappe.get_all("Contact", filters={"name": ["in", links]}, fields=["name", "first_name", "last_name", "designation", "status"])


def get_summary(customer):
    open_opps = frappe.get_all("CRM Opportunity", filters={"customer": customer, "status": "Open"}, fields=["opportunity_value", "weighted_value"])
    ytd = frappe.db.sql(
        """
        select coalesce(sum(grand_total), 0)
        from `tabSales Invoice`
        where customer=%s and docstatus=1 and posting_date >= %s
        """,
        (customer, get_year_start(today())),
    )[0][0]
    outstanding = frappe.db.get_value("Customer", customer, "outstanding_amount") or 0
    return {
        "open_opportunities": len(open_opps),
        "pipeline_value": sum(row.opportunity_value or 0 for row in open_opps),
        "weighted_pipeline": sum(row.weighted_value or 0 for row in open_opps),
        "sales_ytd": ytd,
        "outstanding_receivable": outstanding,
    }


def get_optional_service_data(customer):
    data = {}
    optional = {
        "Service Tickets": "Service Ticket",
        "Customer Equipment": "Customer Equipment",
        "Service Contracts": "Service Contract",
    }
    for label, doctype in optional.items():
        if frappe.db.exists("DocType", doctype):
            data[label] = frappe.get_all(doctype, filters={"customer": customer}, fields=["name", "status", "modified"], limit_page_length=20)
    return data
