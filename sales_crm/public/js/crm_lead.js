frappe.ui.form.on("CRM Lead", {
    refresh(frm) {
        if (!frm.doc.__islocal && !frm.doc.converted) {
            frm.add_custom_button(__("Convert Lead"), () => show_convert_dialog(frm), __("Actions"));
        }
    },
});

function show_convert_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __("Convert Lead"),
        fields: [
            {
                fieldname: "conversion_type",
                label: __("Conversion Type"),
                fieldtype: "Select",
                options: [
                    "create_opportunity_only",
                    "create_customer_contact_opportunity",
                    "link_customer_create_opportunity",
                ].join("\n"),
                default: "create_opportunity_only",
                reqd: 1,
            },
            { fieldname: "existing_customer", label: __("Existing Customer"), fieldtype: "Link", options: "Customer", depends_on: "eval:doc.conversion_type=='link_customer_create_opportunity'" },
            { fieldname: "customer_name", label: __("Customer Name"), fieldtype: "Data", default: frm.doc.organization_name },
            { fieldname: "customer_group", label: __("Customer Group"), fieldtype: "Link", options: "Customer Group" },
            { fieldname: "territory", label: __("Territory"), fieldtype: "Link", options: "Territory", default: frm.doc.territory },
            { fieldname: "opportunity_name", label: __("Opportunity Name"), fieldtype: "Data", default: `${frm.doc.organization_name || frm.doc.lead_name} Opportunity`, reqd: 1 },
            { fieldname: "pipeline", label: __("Pipeline"), fieldtype: "Link", options: "CRM Pipeline" },
            { fieldname: "stage", label: __("Stage"), fieldtype: "Data" },
            { fieldname: "opportunity_owner", label: __("Opportunity Owner"), fieldtype: "Link", options: "User", default: frm.doc.lead_owner },
            { fieldname: "expected_value", label: __("Expected Value"), fieldtype: "Currency", default: frm.doc.estimated_value },
            { fieldname: "expected_close_date", label: __("Expected Close Date"), fieldtype: "Date", default: frm.doc.expected_purchase_date },
        ],
        primary_action_label: __("Convert"),
        primary_action(values) {
            frappe.call({
                method: "sales_crm.api.lead.convert_lead",
                args: { lead: frm.doc.name, ...values },
                callback(r) {
                    dialog.hide();
                    frm.reload_doc();
                    if (r.message && r.message.opportunity) {
                        frappe.set_route("Form", "CRM Opportunity", r.message.opportunity);
                    }
                },
            });
        },
    });
    dialog.show();
}
