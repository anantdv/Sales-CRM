import frappe


def create_workspace():
    sales_workspace_page = create_sales_workspace_page()
    management_command_center_page = create_management_command_center_page()
    name = "Sales CRM"
    workspace = frappe.get_doc("Workspace", name) if frappe.db.exists("Workspace", name) else frappe.new_doc("Workspace")
    workspace.title = name
    workspace.module = "Sales CRM"
    workspace.public = 1
    workspace.is_hidden = 0
    workspace.label = name
    workspace.icon = "crm"

    workspace.set("links", [])
    for label, link_type, link_to in workspace_links(sales_workspace_page, management_command_center_page):
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


def workspace_links(sales_workspace_page, management_command_center_page):
    return [
        ("Sales Workspace", "Page", sales_workspace_page),
        ("Sales Management Command Center", "Page", management_command_center_page),
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
    return create_page("sales-crm-workspace", "Sales Workspace")


def create_management_command_center_page():
    return create_page("sales-management-command-center", "Sales Management Command Center")


def create_page(page_name, title):
    existing = frappe.db.exists("Page", page_name)
    if existing:
        return existing

    existing = frappe.db.get_value("Page", {"page_name": page_name}, "name")
    if existing:
        return existing

    page = frappe.new_doc("Page")
    page.page_name = page_name
    page.title = title
    page.module = "Sales CRM"
    page.standard = "Yes"
    page.insert(ignore_permissions=True)
    return page.name
