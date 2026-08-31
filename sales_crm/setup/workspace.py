import frappe


def create_workspace():
    create_sales_workspace_page()
    create_management_command_center_page()
    name = "Sales CRM"
    workspace = frappe.get_doc("Workspace", name) if frappe.db.exists("Workspace", name) else frappe.new_doc("Workspace")
    workspace.title = name
    workspace.module = "Sales CRM"
    workspace.public = 1
    workspace.is_hidden = 0
    workspace.label = name
    workspace.icon = "crm"

    workspace.set("links", [])
    for label, link_type, link_to in workspace_links():
        workspace.append(
            "links",
            {
                "label": label,
                "type": link_type,
                "link_to": link_to,
                "hidden": 0,
                "onboard": 0,
            },
        )

    workspace.save(ignore_permissions=True)


def workspace_links():
    return [
        ("Sales Workspace", "Page", "sales-crm-workspace"),
        ("Sales Management Command Center", "Page", "sales-management-command-center"),
        ("My Leads", "DocType", "CRM Lead"),
        ("My Opportunities", "DocType", "CRM Opportunity"),
        ("My Activities", "DocType", "Sales Activity"),
        ("CRM Leads", "DocType", "CRM Lead"),
        ("Sales Activities", "DocType", "Sales Activity"),
        ("CRM Account Profiles", "DocType", "CRM Account Profile"),
        ("Contacts", "DocType", "Contact"),
        ("Customers", "DocType", "Customer"),
        ("CRM Opportunities", "DocType", "CRM Opportunity"),
        ("Quotations", "DocType", "Quotation"),
        ("Sales Orders", "DocType", "Sales Order"),
        ("CRM Pipelines", "DocType", "CRM Pipeline"),
        ("Qualification Templates", "DocType", "CRM Qualification Template"),
        ("CRM Settings", "DocType", "CRM Settings"),
    ]


def create_sales_workspace_page():
    if frappe.db.exists("Page", "sales-crm-workspace"):
        return
    page = frappe.new_doc("Page")
    page.name = "sales-crm-workspace"
    page.page_name = "sales-crm-workspace"
    page.title = "Sales Workspace"
    page.module = "Sales CRM"
    page.standard = "Yes"
    page.insert(ignore_permissions=True)


def create_management_command_center_page():
    if frappe.db.exists("Page", "sales-management-command-center"):
        return
    page = frappe.new_doc("Page")
    page.name = "sales-management-command-center"
    page.page_name = "sales-management-command-center"
    page.title = "Sales Management Command Center"
    page.module = "Sales CRM"
    page.standard = "Yes"
    page.insert(ignore_permissions=True)
