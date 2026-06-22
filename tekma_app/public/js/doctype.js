const doctypes = [
    { 
        dt: "Pick List", items_key: "locations", prev: "Sales Order", key: "sales_order"
    }, { 
        dt: "Delivery Note", items_key: "items", prev: "Pick List", key: "against_pick_list"
    }, { 
        dt: "Sales Invoice", items_key: "items", prev: "Delivery Note", key: "delivery_note"
    }]
doctypes.forEach(dt => {
    frappe.ui.form.on(dt.dt, {
        after_load(frm){
            load_note_internal(frm, dt)
        },
        refresh(frm) {
            load_note_internal(frm, dt)
        }
    })
})
function load_note_internal(frm, dt) {
    let orders = get_ref_doctype(frm.doc, dt.items_key, dt.key)
    let note_internal = ""
    if (orders.length) {
        frappe.db.get_list(dt.prev, { fields: ["name", "note_internal"], filters: [["name", "in", [...new Set(orders)].sort()]] }, "note_internal")
            .then(list => {
                for (let i = 0; i < list.length; i++) {
                    const el = list[i];
                    if (el.note_internal) {
                        if (list.length == 1) {
                            note_internal = el.note_internal
                        } else {
                            note_internal += el.name + ": " + el.note_internal + "\n"
                        }
                    }
                }
                return true
            }).then(() => {
                frm.set_value("note_internal", note_internal)
            })
    }
}
function get_ref_doctype(doc, list, key) {
    return doc[list].map(d => d[key])
}