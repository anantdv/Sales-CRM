import frappe
from frappe import _
from frappe.utils import now

from sales_crm.services.pipeline import get_default_pipeline, get_first_stage


@frappe.whitelist()
def convert_lead(lead, conversion_type, customer_name=None, customer_group=None, territory=None, opportunity_name=None, pipeline=None, stage=None, opportunity_owner=None, expected_value=None, expected_close_date=None, existing_customer=None):
    lead_doc = frappe.get_doc("CRM Lead", lead)
    if lead_doc.converted:
        frappe.throw(_("Lead is already converted."))

    customer = None
    contact = None
    if conversion_type in ("create_customer_contact_opportunity", "create_customer"):
        customer = get_or_create_customer(lead_doc, customer_name, customer_group, territory)
        contact = get_or_create_contact(lead_doc, customer)
    elif conversion_type in ("link_customer_create_opportunity", "link_customer"):
        if not existing_customer:
            frappe.throw(_("Existing Customer is required."))
        customer = existing_customer

    opportunity = create_opportunity(
        lead_doc,
        customer,
        opportunity_name,
        pipeline,
        stage,
        opportunity_owner,
        expected_value,
        expected_close_date,
        territory,
    )

    lead_doc.converted = 1
    lead_doc.converted_on = now()
    lead_doc.lead_status = "Converted"
    lead_doc.converted_customer = customer
    lead_doc.converted_contact = contact
    lead_doc.converted_opportunity = opportunity.name
    lead_doc.save(ignore_permissions=True)

    return {"customer": customer, "contact": contact, "opportunity": opportunity.name}


def get_or_create_customer(lead_doc, customer_name=None, customer_group=None, territory=None):
    name = customer_name or lead_doc.organization_name or lead_doc.lead_name
    existing = frappe.db.get_value("Customer", {"customer_name": name}, "name")
    if existing:
        return existing

    customer = frappe.new_doc("Customer")
    customer.customer_name = name
    customer.customer_type = "Company" if lead_doc.organization_name else "Individual"
    customer.customer_group = customer_group or frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
    customer.territory = territory or lead_doc.territory or frappe.db.get_value("Territory", {"is_group": 0}, "name")
    customer.insert(ignore_permissions=True)
    return customer.name


def get_or_create_contact(lead_doc, customer):
    if not (lead_doc.email or lead_doc.mobile_no or lead_doc.phone):
        return None

    if lead_doc.email:
        existing = frappe.db.get_value("Contact Email", {"email_id": lead_doc.email, "parenttype": "Contact"}, "parent")
        if existing:
            return existing

    contact = frappe.new_doc("Contact")
    contact.first_name = lead_doc.first_name or lead_doc.lead_name
    contact.last_name = lead_doc.last_name
    contact.designation = lead_doc.designation
    if lead_doc.email:
        contact.append("email_ids", {"email_id": lead_doc.email, "is_primary": 1})
    if lead_doc.mobile_no:
        contact.append("phone_nos", {"phone": lead_doc.mobile_no, "is_primary_mobile_no": 1})
    if lead_doc.phone:
        contact.append("phone_nos", {"phone": lead_doc.phone, "is_primary_phone": 1})
    contact.append("links", {"link_doctype": "Customer", "link_name": customer})
    contact.insert(ignore_permissions=True)
    return contact.name


def create_opportunity(lead_doc, customer, opportunity_name, pipeline, stage, opportunity_owner, expected_value, expected_close_date, territory):
    pipeline = pipeline or get_default_pipeline()
    first_stage = get_first_stage(pipeline) if pipeline else None
    opportunity = frappe.new_doc("CRM Opportunity")
    opportunity.opportunity_name = opportunity_name or f"{lead_doc.organization_name or lead_doc.lead_name} Opportunity"
    opportunity.customer = customer
    opportunity.lead = lead_doc.name
    opportunity.pipeline = pipeline
    opportunity.stage = stage or (first_stage.stage_name if first_stage else None)
    opportunity.opportunity_owner = opportunity_owner or lead_doc.lead_owner or frappe.session.user
    opportunity.territory = territory or lead_doc.territory
    opportunity.currency = lead_doc.currency
    opportunity.opportunity_value = expected_value or lead_doc.estimated_value
    opportunity.expected_close_date = expected_close_date or lead_doc.expected_purchase_date
    opportunity.source = lead_doc.lead_source
    opportunity.next_action = lead_doc.next_action
    opportunity.next_action_date = lead_doc.next_action_date
    opportunity.insert(ignore_permissions=True)
    return opportunity
