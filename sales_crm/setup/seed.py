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


def create_stage_checklists():
    pipeline = frappe.db.get_value("CRM Pipeline", {"pipeline_code": "ENT"}, "name")
    if not pipeline:
        return

    items = {
        "Qualification": [
            ("Business need documented", 1),
            ("Budget discussed", 1),
            ("Decision maker identified", 1),
            ("Timeline understood", 1),
            ("Next action scheduled", 1),
        ],
        "Solution Design": [
            ("Technical requirements documented", 1),
            ("Solution proposed", 1),
            ("Technical contact engaged", 0),
            ("Scope confirmed", 1),
        ],
        "Proposal": [
            ("Products and quantities confirmed", 1),
            ("Pricing reviewed", 1),
            ("Quotation created", 1),
            ("Decision maker received proposal", 1),
            ("Follow-up scheduled", 1),
        ],
        "Negotiation": [
            ("Commercial terms discussed", 1),
            ("Competition identified", 0),
            ("Approval authority confirmed", 1),
            ("Expected close date validated", 1),
        ],
        "Commit": [
            ("Customer verbal confirmation", 1),
            ("Final price agreed", 1),
            ("Purchase process understood", 1),
            ("Procurement next step confirmed", 1),
        ],
    }

    for stage, stage_items in items.items():
        for seq, (label, mandatory) in enumerate(stage_items, start=1):
            if frappe.db.exists("CRM Stage Checklist", {"pipeline": pipeline, "stage": stage, "checklist_item": label}):
                continue
            doc = frappe.new_doc("CRM Stage Checklist")
            doc.pipeline = pipeline
            doc.stage = stage
            doc.checklist_item = label
            doc.mandatory = mandatory
            doc.sequence = seq
            doc.active = 1
            doc.insert(ignore_permissions=True)


def create_default_playbooks():
    pipeline = frappe.db.get_value("CRM Pipeline", {"pipeline_code": "ENT"}, "name")
    create_playbook(
        "Enterprise Discovery",
        pipeline,
        "Discovery",
        "Understand the account context, decision process, and business impact.",
        [
            "What business problem are you trying to solve?",
            "What is the impact of the current situation?",
            "Who owns the decision?",
            "What budget has been allocated?",
            "What is the expected implementation timeline?",
            "What alternatives are being evaluated?",
        ],
        ["Schedule discovery meeting", "Document business need", "Identify decision maker"],
    )
    create_playbook(
        "Proposal Follow-up",
        pipeline,
        "Proposal",
        "Confirm proposal receipt, objections, and decision timeline.",
        [],
        ["Confirm proposal receipt", "Confirm commercial understanding", "Validate decision timeline", "Identify objections", "Schedule next meeting"],
    )
    create_playbook(
        "Negotiation",
        pipeline,
        "Negotiation",
        "Resolve approval blockers and commercial gaps.",
        [
            "What is preventing approval?",
            "Is pricing the primary concern?",
            "Has procurement reviewed the proposal?",
            "Are competitors still active?",
            "Who has final approval authority?",
        ],
        ["Confirm buying process", "Document objections", "Schedule approval meeting"],
    )


def create_playbook(name, pipeline, stage, description, questions, actions):
    if frappe.db.exists("CRM Sales Playbook", name):
        return
    doc = frappe.new_doc("CRM Sales Playbook")
    doc.playbook_name = name
    doc.active = 1
    doc.pipeline = pipeline
    doc.applicable_stage = stage
    doc.description = description
    doc.objectives = description
    for seq, question in enumerate(questions, start=1):
        doc.append("questions", {"question": question, "category": stage, "sequence": seq, "mandatory": 1})
    for seq, action in enumerate(actions, start=1):
        doc.append("recommended_actions", {"action": action, "activity_type": "Follow-up", "sequence": seq, "mandatory": seq == 1})
    doc.insert(ignore_permissions=True)
