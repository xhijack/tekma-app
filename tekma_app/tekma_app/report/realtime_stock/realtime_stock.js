// Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
// For license information, please see license.txt

frappe.query_reports["Realtime Stock"] = {
	filters: [
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group"
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse"
		},
	],

	onload(report) {
	this.report = report
		report.refresh_interval = setInterval(() => {
			report.refresh();
		}, 30 * 1000);

		report.page.add_inner_button(__("Clear Filters"), () => {
			report.filters.forEach(f => {
				if (!f.df.read_only) {
					f.set_value(null);
				}
			});

			report.refresh();
		});

		report.page.add_inner_button(__("Print"), () => {
			this.print_opname(report)
		});
		report.page.add_inner_button(__("Print Summarize"), () => {
			this.print_opname(report, true)
		});
	},

	on_unload(report) {
		if (report.refresh_interval) {
			clearInterval(report.refresh_interval);
		}
	},
	print_opname(report, summarize) {
		let me = this
		let filters = report.get_values()
		frappe.call({
			method: 'frappe.desk.query_report.run',
			args: {
				report_name: 'Realtime Stock',
				filters: filters
			},
			callback({ message }) {
				if (message) {
					me.make_html(me.grouping_stock(message.result), summarize)
				}
			}
		})
	},
	grouping_stock(data) {
		if (!Array.isArray(data)) return [];

		const groupedMap = data.reduce((acc, row) => {
			// skip invalid row (total row, dll)
			if (Array.isArray(row) || !row || !row.item_code) {
				return acc;
			}

			const key = row.item_code + "||" + row.parent_warehouse;

			if (!acc[key]) {
				acc[key] = {
					item_code: row.item_code,
					item_name: row.item_name || "",
					parent_warehouse: row.parent_warehouse,
					total_qty: 0,
					stock_uom: row.stock_uom,
					children: []
				};
			}

			acc[key].total_qty += Number(row.qty || 0);

			acc[key].children.push({
				item_code: row.item_code,
				item_name: row.item_name,
				warehouse: row.warehouse,
				batch_no: row.batch_no,
				manufacturing_date: row.manufacturing_date,
				qty: Number(row.qty || 0),
				stock_uom: row.stock_uom,
			});

			return acc;
		}, {});
		return Object.values(groupedMap);
	},
	make_html(stocks, summarize) {
		let rows = stocks.map(group => {

			let parent_row = `
			<tr class="bold">
				<td>${group.item_name}</td>
				<td>${this.short_wh(group.parent_warehouse)}</td>
				<td>-</td>
				<td>${formatNumber(group.total_qty)}</td>
				<td>${group.stock_uom}</td>
				<td></td>
				<td></td>
			</tr>
		`;

			let child_rows = group.children.map(child => `
			<tr class="${group.children.length == 1 ? 'bold' : ''}">
				<td>${group.children.length == 1 ? group.item_name : ""}</td>
				<td>${group.children.length == 1 ? this.short_wh(child.warehouse) + " - " + this.short_wh(group.parent_warehouse) : this.short_wh(child.warehouse)}</td>
				<td>${summarize ? "-": child.batch_no || "-"}</td>
				<td>${formatNumber(child.qty)}</td>
				<td>${child.stock_uom}</td>
				<td></td>
				<td></td>
			</tr>
		`).join("");
			if (summarize) {
				return group.children.length > 1 ? parent_row : child_rows;
			}
			return group.children.length > 1 ? parent_row + child_rows : child_rows;
		}).join("");
		let warehouse = ''
		let item_group = ''
		if(this.report){
			let filters = this.report.get_values()
			warehouse = filters.warehouse
			item_group = filters.item_group
		}
		const date = new Date();
		const month = date.toLocaleString('id-ID', { month: 'long' });
		let title = `Opname ${item_group || ""} ${month} ${date.getFullYear()}`
		title = summarize? "(Summary) "+title: "(Batch) "+title
		if(warehouse){
			title += ` - ${warehouse}`
		}
		let style = `
			<style>
				@page {
					size: A4 portrait;
					margin: 10mm;
					margin-bottom: 15mm;
					@bottom-center {
						content: "${(new Date()).toLocaleString("id-ID").replaceAll(".",":")} " counter(page) "/" counter(pages);
						font-size: 11px;
					}
				}
				@media print {
					td, th {
						-webkit-print-color-adjust: exact;
						print-color-adjust: exact;
					}

					body {
						counter-reset: page; 
					}
					
					.page-number:after {
						counter-increment: page;
						content: "[P." counter(page) "]";
					}

				}
				*{
					font-size: 12px;
				}
				body {
					font-family: Arial, sans-serif;
					text-align: center;
				}
				h3 {
					margin-bottom: 10px;
				}
				table {
					border-collapse: collapse;
					width: 100%;
					margin: 0 auto;
					text-align: left;
				}
				th, td {
					border: 1px solid #000;
					padding: 4px;
					font-size: 11px;
				}
				th {
					text-align:center;
				}
				tr.bold td{
					font-weight: bold;
				}
			</style>
		`
		let table = `
		<h2>${title}</h2>
		<table border="1" cellspacing="0" cellpadding="6" width="100%">
			<thead>
				<tr>
					<th>Item Name</th>
					<th>Warehouse</th>
					<th>Batch</th>
					<th>Qty</th>
					<th>UoM</th>
					<th>Qty Real</th>
					<th>Selisih</th>
				</tr>
			</thead>
			<tbody>
				${rows}
			</tbody>
		</table>
		`;
		let html = `
		<html>
			<head>
				${style}
				<title>${title}</title>
				</head>
			<body>
				${table}
				<div style="margin-top: 10px; display: flex; flex-direction: column; align-items: flex-start;">
					<p style="margin: 0;">Catatan:</p>
					<p style="width: 100%; border-bottom: 1px solid black; margin: 0;">&nbsp;</p>
					<p style="width: 100%; border-bottom: 1px solid black; margin: 0; margin-top: 10px;">&nbsp;</p>
					<p style="width: 100%; border-bottom: 1px solid black; margin: 0; margin-top: 10px;">&nbsp;</p>
				</div>
				<table style="margin-top: 10mm; width: 70%;">
					<tr>
						<td style="text-align:center; width: 33.3%;">Penghitung</td>
						<td style="text-align:center; width: 33.3%;">Pencatat</td>
						<td style="text-align:center; width: 33.3%;">Checker</td>
					</tr>
					<tr>
						<td style="height: 50px;"></td>
						<td style="height: 50px;"></td>
						<td style="height: 50px;"></td>
					</tr>
					<tr>
						<td>&nbsp;</td>
						<td>&nbsp;</td>
						<td>&nbsp;</td>
					</tr>
				</table>
			</body>
		</html>
		`
		let w = window.open();
		w.document.write(html);
		w.document.close();
		w.focus();
		w.print();
	},
	short_wh(str) {
		str = str.replace("- MK", "").trim()
		if (str.length < 10) return str
		if (str.split(" ").length == 1) return str
		return str.split(" ").map(t => t[0]).join("")
	}
};

function formatNumber(num) {
	return Number.isInteger(num)
		? num.toString()
		: num.toFixed(2).replace(/\.?0+$/, '');
}