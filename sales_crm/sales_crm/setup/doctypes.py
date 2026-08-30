import frappe


ROLE_PERMS = [
    {"role": "CRM Sales User", "read": 1, "write": 1, "create": 1, "delete": 0},
    {"role": "CRM Sales Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
    {"role": "CRM Administrator", "read": 1, "write": 1, "create": 1, "delete": 1},
    {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
]


def create_doctypes():
    ensure_module()
    for spec in _doctype_specs():
        ensure_doctype(spec)
    frappe.clear_cache()


def ensure_module():
    if not frappe.db.exists("Module Def", "Sales CRM"):
        frappe.get_doc({"doctype": "Module Def", "module_name": "Sales CRM", "app_name": "sales_crm"}).insert(
            ignore_permissions=True
        )


def ensure_doctype(spec):
    if frappe.db.exists("DocType", spec["name"]):
        ensure_missing_fields(spec)
        return

    doc = frappe.new_doc("DocType")
    doc.name = spec["name"]
    doc.module = "Sales CRM"
    doc.custom = 1
    doc.istable = spec.get("istable", 0)
    doc.issingle = spec.get("issingle", 0)
    doc.is_submittable = spec.get("is_submittable", 0)
    doc.track_changes = spec.get("track_changes", 1)
    doc.allow_rename = spec.get("allow_rename", 1)
    doc.naming_rule = spec.get("naming_rule", "By fieldname")
    doc.autoname = spec.get("autoname")
    doc.title_field = spec.get("title_field")
    doc.search_fields = spec.get("search_fields")

    for field in spec["fields"]:
        doc.append("fields", field)

    if spec.get("istable"):
        doc.editable_grid = 1
    else:
        for perm in ROLE_PERMS:
            doc.append("permissions", perm)

    doc.insert(ignore_permissions=True)


def ensure_missing_fields(spec):
    existing = {row.fieldname for row in frappe.get_meta(spec["name"]).fields if row.fieldname}
    doc = frappe.get_doc("DocType", spec["name"])
    changed = False
    for field_spec in spec["fields"]:
        fieldname = field_spec.get("fieldname")
        if fieldname and fieldname not in existing:
            doc.append("fields", field_spec)
            existing.add(fieldname)
            changed = True
    if changed:
        doc.save(ignore_permissions=True)


def sec(label):
    return {"fieldtype": "Section Break", "label": label}


def col():
    return {"fieldtype": "Column Break"}


def field(fieldname, label, fieldtype="Data", **kwargs):
    out = {"fieldname": fieldname, "label": label, "fieldtype": fieldtype}
    out.update(kwargs)
    return out


def options(*values):
    return "\n".join(values)


def _doctype_specs():
    return [
        {
            "name": "CRM Settings",
            "issingle": 1,
            "naming_rule": "",
            "autoname": "",
            "allow_rename": 0,
            "fields": [
                sec("General"),
                field("default_pipeline", "Default Pipeline", "Link", options="CRM Pipeline"),
                field("default_lead_owner", "Default Lead Owner", "Link", options="User"),
                field("auto_create_account_on_conversion", "Auto Create Account on Conversion", "Check"),
                field("require_qualification_before_stage_change", "Require Qualification Before Stage Change", "Check"),
                field("qualification_threshold", "Qualification Threshold", "Percent", default=70),
                field("stale_opportunity_days", "Stale Opportunity Days", "Int", default=30),
                field("enable_relationship_tracking", "Enable Relationship Tracking", "Check", default=1),
                field("enable_stage_history", "Enable Stage History", "Check", default=1),
                sec("Lead Management"),
                field("default_lead_status", "Default Lead Status", "Select", options=lead_statuses(), default="New"),
                field("auto_assign_leads", "Auto Assign Leads", "Check"),
                field("lead_duplicate_check", "Lead Duplicate Check", "Check", default=1),
                field("duplicate_check_email", "Duplicate Check Email", "Check", default=1),
                field("duplicate_check_mobile", "Duplicate Check Mobile", "Check", default=1),
                field("duplicate_check_company", "Duplicate Check Company", "Check", default=1),
                sec("Opportunity"),
                field("default_probability_from_stage", "Default Probability From Stage", "Check", default=1),
                field("allow_manual_probability", "Allow Manual Probability", "Check"),
                field("require_expected_close_date", "Require Expected Close Date", "Check", default=1),
                field("require_next_action", "Require Next Action", "Check", default=1),
                sec("Activity"),
                field("default_activity_duration", "Default Activity Duration", "Int", default=30),
                field("auto_create_follow_up_task", "Auto Create Follow-up Task", "Check"),
                sec("Sales Execution"),
                field("stale_lead_days", "Stale Lead Days", "Int", default=14),
                field("stage_age_warning_percent", "Stage Age Warning Percent", "Percent", default=80),
                field("quote_expiry_warning_days", "Quote Expiry Warning Days", "Int", default=7),
                field("expected_close_warning_days", "Expected Close Warning Days", "Int", default=7),
                field("high_value_opportunity_threshold", "High Value Opportunity Threshold", "Currency", default=250000),
                field("require_next_action_on_open_opportunity", "Require Next Action on Open Opportunity", "Check", default=1),
                field("enable_next_best_action", "Enable Next Best Action", "Check", default=1),
                field("enable_deal_health", "Enable Deal Health", "Check", default=1),
                field("enable_sales_playbooks", "Enable Sales Playbooks", "Check", default=1),
                field("activity_reminder_days", "Activity Reminder Days", "Int", default=1),
                field("engagement_active_days", "Engagement Active Days", "Int", default=7),
                field("engagement_moderate_days", "Engagement Moderate Days", "Int", default=30),
                field("engagement_low_days", "Engagement Low Days", "Int", default=60),
            ],
        },
        {
            "name": "CRM Pipeline Stage",
            "istable": 1,
            "fields": [
                field("stage_name", "Stage Name", reqd=1, in_list_view=1),
                field("stage_code", "Stage Code", in_list_view=1),
                field("sequence", "Sequence", "Int", reqd=1, in_list_view=1),
                field("probability", "Probability", "Percent", reqd=1, in_list_view=1),
                field("stage_type", "Stage Type", "Select", options=options("Open", "Won", "Lost"), default="Open"),
                field("maximum_age_days", "Maximum Age Days", "Int"),
                field("require_qualification", "Require Qualification", "Check"),
                field("require_next_action", "Require Next Action", "Check"),
                field("require_expected_close_date", "Require Expected Close Date", "Check"),
                field("allow_quotation", "Allow Quotation", "Check"),
                field("color", "Color", "Color"),
                field("active", "Active", "Check", default=1),
                field("guidance_title", "Guidance Title", "Data"),
                field("guidance_text", "Guidance Text", "Text"),
                field("recommended_activities", "Recommended Activities", "Small Text"),
            ],
        },
        {
            "name": "CRM Pipeline",
            "autoname": "CRM-PIPE-.####",
            "title_field": "pipeline_name",
            "search_fields": "pipeline_name,pipeline_code,company",
            "fields": [
                sec("Pipeline"),
                field("pipeline_name", "Pipeline Name", reqd=1, in_list_view=1),
                field("pipeline_code", "Pipeline Code", reqd=1, in_list_view=1),
                field("description", "Description", "Small Text"),
                col(),
                field("company", "Company", "Link", options="Company", in_list_view=1),
                field("active", "Active", "Check", default=1),
                field("default_pipeline", "Default Pipeline", "Check"),
                field(
                    "applicable_to",
                    "Applicable To",
                    "Select",
                    options=options(
                        "Enterprise Sales",
                        "B2B Sales",
                        "Government / Tender",
                        "Rental",
                        "Managed Services",
                        "Renewals",
                        "General",
                    ),
                    default="Enterprise Sales",
                ),
                field("currency", "Currency", "Link", options="Currency"),
                field("allow_stage_skipping", "Allow Stage Skipping", "Check"),
                sec("Stages"),
                field("stages", "Stages", "Table", options="CRM Pipeline Stage"),
            ],
        },
        {
            "name": "CRM Interested Product",
            "istable": 1,
            "fields": [field("item_code", "Item Code", "Link", options="Item", reqd=1, in_list_view=1)],
        },
        {
            "name": "CRM Lead",
            "autoname": "CRM-LEAD-.YYYY.-.#####",
            "title_field": "lead_name",
            "search_fields": "lead_name,organization_name,email,mobile_no",
            "fields": [
                sec("Identification"),
                field("lead_name", "Lead Name", reqd=1, in_list_view=1),
                field("organization_name", "Organization Name", in_list_view=1),
                field("designation", "Designation"),
                field("salutation", "Salutation", "Link", options="Salutation"),
                field("first_name", "First Name"),
                field("last_name", "Last Name"),
                col(),
                field("email", "Email", "Data", options="Email", in_list_view=1),
                field("mobile_no", "Mobile No", "Data", options="Phone"),
                field("phone", "Phone", "Data", options="Phone"),
                field("website", "Website", "Data", options="URL"),
                sec("Classification"),
                field("lead_status", "Lead Status", "Select", options=lead_statuses(), default="New", in_list_view=1),
                field("lead_source", "Lead Source", "Link", options="Lead Source", in_list_view=1),
                field("industry", "Industry", "Link", options="Industry Type"),
                field("market_segment", "Market Segment", "Link", options="Market Segment"),
                field("company_size", "Company Size", "Data"),
                col(),
                field("territory", "Territory", "Link", options="Territory"),
                field("country", "Country", "Link", options="Country"),
                sec("Ownership"),
                field("lead_owner", "Lead Owner", "Link", options="User", in_list_view=1),
                field("sales_team", "Sales Team", "Table", options="Sales Team"),
                field("assigned_date", "Assigned Date", "Datetime"),
                sec("Interest"),
                field("interested_products", "Interested Products", "Table MultiSelect", options="CRM Interested Product"),
                field("estimated_value", "Estimated Value", "Currency", in_list_view=1),
                field("currency", "Currency", "Link", options="Currency"),
                field("expected_purchase_date", "Expected Purchase Date", "Date"),
                sec("Qualification"),
                field("budget_status", "Budget Status", "Select", options=qualification_statuses()),
                field("authority_status", "Authority Status", "Select", options=qualification_statuses()),
                field("need_status", "Need Status", "Select", options=qualification_statuses()),
                field("timeline_status", "Timeline Status", "Select", options=qualification_statuses()),
                field("qualification_score", "Qualification Score", "Percent", read_only=1),
                sec("Engagement"),
                field("last_activity_date", "Last Activity Date", "Date", read_only=1),
                field("next_action", "Next Action", "Small Text"),
                field("next_action_date", "Next Action Date", "Date", in_list_view=1),
                field("number_of_activities", "Number of Activities", "Int", read_only=1),
                sec("Conversion"),
                field("converted", "Converted", "Check", read_only=1),
                field("converted_on", "Converted On", "Datetime", read_only=1),
                field("converted_customer", "Converted Customer", "Link", options="Customer", read_only=1),
                field("converted_contact", "Converted Contact", "Link", options="Contact", read_only=1),
                field("converted_opportunity", "Converted Opportunity", "Link", options="CRM Opportunity", read_only=1),
                sec("System"),
                field("duplicate_warning", "Duplicate Warning", "Small Text", read_only=1),
                field("lead_age_days", "Lead Age Days", "Int", read_only=1),
                field("created_by_source", "Created By Source", "Data"),
            ],
        },
        {
            "name": "CRM Account Profile",
            "autoname": "field:customer",
            "title_field": "customer",
            "search_fields": "customer,account_owner,territory",
            "fields": [
                sec("Account"),
                field("customer", "Customer", "Link", options="Customer", reqd=1, unique=1, in_list_view=1),
                field("account_tier", "Account Tier", "Select", options=options("Strategic", "Enterprise", "Major", "Growth", "Standard"), in_list_view=1),
                field("account_status", "Account Status", "Select", options=options("Prospect", "Active", "Dormant", "At Risk", "Inactive"), default="Prospect", in_list_view=1),
                field("industry", "Industry", "Link", options="Industry Type"),
                field("parent_account", "Parent Account", "Link", options="CRM Account Profile"),
                field("territory", "Territory", "Link", options="Territory"),
                field("account_owner", "Account Owner", "Link", options="User", in_list_view=1),
                field("sales_team", "Sales Team", "Table", options="Sales Team"),
                sec("Intelligence"),
                field("relationship_strength", "Relationship Strength", "Select", options=relationship_strengths()),
                field("account_health_score", "Account Health Score", "Percent"),
                field("strategic_account", "Strategic Account", "Check"),
                field("annual_revenue_estimate", "Annual Revenue Estimate", "Currency"),
                field("employee_count", "Employee Count", "Int"),
                field("website", "Website", "Data", options="URL"),
                field("notes", "Notes", "Text"),
                sec("Calculated"),
                field("open_opportunities", "Open Opportunities", "Int", read_only=1),
                field("pipeline_value", "Pipeline Value", "Currency", read_only=1),
                field("open_quotations", "Open Quotations", "Int", read_only=1),
                field("sales_ytd", "Sales YTD", "Currency", read_only=1),
                field("outstanding_receivable", "Outstanding Receivable", "Currency", read_only=1),
                field("last_sales_date", "Last Sales Date", "Date", read_only=1),
                field("last_activity_date", "Last Activity Date", "Date", read_only=1),
                field("activities_last_30_days", "Activities Last 30 Days", "Int", read_only=1),
                field("meetings_last_90_days", "Meetings Last 90 Days", "Int", read_only=1),
                field("open_follow_ups", "Open Follow-ups", "Int", read_only=1),
                field("active_opportunities", "Active Opportunities", "Int", read_only=1),
                field("stale_opportunities", "Stale Opportunities", "Int", read_only=1),
                field("engagement_status", "Engagement Status", "Select", options=options("Active", "Moderate", "Low", "Dormant"), read_only=1),
            ],
        },
        {
            "name": "CRM Contact Relationship",
            "autoname": "format:{customer}-{contact}",
            "title_field": "contact",
            "search_fields": "customer,contact,role",
            "fields": [
                sec("Relationship"),
                field("customer", "Customer", "Link", options="Customer", reqd=1, in_list_view=1),
                field("contact", "Contact", "Link", options="Contact", reqd=1, in_list_view=1),
                field("crm_account_profile", "CRM Account Profile", "Link", options="CRM Account Profile"),
                field("role", "Role", "Select", options=contact_roles(), in_list_view=1),
                field("decision_influence", "Decision Influence", "Select", options=options("High", "Medium", "Low"), in_list_view=1),
                field("relationship_strength", "Relationship Strength", "Select", options=relationship_strengths(), in_list_view=1),
                field("preferred_contact_method", "Preferred Contact Method", "Data"),
                field("last_contact_date", "Last Contact Date", "Date", in_list_view=1),
                field("notes", "Notes", "Text"),
                field("active", "Active", "Check", default=1),
            ],
        },
    ] + opportunity_specs() + qualification_specs() + playbook_specs() + activity_specs() + task_specs()


def opportunity_specs():
    return [
        {
            "name": "CRM Opportunity Product",
            "istable": 1,
            "fields": [
                field("item_code", "Item Code", "Link", options="Item", in_list_view=1),
                field("item_name", "Item Name", "Data", in_list_view=1),
                field("item_group", "Item Group", "Link", options="Item Group"),
                field("description", "Description", "Small Text"),
                field("qty", "Qty", "Float", default=1, in_list_view=1),
                field("uom", "UOM", "Link", options="UOM"),
                field("rate", "Rate", "Currency", in_list_view=1),
                field("amount", "Amount", "Currency", read_only=1, in_list_view=1),
                field("probability", "Probability", "Percent"),
                field("weighted_amount", "Weighted Amount", "Currency", read_only=1),
                field("expected_margin_percent", "Expected Margin Percent", "Percent"),
                field("notes", "Notes", "Small Text"),
            ],
        },
        {
            "name": "CRM Opportunity Contact",
            "istable": 1,
            "fields": [
                field("contact", "Contact", "Link", options="Contact", in_list_view=1),
                field("contact_name", "Contact Name", "Data", in_list_view=1),
                field("role", "Role", "Select", options=contact_roles(), in_list_view=1),
                field("influence", "Influence", "Select", options=options("High", "Medium", "Low")),
                field("relationship_strength", "Relationship Strength", "Select", options=relationship_strengths()),
                field("primary_contact", "Primary Contact", "Check"),
                field("notes", "Notes", "Small Text"),
            ],
        },
        {
            "name": "CRM Opportunity",
            "autoname": "CRM-OPP-.YYYY.-.#####",
            "title_field": "opportunity_name",
            "search_fields": "opportunity_name,customer,lead,stage",
            "fields": [
                sec("Identification"),
                field("opportunity_name", "Opportunity Name", reqd=1, in_list_view=1),
                field("opportunity_code", "Opportunity Code"),
                field("company", "Company", "Link", options="Company"),
                field("customer", "Customer", "Link", options="Customer", in_list_view=1),
                field("crm_account_profile", "CRM Account Profile", "Link", options="CRM Account Profile"),
                field("lead", "CRM Lead", "Link", options="CRM Lead"),
                field("primary_contact", "Primary Contact", "Link", options="Contact"),
                sec("Ownership"),
                field("opportunity_owner", "Opportunity Owner", "Link", options="User", in_list_view=1),
                field("sales_team", "Sales Team", "Table", options="Sales Team"),
                field("territory", "Territory", "Link", options="Territory"),
                sec("Pipeline"),
                field("pipeline", "Pipeline", "Link", options="CRM Pipeline", reqd=1, in_list_view=1),
                field("stage", "Stage", "Data", reqd=1, in_list_view=1),
                field("probability", "Probability", "Percent", in_list_view=1),
                field("status", "Status", "Select", options=options("Open", "Won", "Lost", "On Hold"), default="Open", in_list_view=1),
                sec("Value"),
                field("currency", "Currency", "Link", options="Currency"),
                field("opportunity_value", "Opportunity Value", "Currency", in_list_view=1),
                field("weighted_value", "Weighted Value", "Currency", read_only=1, in_list_view=1),
                field("expected_close_date", "Expected Close Date", "Date", in_list_view=1),
                sec("Business Context"),
                field("opportunity_type", "Opportunity Type", "Select", options=options("New Business", "Existing Customer", "Upsell", "Cross-sell", "Renewal", "Rental", "Managed Service", "Tender")),
                field("source", "Source", "Link", options="Lead Source"),
                field("business_need", "Business Need", "Text"),
                field("proposed_solution", "Proposed Solution", "Text"),
                field("key_requirements", "Key Requirements", "Text"),
                sec("Next Action"),
                field("next_action", "Next Action", "Small Text", in_list_view=1),
                field("next_action_date", "Next Action Date", "Date", in_list_view=1),
                sec("Deal Health"),
                field("days_in_stage", "Days in Stage", "Int", read_only=1, in_list_view=1),
                field("opportunity_age_days", "Opportunity Age Days", "Int", read_only=1),
                field("last_activity_date", "Last Activity Date", "Date", read_only=1),
                field("stale", "Stale", "Check", read_only=1),
                field("risk_level", "Risk Level", "Select", options=options("Low", "Medium", "High", "Critical"), in_list_view=1),
                field("deal_health_score", "Deal Health Score", "Percent", read_only=1),
                field("deal_health_status", "Deal Health Status", "Select", options=options("Healthy", "Watch", "At Risk", "Critical"), read_only=1),
                sec("Closure"),
                field("won_date", "Won Date", "Date", read_only=1),
                field("lost_date", "Lost Date", "Date", read_only=1),
                field("lost_reason", "Lost Reason", "Small Text"),
                field("competitor", "Competitor", "Data"),
                field("competitor_price", "Competitor Price", "Currency"),
                field("lessons_learned", "Lessons Learned", "Text"),
                field("reopen_reason", "Reopen Reason", "Small Text"),
                field("closure_notes", "Closure Notes", "Text"),
                sec("ERP Linkage"),
                field("quotation", "Quotation", "Link", options="Quotation"),
                field("sales_order", "Sales Order", "Link", options="Sales Order"),
                sec("Tracking"),
                field("current_stage_entered_on", "Current Stage Entered On", "Datetime", read_only=1),
                field("previous_stage", "Previous Stage", "Data", read_only=1),
                field("number_of_stage_changes", "Number of Stage Changes", "Int", read_only=1),
                field("qualification_score", "Qualification Score", "Percent", read_only=1),
                sec("Contacts"),
                field("contacts", "Contacts", "Table", options="CRM Opportunity Contact"),
                sec("Products"),
                field("products", "Products", "Table", options="CRM Opportunity Product"),
            ],
        },
    ]


def qualification_specs():
    return [
        {
            "name": "CRM Qualification Question",
            "istable": 1,
            "fields": [
                field("category", "Category", "Data", reqd=1, in_list_view=1),
                field("question", "Question", "Small Text", reqd=1, in_list_view=1),
                field("required", "Required", "Check", default=1),
                field("weight", "Weight", "Float", default=25),
                field("sequence", "Sequence", "Int", reqd=1, in_list_view=1),
            ],
        },
        {
            "name": "CRM Qualification Template",
            "autoname": "field:template_name",
            "title_field": "template_name",
            "fields": [
                field("template_name", "Template Name", reqd=1, unique=1),
                field("methodology", "Methodology", "Select", options=options("BANT", "Custom"), default="BANT"),
                field("active", "Active", "Check", default=1),
                field("questions", "Questions", "Table", options="CRM Qualification Question"),
            ],
        },
        {
            "name": "CRM Opportunity Qualification",
            "autoname": "format:{opportunity}-{category}",
            "title_field": "opportunity",
            "search_fields": "opportunity,template,category,status",
            "fields": [
                field("opportunity", "Opportunity", "Link", options="CRM Opportunity", reqd=1, in_list_view=1),
                field("template", "Template", "Link", options="CRM Qualification Template"),
                field("question", "Question", "Small Text", reqd=1),
                field("category", "Category", "Data", reqd=1, in_list_view=1),
                field("response", "Response", "Text"),
                field("status", "Status", "Select", options=options("Confirmed", "Partial", "Unknown", "Not Applicable"), default="Unknown", in_list_view=1),
                field("score", "Score", "Percent", read_only=1, in_list_view=1),
                field("notes", "Notes", "Small Text"),
            ],
        },
        {
            "name": "CRM Opportunity Stage History",
            "autoname": "CRM-STAGE-HIST-.YYYY.-.#####",
            "search_fields": "opportunity,from_stage,to_stage,changed_by",
            "fields": [
                field("opportunity", "Opportunity", "Link", options="CRM Opportunity", reqd=1, in_list_view=1),
                field("pipeline", "Pipeline", "Link", options="CRM Pipeline"),
                field("from_stage", "From Stage", "Data", in_list_view=1),
                field("to_stage", "To Stage", "Data", in_list_view=1),
                field("changed_on", "Changed On", "Datetime", in_list_view=1),
                field("changed_by", "Changed By", "Link", options="User"),
                field("previous_probability", "Previous Probability", "Percent"),
                field("new_probability", "New Probability", "Percent"),
                field("opportunity_value", "Opportunity Value", "Currency"),
                field("reason", "Reason", "Small Text"),
                field("days_in_previous_stage", "Days in Previous Stage", "Int"),
            ],
        },
    ]


def playbook_specs():
    return [
        {
            "name": "CRM Stage Checklist",
            "autoname": "CRM-STAGE-CHECK-.#####",
            "search_fields": "pipeline,stage,checklist_item",
            "fields": [
                field("pipeline", "Pipeline", "Link", options="CRM Pipeline", reqd=1, in_list_view=1),
                field("stage", "Stage", "Data", reqd=1, in_list_view=1),
                field("checklist_item", "Checklist Item", "Data", reqd=1, in_list_view=1),
                field("mandatory", "Mandatory", "Check"),
                field("sequence", "Sequence", "Int", in_list_view=1),
                field("active", "Active", "Check", default=1),
            ],
        },
        {
            "name": "CRM Opportunity Checklist",
            "autoname": "CRM-OPP-CHECK-.#####",
            "search_fields": "opportunity,stage,checklist_item",
            "fields": [
                field("opportunity", "Opportunity", "Link", options="CRM Opportunity", reqd=1, in_list_view=1),
                field("pipeline", "Pipeline", "Link", options="CRM Pipeline"),
                field("stage", "Stage", "Data", in_list_view=1),
                field("checklist_item", "Checklist Item", "Data", reqd=1, in_list_view=1),
                field("mandatory", "Mandatory", "Check"),
                field("completed", "Completed", "Check", in_list_view=1),
                field("completed_on", "Completed On", "Datetime"),
                field("completed_by", "Completed By", "Link", options="User"),
            ],
        },
        {
            "name": "CRM Playbook Question",
            "istable": 1,
            "fields": [
                field("question", "Question", "Small Text", reqd=1, in_list_view=1),
                field("category", "Category", "Data", in_list_view=1),
                field("sequence", "Sequence", "Int", in_list_view=1),
                field("mandatory", "Mandatory", "Check"),
                field("guidance", "Guidance", "Small Text"),
            ],
        },
        {
            "name": "CRM Recommended Action",
            "istable": 1,
            "fields": [
                field("action", "Action", "Small Text", reqd=1, in_list_view=1),
                field("activity_type", "Activity Type", "Select", options=activity_types(), in_list_view=1),
                field("sequence", "Sequence", "Int", in_list_view=1),
                field("mandatory", "Mandatory", "Check"),
            ],
        },
        {
            "name": "CRM Sales Playbook",
            "autoname": "field:playbook_name",
            "title_field": "playbook_name",
            "search_fields": "playbook_name,opportunity_type,pipeline,applicable_stage,industry",
            "fields": [
                field("playbook_name", "Playbook Name", reqd=1, unique=1, in_list_view=1),
                field("active", "Active", "Check", default=1, in_list_view=1),
                field("opportunity_type", "Opportunity Type", "Select", options=options("New Business", "Existing Customer", "Upsell", "Cross-sell", "Renewal", "Rental", "Managed Service", "Tender")),
                field("pipeline", "Pipeline", "Link", options="CRM Pipeline", in_list_view=1),
                field("applicable_stage", "Applicable Stage", "Data", in_list_view=1),
                field("industry", "Industry", "Link", options="Industry Type"),
                field("description", "Description", "Small Text"),
                field("objectives", "Objectives", "Text"),
                field("questions", "Questions", "Table", options="CRM Playbook Question"),
                field("recommended_actions", "Recommended Actions", "Table", options="CRM Recommended Action"),
                field("objection_handling", "Objection Handling", "Text"),
                field("resources", "Resources", "Text"),
            ],
        },
    ]


def activity_specs():
    return [
        {
            "name": "CRM Meeting Participant",
            "istable": 1,
            "fields": [
                field("contact", "Contact", "Link", options="Contact", in_list_view=1),
                field("email", "Email", "Data", options="Email", in_list_view=1),
                field("role", "Role", "Data"),
                field("attendance_status", "Attendance Status", "Select", options=options("Invited", "Accepted", "Declined", "Attended", "No Show"), default="Invited", in_list_view=1),
            ],
        },
        {
            "name": "CRM Meeting Action Item",
            "istable": 1,
            "fields": [
                field("action", "Action", "Small Text", reqd=1, in_list_view=1),
                field("assigned_to", "Assigned To", "Link", options="User", in_list_view=1),
                field("due_date", "Due Date", "Date", in_list_view=1),
                field("status", "Status", "Select", options=options("Open", "In Progress", "Completed", "Cancelled"), default="Open"),
            ],
        },
        {
            "name": "Sales Activity",
            "autoname": "CRM-ACT-.YYYY.-.#####",
            "title_field": "subject",
            "search_fields": "subject,activity_type,crm_lead,customer,crm_opportunity",
            "fields": [
                sec("Activity"),
                field("activity_type", "Activity Type", "Select", options=options("Call", "Email", "Meeting", "Customer Visit", "Demo", "Presentation", "Task", "Follow-up", "Proposal", "WhatsApp", "Other"), reqd=1, in_list_view=1),
                field("subject", "Subject", reqd=1, in_list_view=1),
                field("activity_date", "Activity Date", "Date", reqd=1, in_list_view=1),
                field("start_time", "Start Time", "Time"),
                field("end_time", "End Time", "Time"),
                field("duration_minutes", "Duration Minutes", "Int"),
                field("status", "Status", "Select", options=options("Planned", "Completed", "Cancelled", "No Show"), default="Planned", in_list_view=1),
                field("meeting_title", "Meeting Title", "Data"),
                field("meeting_type", "Meeting Type", "Data"),
                sec("Links"),
                field("crm_lead", "CRM Lead", "Link", options="CRM Lead", in_list_view=1),
                field("customer", "Customer", "Link", options="Customer"),
                field("crm_account_profile", "CRM Account Profile", "Link", options="CRM Account Profile"),
                field("contact", "Contact", "Link", options="Contact"),
                field("crm_opportunity", "CRM Opportunity", "Link", options="CRM Opportunity", in_list_view=1),
                sec("Ownership"),
                field("assigned_to", "Assigned To", "Link", options="User", in_list_view=1),
                field("created_by", "Created By", "Link", options="User", read_only=1),
                field("sales_team", "Sales Team", "Table", options="Sales Team"),
                sec("Details"),
                field("purpose", "Purpose", "Small Text"),
                field("notes", "Notes", "Text"),
                field("outcome", "Outcome", "Small Text"),
                field("next_action", "Next Action", "Small Text"),
                field("next_action_date", "Next Action Date", "Date", in_list_view=1),
                sec("Meeting"),
                field("participants", "Participants", "Table", options="CRM Meeting Participant"),
                field("meeting_link", "Meeting Link", "Data", options="URL"),
                field("location", "Location", "Data"),
                field("meeting_mode", "Meeting Mode", "Select", options=options("Onsite", "Online", "Phone")),
                field("agenda", "Agenda", "Text"),
                field("meeting_notes", "Meeting Notes", "Text"),
                field("decisions", "Decisions", "Text"),
                field("action_items", "Action Items", "Table", options="CRM Meeting Action Item"),
                sec("Customer Visit"),
                field("customer_site", "Customer Site", "Data"),
                field("visit_purpose", "Visit Purpose", "Small Text"),
                field("visit_outcome", "Visit Outcome", "Small Text"),
                sec("Follow-up"),
                field("follow_up_required", "Follow-up Required", "Check"),
                field("follow_up_date", "Follow-up Date", "Date"),
                sec("Attachments / System"),
                field("communication", "Communication", "Link", options="Communication"),
                field("completed_on", "Completed On", "Datetime", read_only=1),
            ],
        }
    ]


def task_specs():
    return [
        {
            "name": "Sales Task",
            "autoname": "CRM-TASK-.YYYY.-.#####",
            "title_field": "subject",
            "search_fields": "subject,assigned_to,crm_lead,customer,crm_opportunity,status",
            "fields": [
                field("subject", "Subject", reqd=1, in_list_view=1),
                field("task_type", "Task Type", "Select", options=activity_types(), default="Follow-up", in_list_view=1),
                field("status", "Status", "Select", options=options("Open", "In Progress", "Completed", "Cancelled"), default="Open", in_list_view=1),
                field("priority", "Priority", "Select", options=options("Low", "Medium", "High", "Urgent"), default="Medium", in_list_view=1),
                field("assigned_to", "Assigned To", "Link", options="User", in_list_view=1),
                field("due_date", "Due Date", "Date", in_list_view=1),
                field("due_time", "Due Time", "Time"),
                field("completed_on", "Completed On", "Datetime", read_only=1),
                sec("Links"),
                field("crm_lead", "CRM Lead", "Link", options="CRM Lead"),
                field("customer", "Customer", "Link", options="Customer"),
                field("contact", "Contact", "Link", options="Contact"),
                field("crm_opportunity", "CRM Opportunity", "Link", options="CRM Opportunity"),
                field("sales_activity", "Sales Activity", "Link", options="Sales Activity"),
                sec("Details"),
                field("description", "Description", "Text"),
                field("outcome", "Outcome", "Text"),
                field("next_step", "Next Step", "Small Text"),
            ],
        }
    ]


def lead_statuses():
    return options("New", "Unassigned", "Assigned", "Attempting Contact", "Connected", "Qualifying", "Qualified", "Nurture", "Disqualified", "Converted")


def qualification_statuses():
    return options("Confirmed", "Partial", "Unknown", "Not Applicable")


def relationship_strengths():
    return options("Strong", "Positive", "Neutral", "Weak", "Negative")


def contact_roles():
    return options("Decision Maker", "Economic Buyer", "Champion", "Influencer", "Technical Evaluator", "Procurement", "Finance", "End User", "Gatekeeper", "Blocker", "Other")


def activity_types():
    return options("Call", "Email", "Meeting", "Customer Visit", "Demo", "Presentation", "Task", "Follow-up", "Proposal", "WhatsApp", "Internal", "Other")
