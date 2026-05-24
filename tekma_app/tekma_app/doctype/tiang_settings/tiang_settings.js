// Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
// For license information, please see license.txt

frappe.ui.form.on("Tiang Settings", {
	refresh(frm) {
        frm.call({
            method: "get_series",
            doc: frm.doc,
            callback: function(r){
                frm.set_df_property("dt_series", 'options', r.message)
                frm.set_df_property("tt_series", 'options', r.message)
            },
            error: function(r){
                frappe.msgprint({
                    title: "Failed to fetch Series",
                    indicator: "red",
                    message: r.message
                })
            }
        })
	},
});
