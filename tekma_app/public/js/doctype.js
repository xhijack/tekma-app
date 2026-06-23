const doctypes = [
    {
        dt: "Pick List", items_key: "locations", prev: "Sales Order", key: "sales_order", field: "pl_note_internal", p_field: "note_internal"
    },
    {
        dt: "Delivery Note", items_key: "items", prev: "Pick List", key: "against_pick_list", field: "dn_note_internal", p_field: "pl_note_internal"
    },
    {
        dt: "Sales Invoice", items_key: "items", prev: "Delivery Note", key: "delivery_note", field: "si_note_internal", p_field: "dn_note_internal"
    }
]
doctypes.forEach(dt => {
    frappe.ui.form.on(dt.dt, {
        after_load(frm) {
            load_note_internal(frm, dt)
        },
        refresh(frm) {
            load_note_internal(frm, dt)
        }
    })
})
function load_note_internal(frm, dt) {
    let orders = get_ref_doctype(frm.doc, dt.items_key, dt.key)
    let old_val = frm.doc[dt.field]
    if (orders.length && frm.doc?.docstatus == 0) {
        if(old_val?.length > 0) return 
        console.log(orders, old_val, frm.doc, "hello")
        frappe.db.get_list(dt.prev, { fields: ["name", dt.p_field], filters: [["name", "in", [...new Set(orders)].sort()]] }, "note_internal")
            .then(list => {
                let note_internal = [];

                for (const el of list) {
                    let note = el[dt.p_field]
                    if (note) {
                        if (list.length === 1) {
                            note_internal.push(...note.split("\n").filter(Boolean));
                        } else {
                            note_internal.push(`${el.name}: ${note}`);
                        }
                    }
                }
                frm.set_value(dt.field, note_internal.join("\n"))
            })
    }
}
function get_ref_doctype(doc, list, key) {
    return doc[list].map(d => d[key])
}