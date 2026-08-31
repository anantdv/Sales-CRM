from datetime import date

import frappe
from frappe import _
from frappe.utils import cint, date_diff, flt, getdate, now, today

from sales_crm.services.pipeline import get_first_stage, get_stage


def before_validate(doc, method=None):
    if not doc.pipeline:
        default_pipeline = frappe.db.get_single_value("CRM Settings", "default_pipeline")
        if default_pipeline:
            doc.pipeline = default_pipeline

    if doc.pipeline and not doc.stage:
        first_stage = get_first_stage(doc.pipeline)
        if first_stage:
            doc.stage = first_stage.stage_name

    apply_stage_defaults(doc)
    calculate_values(doc)
    calculate_age_fields(doc)
    set_status_dates(doc)
    from sales_crm.services.deal_health import apply_deal_health

    apply_deal_health(doc)


def validate_opportunity(doc, method=None):
    stage = get_stage(doc.pipeline, doc.stage)
    if not stage:
        frappe.throw(_("Stage {0} is not defined in pipeline {1}.").format(doc.stage, doc.pipeline))

    validate_stage_requirements(doc, stage)
    validate_closed_status(doc, stage)


def before_save(doc, method=None):
    previous = doc.get_doc_before_save()
    if not previous and not doc.current_stage_entered_on:
        doc.current_stage_entered_on = now()

    if previous and previous.stage != doc.stage:
        validate_stage_change(doc, previous)
        doc.previous_stage = previous.stage
        doc.current_stage_entered_on = now()
        doc.number_of_stage_changes = cint(doc.number_of_stage_changes) + 1

    calculate_values(doc)
    calculate_age_fields(doc)


def on_update(doc, method=None):
    previous = doc.get_doc_before_save()
    if previous and previous.stage != doc.stage and frappe.db.get_single_value("CRM Settings", "enable_stage_history"):
        create_stage_history(doc, previous)


def validate_opportunity_product(doc, method=None):
    doc.amount = flt(doc.qty) * flt(doc.rate)
    probability = flt(doc.probability)
    doc.weighted_amount = doc.amount * probability / 100


def apply_stage_defaults(doc):
    if not doc.pipeline or not doc.stage:
        return

    stage = get_stage(doc.pipeline, doc.stage)
    if not stage:
        return

    settings = frappe.get_single("CRM Settings")
    if settings.default_probability_from_stage and not settings.allow_manual_probability:
        doc.probability = stage.probability

    if stage.stage_type == "Won":
        doc.status = "Won"
    elif stage.stage_type == "Lost":
        doc.status = "Lost"
    elif doc.status not in ("On Hold",):
        doc.status = "Open"


def calculate_values(doc):
    doc.weighted_value = flt(doc.opportunity_value) * flt(doc.probability) / 100
    for row in doc.get("products") or []:
        row.amount = flt(row.qty) * flt(row.rate)
        row_probability = row.probability if row.probability is not None else doc.probability
        row.weighted_amount = flt(row.amount) * flt(row_probability) / 100


def calculate_age_fields(doc):
    created_on = getdate(doc.creation) if doc.creation else getdate(today())
    doc.opportunity_age_days = date_diff(today(), created_on)
    if doc.current_stage_entered_on:
        doc.days_in_stage = date_diff(today(), getdate(doc.current_stage_entered_on))

    stale_days = cint(frappe.db.get_single_value("CRM Settings", "stale_opportunity_days") or 30)
    doc.stale = 1 if doc.days_in_stage and doc.days_in_stage > stale_days else 0


def set_status_dates(doc):
    if doc.status == "Won" and not doc.won_date:
        doc.won_date = today()
    if doc.status == "Lost" and not doc.lost_date:
        doc.lost_date = today()


def validate_stage_requirements(doc, stage):
    settings = frappe.get_single("CRM Settings")

    if (stage.require_expected_close_date or settings.require_expected_close_date) and not doc.expected_close_date:
        frappe.throw(_("Expected Close Date is required for stage {0}.").format(stage.stage_name))

    if (stage.require_next_action or settings.require_next_action) and stage.stage_type == "Open" and not doc.next_action:
        frappe.throw(_("Next Action is required for stage {0}.").format(stage.stage_name))

    if stage.require_qualification and settings.require_qualification_before_stage_change:
        threshold = flt(settings.qualification_threshold or 70)
        if flt(doc.qualification_score) < threshold:
            frappe.throw(_("Qualification score must be at least {0}% before entering {1}.").format(threshold, stage.stage_name))

    if stage.allow_quotation and not doc.customer:
        frappe.throw(_("Customer is required before quotation is allowed."))

    if not doc.is_new() and stage.stage_type == "Open":
        validate_mandatory_stage_checklist(doc)


def validate_closed_status(doc, stage):
    if stage.stage_type == "Won":
        for fieldname in ("customer", "opportunity_value"):
            if not doc.get(fieldname):
                frappe.throw(_("{0} is required before closing as won.").format(frappe.unscrub(fieldname)))

    if stage.stage_type == "Lost":
        if not doc.lost_reason or not doc.closure_notes:
            frappe.throw(_("Lost Reason and Closure Notes are required before closing as lost."))


def validate_stage_change(doc, previous):
    if not frappe.db.get_value("CRM Pipeline", doc.pipeline, "allow_stage_skipping"):
        old_stage = get_stage(previous.pipeline, previous.stage)
        new_stage = get_stage(doc.pipeline, doc.stage)
        if old_stage and new_stage and new_stage.sequence > old_stage.sequence + 1:
            frappe.throw(_("Stage skipping is disabled for this pipeline."))


def validate_mandatory_stage_checklist(doc):
    mandatory = frappe.get_all(
        "CRM Stage Checklist",
        filters={"pipeline": doc.pipeline, "stage": doc.stage, "mandatory": 1, "active": 1},
        pluck="checklist_item",
    )
    if not mandatory:
        return
    completed = set(
        frappe.get_all(
            "CRM Opportunity Checklist",
            filters={"opportunity": doc.name, "stage": doc.stage, "completed": 1},
            pluck="checklist_item",
        )
    )
    missing = [item for item in mandatory if item not in completed]
    if missing and doc.stage in ("Proposal", "Negotiation", "Commit"):
        frappe.throw(_("Complete mandatory stage checklist items before advancing: {0}").format(", ".join(missing)))


def create_stage_history(doc, previous):
    days = 0
    if previous.current_stage_entered_on:
        days = date_diff(today(), getdate(previous.current_stage_entered_on))

    history = frappe.get_doc(
        {
            "doctype": "CRM Opportunity Stage History",
            "opportunity": doc.name,
            "pipeline": doc.pipeline,
            "from_stage": previous.stage,
            "to_stage": doc.stage,
            "changed_on": now(),
            "changed_by": frappe.session.user,
            "previous_probability": previous.probability,
            "new_probability": doc.probability,
            "opportunity_value": doc.opportunity_value,
            "days_in_previous_stage": days,
        }
    )
    history.insert(ignore_permissions=True)
