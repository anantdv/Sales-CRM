import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from sales_crm.setup.doctypes import create_doctypes
from sales_crm.setup.seed import create_default_pipeline, create_default_qualification_template
from sales_crm.setup.seed import create_default_playbooks, create_stage_checklists
from sales_crm.setup.workspace import create_workspace


def after_install():
    create_roles()
    create_doctypes()
    create_custom_erp_fields()
    create_default_settings()
    create_default_pipeline()
    create_default_qualification_template()
    create_stage_checklists()
    create_default_playbooks()
    create_workspace()


def create_roles():
    for role in ("CRM Sales User", "CRM Sales Manager", "CRM Administrator"):
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)


def create_default_settings():
    settings = frappe.get_single("CRM Settings")
    settings.default_lead_status = settings.default_lead_status or "New"
    settings.stale_opportunity_days = settings.stale_opportunity_days or 30
    settings.default_activity_duration = settings.default_activity_duration or 30
    settings.stale_lead_days = settings.stale_lead_days or 14
    settings.stage_age_warning_percent = settings.stage_age_warning_percent or 80
    settings.quote_expiry_warning_days = settings.quote_expiry_warning_days or 7
    settings.expected_close_warning_days = settings.expected_close_warning_days or 7
    settings.high_value_opportunity_threshold = settings.high_value_opportunity_threshold or 250000
    settings.require_next_action_on_open_opportunity = 1
    settings.enable_next_best_action = 1
    settings.enable_deal_health = 1
    settings.enable_sales_playbooks = 1
    settings.activity_reminder_days = settings.activity_reminder_days or 1
    settings.engagement_active_days = settings.engagement_active_days or 7
    settings.engagement_moderate_days = settings.engagement_moderate_days or 30
    settings.engagement_low_days = settings.engagement_low_days or 60
    settings.enable_relationship_tracking = 1
    settings.enable_stage_history = 1
    settings.default_probability_from_stage = 1
    settings.require_expected_close_date = 1
    settings.require_next_action = 1
    settings.save(ignore_permissions=True)


def create_custom_erp_fields():
    fields = {
        "Quotation": [
            {
                "fieldname": "custom_crm_opportunity",
                "label": "CRM Opportunity",
                "fieldtype": "Link",
                "options": "CRM Opportunity",
                "insert_after": "opportunity",
                "module": "Sales CRM",
            },
            {
                "fieldname": "custom_crm_lead",
                "label": "CRM Lead",
                "fieldtype": "Link",
                "options": "CRM Lead",
                "insert_after": "custom_crm_opportunity",
                "module": "Sales CRM",
            },
        ],
        "Sales Order": [
            {
                "fieldname": "custom_crm_opportunity",
                "label": "CRM Opportunity",
                "fieldtype": "Link",
                "options": "CRM Opportunity",
                "insert_after": "po_no",
                "module": "Sales CRM",
            }
        ],
    }
    create_custom_fields(fields, ignore_validate=True)
