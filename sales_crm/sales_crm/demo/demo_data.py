import frappe
from frappe.utils import add_days, today

from sales_crm.setup.seed import create_default_pipeline, create_default_qualification_template


LEADS = [
    ("Pacific Commercial Bank", "Chief Information Officer", 420000),
    ("PNG Telecommunications", "Network Operations Manager", 380000),
    ("Highlands Mining", "Procurement Manager", 210000),
    ("Coral Retail Group", "Retail Systems Lead", 175000),
    ("Island Medical Centre", "Operations Director", 95000),
    ("Western Logistics", "Infrastructure Manager", 145000),
    ("National Government Department", "ICT Director", 520000),
    ("Pacific Hospitality Group", "General Manager", 130000),
    ("Harbour Construction", "Finance Manager", 90000),
    ("Sepik Education Trust", "Administration Lead", 65000),
]

OPPORTUNITIES = [
    ("Pacific Commercial Bank - Data Centre Refresh", "Pacific Commercial Bank", "Discovery", 420000),
    ("PNG Telecommunications - Managed Network Upgrade", "PNG Telecommunications", "Solution Design", 380000),
    ("Highlands Mining - Printer Fleet Replacement", "Highlands Mining", "Proposal", 210000),
    ("Coral Retail - POS Rollout", "Coral Retail Group", "Qualification", 175000),
    ("Island Medical - Managed IT Support", "Island Medical Centre", "Negotiation", 95000),
    ("Western Logistics - Warehouse Infrastructure", "Western Logistics", "Prospecting", 145000),
    ("Government Department - Hardware Tender", "National Government Department", "Commit", 520000),
    ("Pacific Hospitality - WiFi Upgrade", "Pacific Hospitality Group", "Discovery", 130000),
]


def create_demo_data():
    create_default_pipeline()
    create_managed_services_pipeline()
    create_default_qualification_template()
    ensure_demo_leads()
    ensure_demo_accounts()
    ensure_demo_opportunities()
    frappe.db.commit()
    return "Sales CRM demo data created or updated."


def create_managed_services_pipeline():
    if frappe.db.exists("CRM Pipeline", {"pipeline_code": "MS"}):
        return

    pipeline = frappe.new_doc("CRM Pipeline")
    pipeline.pipeline_name = "Managed Services"
    pipeline.pipeline_code = "MS"
    pipeline.applicable_to = "Managed Services"
    pipeline.currency = "PGK" if frappe.db.exists("Currency", "PGK") else None
    pipeline.active = 1
    for idx, (name, probability, stage_type) in enumerate(
        [
            ("Prospecting", 10, "Open"),
            ("Assessment", 30, "Open"),
            ("Service Design", 55, "Open"),
            ("Commercial Review", 75, "Open"),
            ("Closed Won", 100, "Won"),
            ("Closed Lost", 0, "Lost"),
        ],
        start=1,
    ):
        pipeline.append(
            "stages",
            {
                "stage_name": name,
                "stage_code": name.upper().replace(" ", "_"),
                "sequence": idx,
                "probability": probability,
                "stage_type": stage_type,
                "require_expected_close_date": 1 if stage_type == "Open" else 0,
                "require_next_action": 1 if stage_type == "Open" else 0,
                "require_qualification": 1 if name in ("Commercial Review",) else 0,
                "allow_quotation": 1 if name in ("Commercial Review",) else 0,
                "active": 1,
            },
        )
    pipeline.insert(ignore_permissions=True)


def ensure_demo_leads():
    for idx, (org, designation, value) in enumerate(LEADS, start=1):
        if frappe.db.exists("CRM Lead", {"organization_name": org}):
            continue
        lead = frappe.new_doc("CRM Lead")
        lead.lead_name = f"{org} Lead"
        lead.organization_name = org
        lead.designation = designation
        lead.email = f"contact{idx}@example.pg"
        lead.mobile_no = f"+6757000{idx:04d}"
        lead.lead_status = "Qualified" if idx <= 6 else "Assigned"
        lead.lead_source = frappe.db.get_value("Lead Source", {}, "name")
        lead.territory = frappe.db.get_value("Territory", {"is_group": 0}, "name")
        lead.country = "Papua New Guinea" if frappe.db.exists("Country", "Papua New Guinea") else None
        lead.lead_owner = frappe.session.user
        lead.estimated_value = value
        lead.currency = "PGK" if frappe.db.exists("Currency", "PGK") else None
        lead.expected_purchase_date = add_days(today(), 45 + idx * 7)
        lead.budget_status = "Confirmed" if idx <= 5 else "Partial"
        lead.authority_status = "Confirmed" if idx <= 4 else "Partial"
        lead.need_status = "Confirmed"
        lead.timeline_status = "Partial"
        lead.next_action = "Schedule discovery call"
        lead.next_action_date = add_days(today(), idx)
        lead.created_by_source = "Sales CRM demo"
        lead.insert(ignore_permissions=True)


