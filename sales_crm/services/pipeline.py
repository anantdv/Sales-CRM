import frappe
from frappe import _


def validate_pipeline(doc, method=None):
    seen = set()
    has_won = False
    has_lost = False

    for row in doc.get("stages") or []:
        if row.sequence in seen:
            frappe.throw(_("Pipeline stage sequence {0} is duplicated.").format(row.sequence))
        seen.add(row.sequence)

        if row.probability is not None and not 0 <= row.probability <= 100:
            frappe.throw(_("Probability must be between 0 and 100 for stage {0}.").format(row.stage_name))

        if row.stage_type == "Won":
            has_won = True
            if row.probability != 100:
                frappe.throw(_("Won stage {0} must have probability 100.").format(row.stage_name))

        if row.stage_type == "Lost":
            has_lost = True
            if row.probability != 0:
                frappe.throw(_("Lost stage {0} must have probability 0.").format(row.stage_name))

    if not (has_won and has_lost):
        frappe.throw(_("Pipeline must include at least one Won stage and one Lost stage."))

    if doc.default_pipeline:
        filters = {"default_pipeline": 1}
        if doc.company:
            filters["company"] = doc.company
        else:
            filters["company"] = ["is", "not set"]
        existing = frappe.db.exists("CRM Pipeline", {**filters, "name": ["!=", doc.name]})
        if existing:
            frappe.throw(_("Only one default CRM Pipeline is allowed per company."))


def get_stage(pipeline, stage_name):
    if not pipeline or not stage_name:
        return None

    pipeline_doc = frappe.get_cached_doc("CRM Pipeline", pipeline)
    for row in pipeline_doc.get("stages") or []:
        if row.stage_name == stage_name or row.stage_code == stage_name:
            return row
    return None


def get_first_stage(pipeline):
    pipeline_doc = frappe.get_cached_doc("CRM Pipeline", pipeline)
    stages = sorted([row for row in pipeline_doc.get("stages") or [] if row.active], key=lambda row: row.sequence or 0)
    return stages[0] if stages else None


def get_default_pipeline(company=None):
    filters = {"default_pipeline": 1, "active": 1}
    if company:
        filters["company"] = company
    name = frappe.db.get_value("CRM Pipeline", filters, "name")
    if not name:
        name = frappe.db.get_value("CRM Pipeline", {"default_pipeline": 1, "active": 1}, "name")
    return name
