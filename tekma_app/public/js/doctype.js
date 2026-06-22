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
    if (orders.length) {
        frappe.db.get_list(dt.prev, { fields: ["name", "note_internal"], filters: [["name", "in", [...new Set(orders)].sort()]] }, "note_internal")
            .then(list => {
                let note_internal = [];

                for (const el of list) {
                    if (el.note_internal) {
                        if (list.length === 1) {
                            note_internal.push(...el.note_internal.split("\n").filter(Boolean));
                        } else {
                            note_internal.push(`${el.name}: ${el.note_internal}`);
                        }
                    }
                }

                // Note yang sudah ada
                let old_note = (frm.doc.note_internal || "")
                    .split("\n")
                    .filter(Boolean);
                console.log("old note", old_note)
                console.log(note_internal)
                // Tambahkan hanya yang belum ada
                let new_note = note_internal.filter(
                    note => !old_note.includes(note)
                );

                if (new_note.length) {
                    frm.set_value(
                        "note_internal",
                        [...new_note, ...old_note].join("\n\n")
                    );
                }
            })
    }
}
function get_ref_doctype(doc, list, key) {
    return doc[list].map(d => d[key])
}