def ensure_demo_accounts():
    for org, _, _ in LEADS[:5]:
        customer = ensure_customer(org)
        if not frappe.db.exists("CRM Account Profile", customer):
            profile = frappe.new_doc("CRM Account Profile")
            profile.customer = customer
            profile.account_tier = "Enterprise" if org in ("Pacific Commercial Bank", "PNG Telecommunications") else "Major"
            profile.account_status = "Prospect"
            profile.account_owner = frappe.session.user
            profile.relationship_strength = "Positive"
            profile.account_health_score = 70
            profile.strategic_account = 1 if org in ("Pacific Commercial Bank", "PNG Telecommunications") else 0
            profile.website = f"https://{org.lower().replace(' ', '')}.example.pg"
            profile.insert(ignore_permissions=True)


def ensure_demo_opportunities():
    pipeline = frappe.db.get_value("CRM Pipeline", {"pipeline_code": "ENT"}, "name")
    item = frappe.db.get_value("Item", {"disabled": 0}, "name")
    for idx, (name, customer_name, stage, value) in enumerate(OPPORTUNITIES, start=1):
        if frappe.db.exists("CRM Opportunity", {"opportunity_name": name}):
            continue
        customer = ensure_customer(customer_name)
        lead = frappe.db.get_value("CRM Lead", {"organization_name": customer_name}, "name")
        opp = frappe.new_doc("CRM Opportunity")
        opp.opportunity_name = name
        opp.customer = customer
        opp.crm_account_profile = customer if frappe.db.exists("CRM Account Profile", customer) else None
        opp.lead = lead
        opp.opportunity_owner = frappe.session.user
        opp.pipeline = pipeline
        opp.stage = stage
        opp.currency = "PGK" if frappe.db.exists("Currency", "PGK") else None
        opp.opportunity_value = value
        opp.expected_close_date = add_days(today(), 30 + idx * 8)
        opp.opportunity_type = "Managed Service" if "Managed" in name else "New Business"
        opp.business_need = "Modernize critical business technology and improve operating resilience."
        opp.next_action = "Confirm stakeholder meeting"
        opp.next_action_date = add_days(today(), idx + 2)
        if item:
            opp.append("products", {"item_code": item, "qty": 1, "rate": value})
        opp.insert(ignore_permissions=True)
        create_activities(opp.name, customer, idx)
        create_qualification(opp.name)


def ensure_customer(customer_name):
    existing = frappe.db.get_value("Customer", {"customer_name": customer_name}, "name")
    if existing:
        return existing
    customer = frappe.new_doc("Customer")
    customer.customer_name = customer_name
    customer.customer_type = "Company"
    customer.customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
    customer.territory = frappe.db.get_value("Territory", {"is_group": 0}, "name")
    customer.insert(ignore_permissions=True)
    return customer.name


def create_activities(opportunity, customer, idx):
    for activity_type, subject in [("Call", "Initial qualification call"), ("Meeting", "Discovery meeting")]:
        if frappe.db.exists("Sales Activity", {"crm_opportunity": opportunity, "subject": subject}):
            continue
        activity = frappe.new_doc("Sales Activity")
        activity.activity_type = activity_type
        activity.subject = subject
        activity.activity_date = add_days(today(), -idx)
        activity.status = "Completed"
        activity.customer = customer
        activity.crm_opportunity = opportunity
        activity.assigned_to = frappe.session.user
        activity.outcome = "Positive engagement"
        activity.next_action = "Prepare next step"
        activity.next_action_date = add_days(today(), idx)
        activity.insert(ignore_permissions=True)


def create_qualification(opportunity):
    template = "BANT" if frappe.db.exists("CRM Qualification Template", "BANT") else None
    rows = [
        ("Budget", "Is budget approved or reasonably available?", "Confirmed"),
        ("Authority", "Have we identified the economic buyer and decision process?", "Confirmed"),
        ("Need", "Is there a clear business need with measurable impact?", "Confirmed"),
        ("Timeline", "Is there a defined purchase or implementation timeline?", "Unknown"),
    ]
    for category, question, status in rows:
        if frappe.db.exists("CRM Opportunity Qualification", {"opportunity": opportunity, "category": category}):
            continue
        row = frappe.new_doc("CRM Opportunity Qualification")
        row.opportunity = opportunity
        row.template = template
        row.category = category
        row.question = question
        row.status = status
        row.insert(ignore_permissions=True)
