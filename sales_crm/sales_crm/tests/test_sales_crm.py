import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from sales_crm.install import after_install


class SalesCRMTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        after_install()

    def make_opportunity(self, stage="Prospecting", **kwargs):
        pipeline = frappe.db.get_value("CRM Pipeline", {"pipeline_code": "ENT"}, "name")
        doc = frappe.new_doc("CRM Opportunity")
        doc.opportunity_name = kwargs.get("opportunity_name", "Test Opportunity")
        doc.pipeline = pipeline
        doc.stage = stage
        doc.opportunity_value = kwargs.get("opportunity_value", 1000)
        doc.expected_close_date = add_days(today(), 30)
        doc.next_action = "Call customer"
        doc.insert(ignore_permissions=True)
        return doc

    def test_pipeline_stage_probability_validation(self):
        pipeline = frappe.copy_doc(frappe.get_doc("CRM Pipeline", {"pipeline_code": "ENT"}))
        pipeline.pipeline_name = "Invalid Probability Test"
        pipeline.pipeline_code = frappe.generate_hash(length=8)
        pipeline.stages[0].probability = 101
        self.assertRaises(frappe.ValidationError, pipeline.insert)

    def test_weighted_opportunity_value(self):
        opp = self.make_opportunity(opportunity_value=2000)
        self.assertEqual(opp.probability, 10)
        self.assertEqual(opp.weighted_value, 200)

    def test_stage_history_creation(self):
        opp = self.make_opportunity()
        opp.stage = "Qualification"
        opp.save(ignore_permissions=True)
        self.assertTrue(frappe.db.exists("CRM Opportunity Stage History", {"opportunity": opp.name, "to_stage": "Qualification"}))

    def test_qualification_score(self):
        opp = self.make_opportunity()
        for category, status in [("Budget", "Confirmed"), ("Authority", "Confirmed"), ("Need", "Partial"), ("Timeline", "Unknown")]:
            row = frappe.new_doc("CRM Opportunity Qualification")
            row.opportunity = opp.name
            row.category = category
            row.question = category
            row.status = status
            row.insert(ignore_permissions=True)
        self.assertEqual(frappe.db.get_value("CRM Opportunity", opp.name, "qualification_score"), 62.5)

    def test_closed_lost_requires_reason_and_notes(self):
        opp = self.make_opportunity(stage="Commit")
        opp.stage = "Closed Lost"
        self.assertRaises(frappe.ValidationError, opp.save)

    def test_sales_activity_updates_opportunity(self):
        opp = self.make_opportunity()
        activity = frappe.new_doc("Sales Activity")
        activity.activity_type = "Call"
        activity.subject = "Test call"
        activity.activity_date = today()
        activity.status = "Completed"
        activity.crm_opportunity = opp.name
        activity.next_action = "Send proposal"
        activity.next_action_date = add_days(today(), 1)
        activity.insert(ignore_permissions=True)
        self.assertEqual(frappe.db.get_value("CRM Opportunity", opp.name, "next_action"), "Send proposal")

    def test_lead_conversion_creates_opportunity(self):
        lead = frappe.new_doc("CRM Lead")
        lead.lead_name = "Conversion Test Lead"
        lead.organization_name = "Conversion Test Company"
        lead.estimated_value = 1500
        lead.expected_purchase_date = add_days(today(), 20)
        lead.next_action = "Qualify"
        lead.insert(ignore_permissions=True)

        result = frappe.call(
            "sales_crm.api.lead.convert_lead",
            lead=lead.name,
            conversion_type="create_opportunity_only",
            opportunity_name="Converted Test Opportunity",
        )
        self.assertTrue(result["opportunity"])
        self.assertTrue(frappe.db.get_value("CRM Lead", lead.name, "converted"))

    def test_quotation_creation_linkage(self):
        if not frappe.db.exists("Item", {"disabled": 0}):
            self.skipTest("No enabled Item available for quotation linkage test")
        customer = get_or_create_customer()
        item = frappe.db.get_value("Item", {"disabled": 0}, "name")
        opp = self.make_opportunity(stage="Proposal")
        opp.customer = customer
        opp.append("products", {"item_code": item, "qty": 1, "rate": 1000})
        opp.save(ignore_permissions=True)

        quotation = frappe.call("sales_crm.api.opportunity.create_quotation", opportunity=opp.name)
        self.assertEqual(frappe.db.get_value("CRM Opportunity", opp.name, "quotation"), quotation)


def get_or_create_customer():
    existing = frappe.db.get_value("Customer", {"customer_name": "Sales CRM Test Customer"}, "name")
    if existing:
        return existing
    customer = frappe.new_doc("Customer")
    customer.customer_name = "Sales CRM Test Customer"
    customer.customer_type = "Company"
    customer.customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
    customer.territory = frappe.db.get_value("Territory", {"is_group": 0}, "name")
    customer.insert(ignore_permissions=True)
    return customer.name
