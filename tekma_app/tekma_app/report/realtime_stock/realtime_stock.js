// Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
// For license information, please see license.txt

frappe.query_reports["Realtime Stock"] = {

	// STATE
	last_update_time: null,
	auto_refresh_interval: null,
	is_tab_active: true,

	filters: [
		{
			fieldname: "item",
			label: __("Item"),
			fieldtype: "MultiSelectList",
			get_data: (q) => frappe.db.get_link_options("Item", q)
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "MultiSelectList",
			get_data: (q) => frappe.db.get_link_options("Item Group", q)
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "MultiSelectList",
			get_data: (q) => frappe.db.get_link_options("Warehouse", q)
		},
		{
			fieldname: "picked_stock",
			label: __("Show Reserved Stock"),
			fieldtype: "Check"
		},
		{
			fieldname: "disabled_batch",
			label: __("Include Disabled Batch"),
			fieldtype: "Check"
		},
		{
			fieldname: "disabled_item",
			label: __("Include Disabled Item"),
			fieldtype: "Check"
		},
		{
			fieldname: "ignore_empty_stock",
			label: __("Ignore Empty Stock"),
			fieldtype: "Check",
			default: 1
		},
		{
			fieldname: "summary",
			label: __("Summary"),
			fieldtype: "Check"
		},
	],

	after_datatable_render(){
		this.last_update_time = Date.now()
		this.update_indicator()
	},

	onload(report) {
		this.report = report;

		report.page.set_indicator(__("Loading..."), "orange");

		this.init_auto_refresh();
		this.init_tab_visibility_handler();

		report.page.add_inner_button(__("Clear Filters"), () => {
			report.filters.forEach(f => {
				if (!f.df.read_only) f.set_value(null);
			});
			this.refresh_report();
		});

		report.page.add_inner_button(__("Print"), () => {
			this.print_opname(false);
		});

		report.page.add_inner_button(__("Print Summarize"), () => {
			this.print_opname(true);
		});
	},

	// TAB VISIBILITY CONTROL
	init_tab_visibility_handler() {
		let me = this;

		document.addEventListener("visibilitychange", function () {
			me.is_tab_active = !document.hidden;

			if (!me.is_tab_active) {
				frappe.query_report.page.set_indicator(
					__("Paused (Tab Hidden)"),
					"orange"
				);
			} else {
				me.update_indicator();
			}
		});
	},

	// AUTO REFRESH
	init_auto_refresh() {
		if (this.auto_refresh_interval) {
			clearInterval(this.auto_refresh_interval);
		}

		this.auto_refresh_interval = setInterval(() => {
			if(frappe.get_route(1) != "Realtime Stock")
			if (!this.report) return;

			// pause jika tab tidak aktif
			if (!this.is_tab_active) return;

			if (!this.last_update_time) {
				this.refresh_report();
				return;
			}

			const now = Date.now();
			const diff = now - this.last_update_time;

			if (diff >= 30000) {
				this.refresh_report();
			}
		}, 5000);
	},

	refresh_report() {
		this.last_update_time = Date.now();

		if (frappe.query_report?.refresh) {
			frappe.query_report.refresh();
		}

		this.update_indicator();
	},

	update_indicator() {
		const formatted = new Date().toLocaleTimeString('id-ID', {
			hour: '2-digit',
			minute: '2-digit',
			second: '2-digit'
		});

		frappe.query_report.page.set_indicator(
			__(`Refreshed at: ${formatted}`),
			"blue"
		);
	},

	// PRINT
	print_opname(summarize) {
		const filters = this.report.get_values();
		const me = this;

		frappe.call({
			method: 'frappe.desk.query_report.run',
			args: {
				report_name: 'Realtime Stock',
				filters
			},
			callback({ message }) {
				if (message) {
					const grouped = me.grouping_stock(message.result);
					me.make_html(grouped, summarize);
				}
			}
		});
	},

	// GROUPING
	grouping_stock(data) {
		if (!Array.isArray(data)) return [];

		const groupedMap = data.reduce((acc, row) => {
			if (!row || !row.item_code || Array.isArray(row)) return acc;

			const key = `${row.item_code}||${row.parent_warehouse}`;

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
				stock_uom: row.stock_uom
			});

			return acc;
		}, {});

		return Object.values(groupedMap);
	},

	// HTML PRINT
	make_html(stocks, summarize) {
		const rows = stocks.map(group => {

			const parent_row = `
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

			const child_rows = group.children.map(child => `
				<tr class="${group.children.length == 1 ? 'bold' : ''}">
					<td>${group.children.length == 1 ? group.item_name : ""}</td>
					<td>${this.short_wh(child.warehouse)}</td>
					<td>${summarize ? "-" : (child.batch_no || "-")}</td>
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

		const filters = this.report?.get_values() || {};
		const date = new Date();

		let title = `Opname ${filters.item_group || ""} ${date.toLocaleString('id-ID', { month: 'long' })} ${date.getFullYear()}`;
		title = (summarize ? "(Summary) " : "(Batch) ") + title;

		if (filters.warehouse) title += ` - ${filters.warehouse}`;

		const html = `
		<html>
		<head>
			<style>
				@page { size: A4 portrait; margin: 10mm; }
				* { font-size: 12px; }
				body { font-family: Arial; text-align: center; }
				table { border-collapse: collapse; width: 100%; }
				th, td { border: 1px solid #000; padding: 4px; font-size: 11px; }
				tr.bold td { font-weight: bold; }
			</style>
		</head>
		<body>
			<h2>${title}</h2>

			<table>
				<thead>
					<tr>
						<th>Item</th>
						<th>Warehouse</th>
						<th>Batch</th>
						<th>Qty</th>
						<th>UoM</th>
						<th>Qty Real</th>
						<th>Selisih</th>
					</tr>
				</thead>
				<tbody>${rows}</tbody>
			</table>
		</body>
		</html>`;

		const w = window.open();
		w.document.write(html);
		w.document.close();
		w.focus();
		w.print();
	},

	short_wh(str = "") {
		str = str.replace("- MK", "").trim();
		if (str.length < 10) return str;
		if (str.split(" ").length === 1) return str;
		return str.split(" ").map(t => t[0]).join("");
	}
};

function formatNumber(num) {
	return Number.isInteger(num)
		? num.toString()
		: num.toFixed(2).replace(/\.?0+$/, '');
}