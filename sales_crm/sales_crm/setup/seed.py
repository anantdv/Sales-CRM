import frappe


def create_default_pipeline():
    if frappe.db.exists("CRM Pipeline", {"pipeline_code": "ENT"}):
        pipeline = frappe.get_doc("CRM Pipeline", {"pipeline_code": "ENT"})
    else:
        pipeline = frappe.new_doc("CRM Pipeline")
        pipeline.pipeline_name = "Enterprise Sales"
        pipeline.pipeline_code = "ENT"

    pipeline.applicable_to = "Enterprise Sales"
    pipeline.active = 1
    pipeline.default_pipeline = 1
    pipeline.currency = "PGK" if frappe.db.exists("Currency", "PGK") else None
    pipeline.allow_stage_skipping = 0
    pipeline.set("stages", [])

    for idx, (name, probability, stage_type) in enumerate(
        [
            ("Prospecting", 10, "Open"),
            ("Qualification", 20, "Open"),
            ("Discovery", 35, "Open"),
            ("Solution Design", 50, "Open"),
            ("Proposal", 65, "Open"),
            ("Negotiation", 80, "Open"),
            ("Commit", 90, "Open"),
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
                "require_qualification": 1 if name in ("Proposal", "Negotiation", "Commit") else 0,
                "require_next_action": 1 if stage_type == "Open" else 0,
                "require_expected_close_date": 1 if stage_type == "Open" else 0,
                "allow_quotation": 1 if name in ("Proposal", "Negotiation", "Commit") else 0,
                "active": 1,
            },
        )

    pipeline.save(ignore_permissions=True)
    frappe.db.set_single_value("CRM Settings", "default_pipeline", pipeline.name)


def create_default_qualification_template():
    if frappe.db.exists("CRM Qualification Template", "BANT"):
        return

    template = frappe.new_doc("CRM Qualification Template")
    template.template_name = "BANT"
    template.methodology = "BANT"
    template.active = 1
    for idx, (category, question) in enumerate(
        [
            ("Budget", "Is budget approved or reasonably available?"),
            ("Authority", "Have we identified the economic buyer and decision process?"),
            ("Need", "Is there a clear business need with measurable impact?"),
            ("Timeline", "Is there a defined purchase or implementation timeline?"),
        ],
        start=1,
    ):
        template.append(
            "questions",
            {"category": category, "question": question, "required": 1, "weight": 25, "sequence": idx},
        )
    template.insert(ignore_permissions=True)
