// Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
// For license information, please see license.txt

frappe.query_reports["Realized Profit"] = {
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
			fieldname: "fiscal_year",
			label: __("Fiscal Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: erpnext.utils.get_fiscal_year(
				frappe.datetime.get_today(),
				true
			)[0],
			reqd: 1,
		},
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Select",
			options: [
				{ value: "All", label: __("All Months") },
				{ value: "1", label: __("January") },
				{ value: "2", label: __("February") },
				{ value: "3", label: __("March") },
				{ value: "4", label: __("April") },
				{ value: "5", label: __("May") },
				{ value: "6", label: __("June") },
				{ value: "7", label: __("July") },
				{ value: "8", label: __("August") },
				{ value: "9", label: __("September") },
				{ value: "10", label: __("October") },
				{ value: "11", label: __("November") },
				{ value: "12", label: __("December") },
			],
			default: "All",
			reqd: 1,
		},
		{
			fieldname: "hide_zero_month",
			label: __("Hide Zero Month"),
			fieldtype: "Check",
			default: 0,
		},
	],

	onload(report) {
		report.page.wrapper
			.off("click.realized_profit", ".realized-profit-outstanding-link")
			.on(
				"click.realized_profit",
				".realized-profit-outstanding-link",
				function (e) {
					e.preventDefault();

					const $link = $(this);

					frappe.route_options = {
						company: decodeURIComponent(
							$link.attr("data-company") || ""
						),
						posting_date: [
							"between",
							[
								$link.attr("data-from-date"),
								$link.attr("data-to-date"),
							],
						],
						outstanding_amount: [">", 0],
						docstatus: 1,
						is_return: 0,
					};

					frappe.set_route("List", "Sales Invoice");
				}
			);
	},

	formatter(value, row, column, data, default_formatter) {
		let formatted = default_formatter(value, row, column, data);

		if (!data) return formatted;

		//-------------------------------------------------------
		// Outstanding Link
		//-------------------------------------------------------

		if (
			column.fieldname === "outstanding_invoice" &&
			Number(data.outstanding_invoice || 0) > 0 &&
			!data.is_total
		) {
			return `
				<a
				href="#"
				class="realized-profit-outstanding-link"
				data-company="${encodeURIComponent(data.company)}"
				data-from-date="${data.from_date}"
				data-to-date="${data.to_date}"
				>
				${formatted}
				</a>`;
		}

		if (column.fieldname === "accounting_vs_real_percentage") {
			const green =
				Number(data.accounting_vs_real_percentage || 0) > 0;

			return `<span style="
				font-weight:600;
				color:${green ? "#16a34a" : "#dc2626"};
				">
				${formatted}
				</span>`;
		}

		//-------------------------------------------------------
		// Total Row
		//-------------------------------------------------------

		if (data.is_total || data.bold) {
			return `<strong>${formatted}</strong>`;
		}

		return formatted;
	},
};