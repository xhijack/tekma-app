frappe.ui.form.on('Pick List', {
    onload(frm) {
        if (!frm.is_new()) return;

        // DELIVERY DATE
        if (!frm.doc.delivery_date) {
            let so = get_sales_order(frm);
            if (!so) return;

            frappe.db.get_value('Sales Order', so, 'delivery_date')
                .then(r => {
                    if (r.message?.delivery_date) {
                        frm.set_value('delivery_date', r.message.delivery_date);
                    }
                });
        }

        // KETERANGAN
        if (!frm.doc.catatan_untuk_gudang) {
            let so = get_sales_order(frm);
            if (!so) return;

            frappe.db.get_value('Sales Order', so, 'keterangan')
                .then(r => {
                    if (r.message?.keterangan) {
                        frm.set_value('catatan_untuk_gudang', r.message.keterangan);
                    }
                });
        }
    }
});

function get_sales_order(frm) {
    for (let row of (frm.doc.locations || [])) {
        if (row.sales_order) {
            return row.sales_order;
        }
    }
    return null;
}