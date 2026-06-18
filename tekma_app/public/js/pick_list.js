frappe.ui.form.on('Pick List', {
    refresh(frm) {
        load_so_summary(frm);
    },
    onload(frm) {
        if (!frm.is_new()) return;
        load_so_summary(frm);
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
    },
    before_save: (frm) => {
		(frm.doc.locations || []).forEach((row) => {
			// if (!flt(row.picked_qty) || flt(row.picked_qty) > flt(row.stock_qty)) {
			frappe.model.set_value(row.doctype, row.name, "picked_qty", row.stock_qty);
			// }
		});
	},
    	before_submit: (frm) => {
		return frappe
			.call({
				method: "tekma_app.custom.pick_list.validate_sales_order_qty",
				args: {
					doc: frm.doc,
				}
			})
			.then((r) => {
				let errors = r.message || [];

				if (!errors.length) return;

				let html = `
		<table class="table table-bordered">
			<tr>
				<th>Sales Order</th>
				<th>Item</th>
				<th>SO Qty</th>
				<th>Picked</th>
				<th>Diff</th>
			</tr>
	`;

				errors.forEach((e) => {
					html += `
			<tr>
				<td>${e.sales_order}</td>
				<td>${e.item_code}</td>
				<td>${e.so_qty}</td>
				<td>${e.picked_qty}</td>
				<td>${e.diff}</td>
			</tr>
		`;
				});

				html += `</table>`;

				frappe.validated = false;

				frappe.confirm(
					`<b>Ada mismatch Qty Sales Order:</b><br><br>${html}<br><br>Lanjutkan submit?`,
					() => {
						frappe.validated = true;
						frm.save("Submit");
					},
					() => {
						frappe.msgprint("Submit dibatalkan");
					},
				);
			});
	},
});

function get_sales_order(frm) {
    for (let row of (frm.doc.locations || [])) {
        if (row.sales_order) {
            return row.sales_order;
        }
    }
    return null;
}


frappe.ui.form.on("Pick List Item", {
    qty(frm) {
        load_so_summary(frm);
    },

    locations_add(frm) {
        load_so_summary(frm);
    },

    locations_remove(frm) {
        load_so_summary(frm);
    },
	locations_add: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		// ambil SO unik dari existing rows
		let so_list = [...new Set((frm.doc.locations || []).map((d) => d.sales_order).filter(Boolean))];

		if (so_list.length === 0) return;

		let d = new frappe.ui.Dialog({
			title: "Pilih Sales Order",
			fields: [
				{
					fieldtype: "Select",
					fieldname: "sales_order",
					label: "Sales Order",
					options: so_list,
					reqd: 1,
				},
			],
			primary_action_label: "Lanjut",
			primary_action(values) {
				d.hide();
				open_item_dialog(values.sales_order);
			},
		});

		d.show();

		const open_item_dialog = (sales_order) => {
			// ambil item dari row existing (bisa diganti server call kalau mau lebih valid)
			let items = (frm.doc.locations || [])
				.filter((d) => d.sales_order === sales_order)
				.map((d) => ({
					value: d.sales_order_item,
					label: d.item_code || d.sales_order_item,
				}))
				.filter((d) => d.value);

			// unique
			let unique_items = [];
			let seen = new Set();

			items.forEach((i) => {
				if (!seen.has(i.value)) {
					seen.add(i.value);
					unique_items.push(i);
				}
			});

			if (unique_items.length === 0) return;

			let d2 = new frappe.ui.Dialog({
				title: "Pilih Item",
				fields: [
					{
						fieldtype: "HTML",
						fieldname: "item_list",
					},
				],
			});

			// render clickable list (lebih enak dari select)
			let html = `
                <div class="list-group">
                    ${unique_items
						.map(
							(i) => `
                        <a class="list-group-item list-group-item-action"
                           data-value="${i.value}">
                           ${i.label}
                        </a>
                    `,
						)
						.join("")}
                </div>
            `;

			d2.fields_dict.item_list.$wrapper.html(html);

			d2.$wrapper.find(".list-group-item").on("click", function () {
				let val = $(this).data("value");

				row.sales_order = sales_order;
				row.sales_order_item = val;

				frm.refresh_field("locations");
				d2.hide();
			});

			d2.show();
		};
	},
});


function load_so_summary(frm) {

    if (!frm.doc.name || frm.is_new()) {
        return;
    }

    frappe.call({
        method: "tekma_app.custom.pick_list.get_pick_list_summary",
        args: {
            pick_list: frm.doc.name
        },
        callback(r) {

            let rows = r.message || [];

            if (!rows.length) {
                frm.fields_dict.so_summary_html.$wrapper.html("");
                return;
            }

            let html = `
                <div class="so-summary-wrapper">
                    <table class="table table-bordered table-sm">
                        <thead>
                            <tr>
                                <th>SO</th>
                                <th>Item</th>
                                <th class="text-right">SO Qty</th>
                                <th class="text-right">Picked</th>
                                <th class="text-right">Diff</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            rows.forEach(row => {

                let cls = "";

                if (row.diff_qty < 0) {
                    cls = "text-warning";
                } else if (row.diff_qty > 0) {
                    cls = "text-danger";
                } else {
                    cls = "text-success";
                }

                html += `
                    <tr>
                        <td>${row.sales_order}</td>
                        <td>${row.item_name || row.item_code}</td>
                        <td class="text-right">${format_number(row.so_qty)}</td>
                        <td class="text-right">${format_number(row.picked_qty)}</td>
                        <td class="text-right ${cls}">
                            ${format_number(row.diff_qty)}
                        </td>
                    </tr>
                `;
            });

            html += `
                        </tbody>
                    </table>
                </div>
            `;

            frm.fields_dict.so_summary_html.$wrapper.html(html);
        }
    });
}
