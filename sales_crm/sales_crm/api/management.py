import json

import frappe

from sales_crm.services.management_dashboard import get_management_dashboard


@frappe.whitelist()
def get_dashboard(filters=None):
    if isinstance(filters, str):
        filters = json.loads(filters) if filters else {}
    return get_management_dashboard(filters)
