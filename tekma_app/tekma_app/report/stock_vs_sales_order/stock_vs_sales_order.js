// Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
// For license information, please see license.txt

const DEFAULT_ITEM_GROUPS = ["FG", "MD"];

window.open_stock_vs_sales_order_list = function (encoded_sales_orders) {
	let sales_orders = [];

	try {
		sales_orders = JSON.parse(
			decodeURIComponent(encoded_sales_orders)
		);
	} catch (error) {
		console.error(error);
		frappe.msgprint(__("Unable to read Sales Order filter."));
		return;
	}

	if (!Array.isArray(sales_orders) || !sales_orders.length) {
		frappe.msgprint(__("No Sales Order found."));
		return;
	}

	frappe.route_options = {
		name: ["in", sales_orders],
	};

	frappe.set_route("List", "Sales Order");
};

function make_sales_order_link(content, sales_orders, title = "") {
	if (!Array.isArray(sales_orders) || !sales_orders.length) {
		return content;
	}

	const encoded_sales_orders = encodeURIComponent(
		JSON.stringify(sales_orders)
	);

	const safe_title = frappe.utils.escape_html(
		title || __("Open Sales Orders")
	);

	return `
		<a
			href="#"
			style="
				display:block;
				color:inherit;
				text-decoration:none;
			"
			title="${safe_title}"
			onclick="
				window.open_stock_vs_sales_order_list(
					'${encoded_sales_orders}'
				);
				return false;
			"
		>
			${content}
		</a>
	`;
}

frappe.query_reports["Stock vs Sales Order"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(
				frappe.datetime.get_today(),
				2
			),
			reqd: 1,
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "MultiSelectList",
			default: DEFAULT_ITEM_GROUPS,
			get_data(txt) {
				return frappe.db.get_link_options(
					"Item Group",
					txt
				);
			},
		},
		{
			fieldname: "item",
			label: __("Item"),
			fieldtype: "MultiSelectList",
			get_data(txt) {
				return frappe.db.get_link_options(
					"Item",
					txt,
					{
						is_stock_item: 1,
						disabled: 0,
					}
				);
			},
		},
		{
			fieldname: "hide_no_order_item",
			label: __("Hide No Order Item"),
			fieldtype: "Check",
			default: 1,
		},
	],
	onload: function(report) {
		let item_group_filter = report.get_filter('item_group'); // ('feild name')
		if (item_group_filter && (!item_group_filter.get_value() || item_group_filter.get_value().length === 0)) {
			item_group_filter.set_value(DEFAULT_ITEM_GROUPS);
		}
	},

	formatter(
		value,
		row,
		column,
		data,
		default_formatter
	) {
		const formatted = default_formatter(
			value,
			row,
			column,
			data
		);

		if (!data || !column.fieldname) {
			return formatted;
		}

		const numeric_value = flt(value);

		if (column.fieldname === "total_so") {
			if (!numeric_value) {
				return formatted;
			}

			const sales_orders = data.sales_orders || [];

			const content = `
				<span
					style="
						display:block;
						color:var(--text-color);
						font-weight:700;
						text-align:right;
						text-decoration:underline;
					"
				>
					${formatted}
				</span>
			`;

			return make_sales_order_link(
				content,
				sales_orders,
				__(
					"Open {0} Sales Orders",
					[sales_orders.length]
				)
			);
		}

		if (column.fieldname.startsWith("date_")) {
			if (!numeric_value) {
				return "";
			}

			const running_balance = flt(
				data[
					`${column.fieldname}_balance`
				]
			);

			const sales_orders =
				data[
					`${column.fieldname}_sales_orders`
				] || [];

			const balance_label = format_number(
				running_balance,
				null,
				2
			);

			const sales_order_label = __(
				"{0} Sales Order(s)",
				[sales_orders.length]
			);

			let style = [
				"display:block",
				"font-weight:600",
				"text-align:right",
				"padding:2px 5px",
				"border-radius:4px",
			].join(";");

			if (running_balance < 0) {
				style += [
					";background:#ffe3e3",
					"color:#c92a2a",
				].join(";");
			} else if (
				Math.abs(running_balance) < 0.000001
			) {
				style += [
					";background:#fff3bf",
					"color:#a15c00",
				].join(";");
			}

			const content = `
				<span style="${style}">
					${formatted}
				</span>
			`;

			return make_sales_order_link(
				content,
				sales_orders,
				`${sales_order_label} · ${__(
					"Running Balance"
				)}: ${balance_label}`
			);
		}

		if (
			column.fieldname === "balance"
			&& numeric_value < 0
		) {
			return `
				<span
					style="
						color:#c92a2a;
						font-weight:700;
					"
				>
					${formatted}
				</span>
			`;
		}

		if (
			column.fieldname === "shortage_qty"
			&& numeric_value > 0
		) {
			return `
				<span
					style="
						display:block;
						background:#ffe3e3;
						color:#c92a2a;
						font-weight:700;
						text-align:right;
						padding:2px 5px;
						border-radius:4px;
					"
				>
					${formatted}
				</span>
			`;
		}

		return formatted;
	},
};