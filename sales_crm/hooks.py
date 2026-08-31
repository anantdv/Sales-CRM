app_name = "sales_crm"
app_title = "Sales CRM"
app_publisher = "BLC"
app_description = "Enterprise CRM layer for Frappe/ERPNext"
app_email = "admin@example.com"
app_license = "MIT"

after_install = "sales_crm.install.after_install"
after_migrate = "sales_crm.install.after_migrate"

app_include_js = []
app_include_css = []
web_include_js = []
web_include_css = []

fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "Sales CRM"]]},
]

doc_events = {
    "CRM Pipeline": {
        "validate": "sales_crm.services.pipeline.validate_pipeline",
    },
    "CRM Opportunity": {
        "before_validate": "sales_crm.services.opportunity.before_validate",
        "validate": "sales_crm.services.opportunity.validate_opportunity",
        "before_save": "sales_crm.services.opportunity.before_save",
        "on_update": "sales_crm.services.opportunity.on_update",
    },
    "CRM Opportunity Product": {
        "validate": "sales_crm.services.opportunity.validate_opportunity_product",
    },
    "CRM Opportunity Qualification": {
        "validate": "sales_crm.services.qualification.validate_qualification_row",
        "on_update": "sales_crm.services.qualification.update_opportunity_score",
        "on_trash": "sales_crm.services.qualification.update_opportunity_score",
    },
    "CRM Lead": {
        "validate": "sales_crm.services.lead.validate_lead",
    },
    "Sales Activity": {
        "validate": "sales_crm.services.activity.validate_activity",
        "on_update": "sales_crm.services.activity.update_linked_records",
    },
    "Sales Task": {
        "validate": "sales_crm.services.task.validate_task",
        "on_update": "sales_crm.services.task.update_linked_records",
    },
    "Quotation": {
        "on_submit": "sales_crm.services.erp_links.update_opportunity_from_quotation",
        "on_update_after_submit": "sales_crm.services.erp_links.update_opportunity_from_quotation",
    },
    "Sales Order": {
        "on_submit": "sales_crm.services.erp_links.update_opportunity_from_sales_order",
        "on_update_after_submit": "sales_crm.services.erp_links.update_opportunity_from_sales_order",
    },
}

scheduled_events = {
    "daily": [
        "sales_crm.services.deal_health.update_stale_opportunities",
        "sales_crm.services.pipeline_snapshot.create_daily_pipeline_snapshots",
    ]
}

doctype_js = {
    "CRM Lead": "public/js/crm_lead.js",
    "CRM Opportunity": "public/js/crm_opportunity.js",
    "CRM Account Profile": "public/js/crm_account_profile.js",
}
