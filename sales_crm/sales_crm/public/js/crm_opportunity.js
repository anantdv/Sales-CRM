frappe.ui.form.on("CRM Opportunity", {
    refresh(frm) {
        if (frm.doc.__islocal) return;

        frm.add_custom_button(__("Create Quotation"), () => {
            frappe.call({
                method: "sales_crm.api.opportunity.create_quotation",
                args: { opportunity: frm.doc.name },
                callback(r) {
                    if (r.message) {
                        frm.reload_doc();
                        frappe.set_route("Form", "Quotation", r.message);
                    }
                },
            });
        }, __("Actions"));

        [
            ["Log Call", "Call"],
            ["Add Meeting", "Meeting"],
            ["Add Follow-up", "Follow-up"],
            ["Add Demo", "Demo"],
            ["Add Note", "Other"],
        ].forEach(([label, type]) => {
            frm.add_custom_button(__(label), () => {
                frappe.new_doc("Sales Activity", {
                    activity_type: type,
                    subject: `${label}: ${frm.doc.opportunity_name}`,
                    crm_opportunity: frm.doc.name,
                    customer: frm.doc.customer,
                    crm_account_profile: frm.doc.crm_account_profile,
                    contact: frm.doc.primary_contact,
                    assigned_to: frm.doc.opportunity_owner,
                    next_action: frm.doc.next_action,
                    next_action_date: frm.doc.next_action_date,
                });
            }, __("Activity"));
        });
    },
});
