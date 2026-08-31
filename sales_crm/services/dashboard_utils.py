from datetime import timedelta

import frappe
from frappe.utils import add_months, get_first_day, get_quarter_start, get_year_start, getdate, today


MANAGEMENT_ROLES = {"CRM Sales Manager", "CRM Administrator", "CRM Sales Executive", "Sales Manager", "System Manager"}


def assert_management_access():
    if not (set(frappe.get_roles()) & MANAGEMENT_ROLES):
        frappe.throw("You do not have access to the Sales Management Command Center.", frappe.PermissionError)


def normalize_filters(filters=None):
    filters = frappe._dict(filters or {})
    filters.from_date = getdate(filters.from_date or get_quarter_start(today()))
    filters.to_date = getdate(filters.to_date or today())
    return filters


def crm_where(filters, alias="o"):
    clauses = ["1=1"]
    params = {}
    mapping = {
        "company": "company",
        "pipeline": "pipeline",
        "salesperson": "opportunity_owner",
        "territory": "territory",
        "opportunity_type": "opportunity_type",
    }
    for key, column in mapping.items():
        if filters.get(key):
            param = key
            clauses.append(f"{alias}.{column}=%({param})s")
            params[param] = filters.get(key)
    return " and ".join(clauses), params


def invoice_where(filters, alias="si"):
    clauses = [f"{alias}.docstatus=1", f"{alias}.posting_date between %(from_date)s and %(to_date)s"]
    params = {"from_date": filters.from_date, "to_date": filters.to_date}
    if filters.get("company"):
        clauses.append(f"{alias}.company=%(company)s")
        params["company"] = filters.company
    if filters.get("territory"):
        clauses.append(f"{alias}.territory=%(territory)s")
        params["territory"] = filters.territory
    return " and ".join(clauses), params


def money(value):
    return value or 0


def percent(numerator, denominator):
    return (float(numerator or 0) / float(denominator or 1)) * 100


def period_bounds(period="quarter"):
    if period == "month":
        start = get_first_day(today())
    elif period == "year":
        start = get_year_start(today())
    else:
        start = get_quarter_start(today())
    return getdate(start), getdate(today())


def previous_period(from_date, to_date):
    days = (getdate(to_date) - getdate(from_date)).days + 1
    prev_to = getdate(from_date) - timedelta(days=1)
    prev_from = prev_to - timedelta(days=days - 1)
    return prev_from, prev_to
