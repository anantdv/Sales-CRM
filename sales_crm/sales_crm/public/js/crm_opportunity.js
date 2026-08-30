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

        frm.add_custom_button(__("Mark Won"), () => mark_won(frm), __("Actions"));
        frm.add_custom_button(__("Mark Lost"), () => mark_lost(frm), __("Actions"));
        if (["Won", "Lost"].includes(frm.doc.status)) {
            frm.add_custom_button(__("Reopen"), () => reopen(frm), __("Actions"));
        }
        frm.add_custom_button(__("Ensure Stage Checklist"), () => {
            frappe.call({
                method: "sales_crm.api.opportunity.ensure_stage_checklist",
                args: { opportunity: frm.doc.name },
                callback() {
                    frappe.show_alert(__("Stage checklist is ready"));
                },
            });
        }, __("Guidance"));

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

        render_deal_room(frm);
    },
});

function render_deal_room(frm) {
    frappe.call({
        method: "sales_crm.api.opportunity.get_deal_room_data",
        args: { opportunity: frm.doc.name },
        callback(r) {
            const data = r.message || {};
            const health = data.health || {};
            const positives = (health.positives || []).map(x => `<li>${frappe.utils.escape_html(x)}</li>`).join("");
            const risks = (health.risks || []).map(x => `<li>${frappe.utils.escape_html(x)}</li>`).join("");
            const checklist = (data.checklist || []).map(x => `<li>${x.mandatory ? "<b>*</b> " : ""}${frappe.utils.escape_html(x.checklist_item)}</li>`).join("");
            frm.dashboard.add_section(`
                <div class="crm-deal-room">
                    <div><b>${__("Deal Health")}:</b> ${health.score || 0} / 100 - ${health.status || ""}</div>
                    <div><b>${__("Positive Signals")}</b><ul>${positives || `<li>${__("None yet")}</li>`}</ul></div>
                    <div><b>${__("Risks")}</b><ul>${risks || `<li>${__("None")}</li>`}</ul></div>
                    <div><b>${__("Stage Checklist")}</b><ul>${checklist || `<li>${__("No checklist for this stage")}</li>`}</ul></div>
                </div>
            `, __("Deal Room"));
        },
    });
}

function mark_won(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __("Mark Won"),
        fields: [
            { fieldname: "actual_close_date", label: __("Actual Close Date"), fieldtype: "Date", default: frappe.datetime.nowdate(), reqd: 1 },
            { fieldname: "final_value", label: __("Final Value"), fieldtype: "Currency", default: frm.doc.opportunity_value, reqd: 1 },
            { fieldname: "notes", label: __("Notes"), fieldtype: "Text" },
        ],
        primary_action_label: __("Mark Won"),
        primary_action(values) {
            frappe.call({
                method: "sales_crm.api.opportunity.mark_won",
                args: { opportunity: frm.doc.name, ...values },
                callback() {
                    dialog.hide();
                    frm.reload_doc();
                },
            });
        },
    });
    dialog.show();
}

function mark_lost(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __("Mark Lost"),
        fields: [
            { fieldname: "lost_reason", label: __("Lost Reason"), fieldtype: "Small Text", reqd: 1 },
            { fieldname: "closure_notes", label: __("Closure Notes"), fieldtype: "Text", reqd: 1 },
            { fieldname: "competitor", label: __("Competitor"), fieldtype: "Data" },
            { fieldname: "competitor_price", label: __("Competitor Price"), fieldtype: "Currency" },
            { fieldname: "lessons_learned", label: __("Lessons Learned"), fieldtype: "Text" },
        ],
        primary_action_label: __("Mark Lost"),
        primary_action(values) {
            frappe.call({
                method: "sales_crm.api.opportunity.mark_lost",
                args: { opportunity: frm.doc.name, ...values },
                callback() {
                    dialog.hide();
                    frm.reload_doc();
                },
            });
        },
    });
    dialog.show();
}

function reopen(frm) {
    frappe.prompt(
        [{ fieldname: "reopen_reason", label: __("Reopen Reason"), fieldtype: "Small Text", reqd: 1 }],
        values => frappe.call({
            method: "sales_crm.api.opportunity.reopen_opportunity",
            args: { opportunity: frm.doc.name, reopen_reason: values.reopen_reason },
            callback() {
                frm.reload_doc();
            },
        }),
        __("Reopen Opportunity"),
        __("Reopen")
    );
}
