// Copyright (c) 2025, PT Sopwer Teknologi Indonesia and contributors
// For license information, please see license.txt

frappe.ui.form.on("Daily Production Item", {
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.item_code) return;

        frappe.call({
            method: "tekma_app.tekma_app.doctype.daily_production.daily_production.get_qty_info",
            args: {
                item_code: row.item_code,
                warehouse: frm.doc.warehouse
            },
            callback: function(r) {
                if (r.message) {
                    row.qty_sales_order = r.message.qty_sales_order;
                    row.actual_qty = r.message.actual_qty;
                    row.ratio = r.message.ratio || 0;
                    row.prediction_qty = row.actual_qty + (row.qty_production || 0) - row.qty_sales_order;

                    let ratio = r.message.sum_kg && r.message.prediction_qty != 0 
                                ? r.message.sum_kg / r.message.prediction_qty 
                                : 0;
                    row.sum_kg = ratio * row.prediction_qty;

                    frm.refresh_field("productions");
                }
            }
        });
    },

    qty_production: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        row.prediction_qty = (row.actual_qty || 0) + (row.qty_production || 0) - (row.qty_sales_order || 0);
        row.sum_kg = row.prediction_qty * (row.ratio || 0);

        frm.refresh_field("productions");
    }
});
