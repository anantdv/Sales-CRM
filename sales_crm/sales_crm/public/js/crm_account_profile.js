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
    },
});
