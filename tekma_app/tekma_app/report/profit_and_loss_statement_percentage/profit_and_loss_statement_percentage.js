// Copyright (c) 2026
// License: GNU General Public License v3

const REPORT_NAME = "Profit and Loss Statement Percentage";

const report = $.extend(
	true,
	{},
	erpnext.financial_statements
);

function update_filter(fieldname, properties) {
	const filter = report.filters.find(
		(row) => row.fieldname === fieldname
	);

	if (filter) {
		Object.assign(filter, properties);
	}

	return filter;
}

async function get_month_options(txt = "") {
	const fiscal_year =
		frappe.query_report.get_filter_value(
			"from_fiscal_year"
		);

	if (!fiscal_year) {
		return [];
	}

	const response = await frappe.db.get_value(
		"Fiscal Year",
		fiscal_year,
		[
			"year_start_date",
			"year_end_date",
		]
	);

	const fiscal_year_data = response.message;

	if (
		!fiscal_year_data?.year_start_date ||
		!fiscal_year_data?.year_end_date
	) {
		return [];
	}

	const keyword = String(txt)
		.trim()
		.toLowerCase();

	const start = moment(
		fiscal_year_data.year_start_date
	).startOf("month");

	const end = moment(
		fiscal_year_data.year_end_date
	).startOf("month");

	const options = [];
	const cursor = start.clone();

	while (cursor.isSameOrBefore(end, "month")) {
		const month_number = cursor.format("MM");
		const month_name = cursor.format("MMMM");
		const year = cursor.format("YYYY");

		/*
		 * Prefix angka digunakan agar backend tidak bergantung
		 * pada bahasa bulan:
		 *
		 * 05 - Mei
		 * 06 - Juni
		 */
		const value =
			`${month_number} - ${month_name}`;

		const searchable_text =
			`${value} ${year}`.toLowerCase();

		if (
			!keyword ||
			searchable_text.includes(keyword)
		) {
			options.push({
				value,
				description: year,
			});
		}

		cursor.add(1, "month");
	}

	return options;
}

/*
 * Gunakan Fiscal Year, bukan Date Range.
 */
update_filter("filter_based_on", {
	default: "Fiscal Year",
	hidden: 1,
	reqd: 0,
	on_change: null,
});

/*
 * Fiscal Year awal dijadikan satu-satunya
 * filter tahun yang terlihat.
 */
update_filter("from_fiscal_year", {
	label: __("Fiscal Year"),
	hidden: 0,
	reqd: 1,
	depends_on: null,
	mandatory_depends_on: null,

	on_change() {
		const fiscal_year =
			frappe.query_report.get_filter_value(
				"from_fiscal_year"
			);

		/*
		 * Report standar membutuhkan Start Year
		 * dan End Year. Keduanya dibuat sama.
		 *
		 * Bulan dikosongkan karena daftar bulan
		 * harus mengikuti Fiscal Year yang baru.
		 */
		frappe.query_report.set_filter_value({
			to_fiscal_year: fiscal_year,
			months: [],
		});
	},
});

update_filter("to_fiscal_year", {
	hidden: 1,
	reqd: 1,
	depends_on: null,
	mandatory_depends_on: null,
});

update_filter("period_start_date", {
	hidden: 1,
	reqd: 0,
	depends_on: null,
	mandatory_depends_on: null,
});

update_filter("period_end_date", {
	hidden: 1,
	reqd: 0,
	depends_on: null,
	mandatory_depends_on: null,
});

update_filter("periodicity", {
	default: "Monthly",
	options: ["Monthly"],
	hidden: 1,
	reqd: 0,
});

/*
 * Tambahkan Months setelah Fiscal Year.
 */
const fiscal_year_index =
	report.filters.findIndex(
		(row) =>
			row.fieldname === "from_fiscal_year"
	);

const current_month = moment();

report.filters.splice(
	fiscal_year_index + 1,
	0,
	{
		fieldname: "months",
		label: __("Months"),
		fieldtype: "MultiSelectList",
		reqd: 1,

		default: [
			`${current_month.format("MM")} - ` +
			current_month.format("MMMM"),
		],

		get_data(txt) {
			return get_month_options(txt);
		},
	}
);

frappe.query_reports[REPORT_NAME] = report;

/*
 * Tetap gunakan Accounting Dimensions bawaan.
 */
erpnext.utils.add_dimensions(
	REPORT_NAME,
	10
);

report.filters.push(
	{
		fieldname: "selected_view",
		label: __("Select View"),
		fieldtype: "Select",
		options: [
			{
				value: "Report",
				label: __("Report View"),
			},
		],
		default: "Report",
		hidden: 1,
		reqd: 1,
	},
	{
		fieldname: "accumulated_values",
		label: __("Accumulated Values"),
		fieldtype: "Check",
		default: 0,
		hidden: 1,
	},
	{
		fieldname:
			"include_default_book_entries",
		label: __("Include Default FB Entries"),
		fieldtype: "Check",
		default: 1,
	},
	{
		fieldname: "show_zero_values",
		label: __("Show zero values"),
		fieldtype: "Check",
		default: 0,
	}
);