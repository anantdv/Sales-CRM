import frappe
from frappe.utils import flt


SCORE_BY_STATUS = {
    "Confirmed": 100,
    "Partial": 50,
    "Unknown": 0,
    "Not Applicable": 0,
}


def validate_qualification_row(doc, method=None):
    doc.score = SCORE_BY_STATUS.get(doc.status, 0)


def update_opportunity_score(doc, method=None):
    if not doc.opportunity:
        return
    rows = frappe.get_all(
        "CRM Opportunity Qualification",
        filters={"opportunity": doc.opportunity},
        fields=["status", "score"],
    )
    applicable = [row for row in rows if row.status != "Not Applicable"]
    if not applicable:
        score = 0
    else:
        score = sum(flt(row.score) for row in applicable) / len(applicable)
    frappe.db.set_value("CRM Opportunity", doc.opportunity, "qualification_score", score, update_modified=False)
