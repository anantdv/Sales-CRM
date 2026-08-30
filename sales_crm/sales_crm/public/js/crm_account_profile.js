frappe.ui.form.on("CRM Account Profile", {
    refresh(frm) {
        if (frm.doc.__islocal) return;

        frm.add_custom_button(__("Account 360"), () => {
            frappe.call({
                method: "sales_crm.api.account.get_account_360",
                args: { account_profile: frm.doc.name },
                callback(r) {
                    const summary = r.message && r.message.summary ? r.message.summary : {};
                    frappe.msgprint({
                        title: __("Account 360"),
                        indicator: "blue",
                        message: `
                            <div>
                                <p><b>${__("Open Opportunities")}:</b> ${summary.open_opportunities || 0}</p>
                                <p><b>${__("Pipeline Value")}:</b> ${format_currency(summary.pipeline_value || 0)}</p>
                                <p><b>${__("YTD Revenue")}:</b> ${format_currency(summary.sales_ytd || 0)}</p>
                                <p><b>${__("Outstanding")}:</b> ${format_currency(summary.outstanding_receivable || 0)}</p>
                            </div>
                        `,
                    });
                },
            });
        });
        frm.add_custom_button(__("New Opportunity"), () => frappe.new_doc("CRM Opportunity", {
            customer: frm.doc.customer,
            crm_account_profile: frm.doc.name,
            opportunity_owner: frm.doc.account_owner,
        }), __("Actions"));
        frm.add_custom_button(__("Log Activity"), () => frappe.new_doc("Sales Activity", {
            customer: frm.doc.customer,
            crm_account_profile: frm.doc.name,
        }), __("Actions"));
        frm.add_custom_button(__("Schedule Meeting"), () => frappe.new_doc("Sales Activity", {
            activity_type: "Meeting",
            customer: frm.doc.customer,
            crm_account_profile: frm.doc.name,
        }), __("Actions"));
        frm.add_custom_button(__("Add Contact"), () => frappe.new_doc("CRM Contact Relationship", {
            customer: frm.doc.customer,
            crm_account_profile: frm.doc.name,
        }), __("Actions"));
    },
});
