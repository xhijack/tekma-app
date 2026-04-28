frappe.ui.form.on('Pick List', {
    onload: function(frm) {
        if (frm.doc.delivery_date) return;

        let so = null;

        (frm.doc.locations || []).forEach(row => {
            if (!so && row.sales_order) {
                so = row.sales_order;
            }
        });

        if (!so) return;

        frappe.db.get_value('Sales Order', so, 'delivery_date')
            .then(r => {
                if (r.message && r.message.delivery_date) {
                    frm.set_value('delivery_date', r.message.delivery_date);
                }
            });
    }
});