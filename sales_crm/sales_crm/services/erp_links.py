import frappe


def update_opportunity_from_quotation(doc, method=None):
    opportunity = getattr(doc, "custom_crm_opportunity", None)
    if opportunity and frappe.db.exists("CRM Opportunity", opportunity):
        frappe.db.set_value("CRM Opportunity", opportunity, "quotation", doc.name, update_modified=False)


def update_opportunity_from_sales_order(doc, method=None):
    opportunity = getattr(doc, "custom_crm_opportunity", None)
    if not opportunity and getattr(doc, "items", None):
        quotation = next((row.prevdoc_docname for row in doc.items if getattr(row, "prevdoc_docname", None)), None)
        if quotation:
            opportunity = frappe.db.get_value("Quotation", quotation, "custom_crm_opportunity")
    if opportunity and frappe.db.exists("CRM Opportunity", opportunity):
        frappe.db.set_value("CRM Opportunity", opportunity, "sales_order", doc.name, update_modified=False)
