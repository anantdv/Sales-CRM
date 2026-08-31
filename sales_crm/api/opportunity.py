import frappe
from frappe import _
from frappe.utils import flt, now, today

from sales_crm.services.deal_health import get_deal_room

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


@frappe.whitelist()
def get_deal_room_data(opportunity):
    return get_deal_room(opportunity)


@frappe.whitelist()
def ensure_stage_checklist(opportunity):
    opp = frappe.get_doc("CRM Opportunity", opportunity)
    templates = frappe.get_all(
        "CRM Stage Checklist",
        filters={"pipeline": opp.pipeline, "stage": opp.stage, "active": 1},
        fields=["checklist_item", "mandatory", "sequence"],
        order_by="sequence asc",
    )
    created = []
    for row in templates:
        if frappe.db.exists("CRM Opportunity Checklist", {"opportunity": opp.name, "stage": opp.stage, "checklist_item": row.checklist_item}):
            continue
        doc = frappe.new_doc("CRM Opportunity Checklist")
        doc.opportunity = opp.name
        doc.pipeline = opp.pipeline
        doc.stage = opp.stage
        doc.checklist_item = row.checklist_item
        doc.mandatory = row.mandatory
        doc.insert(ignore_permissions=False)
        created.append(doc.name)
    return created


@frappe.whitelist()
def mark_won(opportunity, actual_close_date=None, final_value=None, notes=None):
    opp = frappe.get_doc("CRM Opportunity", opportunity)
    closed_stage = get_closed_stage(opp.pipeline, "Won")
    if not closed_stage:
        frappe.throw(_("No Won stage is configured for this pipeline."))
    if not opp.customer:
        frappe.throw(_("Customer is required before marking won."))
    if not flt(final_value or opp.opportunity_value):
        frappe.throw(_("Opportunity value must be greater than zero before marking won."))
    if not opp.primary_contact:
        frappe.throw(_("Primary Contact is required before marking won."))
    assert_mandatory_checklist_complete(opp)

    opp.stage = closed_stage
    opp.status = "Won"
    opp.probability = 100
    opp.opportunity_value = final_value or opp.opportunity_value
    opp.won_date = actual_close_date or today()
    opp.closure_notes = notes or opp.closure_notes
    opp.save(ignore_permissions=False)
    return opp.name


@frappe.whitelist()
def mark_lost(opportunity, lost_reason, closure_notes, competitor=None, competitor_price=None, lessons_learned=None):
    opp = frappe.get_doc("CRM Opportunity", opportunity)
    closed_stage = get_closed_stage(opp.pipeline, "Lost")
    if not closed_stage:
        frappe.throw(_("No Lost stage is configured for this pipeline."))
    if not lost_reason or not closure_notes:
        frappe.throw(_("Lost Reason and Closure Notes are required."))

    opp.stage = closed_stage
    opp.status = "Lost"
    opp.probability = 0
    opp.lost_date = today()
    opp.lost_reason = lost_reason
    opp.closure_notes = closure_notes
    opp.competitor = competitor
    opp.competitor_price = competitor_price
    opp.lessons_learned = lessons_learned
    opp.save(ignore_permissions=False)
    return opp.name


@frappe.whitelist()
def reopen_opportunity(opportunity, reopen_reason, stage=None):
    if "CRM Sales Manager" not in frappe.get_roles() and "CRM Administrator" not in frappe.get_roles() and "System Manager" not in frappe.get_roles():
        frappe.throw(_("Only CRM Sales Manager or CRM Administrator can reopen opportunities."))
    if not reopen_reason:
        frappe.throw(_("Reopen Reason is required."))

    opp = frappe.get_doc("CRM Opportunity", opportunity)
    opp.status = "Open"
    opp.stage = stage or get_first_open_stage(opp.pipeline)
    opp.reopen_reason = reopen_reason
    opp.probability = None
    opp.save(ignore_permissions=False)
    return opp.name


def get_closed_stage(pipeline, stage_type):
    pipeline_doc = frappe.get_cached_doc("CRM Pipeline", pipeline)
    for row in pipeline_doc.get("stages") or []:
        if row.stage_type == stage_type:
            return row.stage_name
    return None


def get_first_open_stage(pipeline):
    pipeline_doc = frappe.get_cached_doc("CRM Pipeline", pipeline)
    stages = sorted([row for row in pipeline_doc.get("stages") or [] if row.stage_type == "Open"], key=lambda row: row.sequence or 0)
    return stages[0].stage_name if stages else None


def assert_mandatory_checklist_complete(opp):
    mandatory = frappe.get_all(
        "CRM Stage Checklist",
        filters={"pipeline": opp.pipeline, "stage": opp.stage, "mandatory": 1, "active": 1},
        pluck="checklist_item",
    )
    if not mandatory:
        return
    completed = set(
        frappe.get_all(
            "CRM Opportunity Checklist",
            filters={"opportunity": opp.name, "stage": opp.stage, "completed": 1},
            pluck="checklist_item",
        )
    )
    missing = [item for item in mandatory if item not in completed]
    if missing:
        frappe.throw(_("Complete mandatory checklist items before marking won: {0}").format(", ".join(missing)))
