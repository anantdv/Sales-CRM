import frappe
from frappe import _


@frappe.whitelist()
def create_quotation(opportunity):
    opp = frappe.get_doc("CRM Opportunity", opportunity)
    if not opp.customer:
        frappe.throw(_("Customer is required to create a Quotation."))

    quotation = frappe.new_doc("Quotation")
    quotation.quotation_to = "Customer"
    quotation.party_name = opp.customer
    quotation.currency = opp.currency
    quotation.custom_crm_opportunity = opp.name
    quotation.custom_crm_lead = opp.lead

    for row in opp.get("products") or []:
        if not row.item_code:
            continue
        quotation.append(
            "items",
            {
                "item_code": row.item_code,
                "item_name": row.item_name,
                "description": row.description,
                "qty": row.qty,
                "uom": row.uom,
                "rate": row.rate,
            },
        )

    if not quotation.get("items"):
        frappe.throw(_("Add at least one Item-backed opportunity product before creating a Quotation."))

    quotation.insert(ignore_permissions=True)
    frappe.db.set_value("CRM Opportunity", opp.name, "quotation", quotation.name, update_modified=False)
    return quotation.name


@frappe.whitelist()
def get_activity_timeline(opportunity):
    return frappe.get_all(
        "Sales Activity",
        filters={"crm_opportunity": opportunity},
        fields=["name", "activity_date", "activity_type", "subject", "contact", "assigned_to", "outcome", "next_action"],
        order_by="activity_date desc, modified desc",
        limit_page_length=50,
    )
