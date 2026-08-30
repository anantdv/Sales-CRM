import frappe
from frappe.utils import today


def create_daily_pipeline_snapshots():
    if not frappe.db.get_single_value("CRM Settings", "enable_pipeline_snapshots"):
        return

    rows = frappe.get_all(
        "CRM Opportunity",
        filters={"status": ["in", ["Open", "Won", "Lost", "On Hold"]]},
        fields=["name", "company", "pipeline", "opportunity_owner", "stage", "probability", "opportunity_value", "weighted_value", "expected_close_date", "deal_health_status", "status"],
        limit_page_length=1000,
    )
    for row in rows:
        if frappe.db.exists("CRM Pipeline Snapshot", {"snapshot_date": today(), "opportunity": row.name, "pipeline": row.pipeline}):
            continue
        doc = frappe.new_doc("CRM Pipeline Snapshot")
        doc.snapshot_date = today()
        doc.company = row.company
        doc.pipeline = row.pipeline
        doc.opportunity = row.name
        doc.owner = row.opportunity_owner
        doc.stage = row.stage
        doc.probability = row.probability
        doc.value = row.opportunity_value
        doc.weighted_value = row.weighted_value
        doc.expected_close_date = row.expected_close_date
        doc.deal_health = row.deal_health_status
        doc.status = row.status
        doc.insert(ignore_permissions=True)
