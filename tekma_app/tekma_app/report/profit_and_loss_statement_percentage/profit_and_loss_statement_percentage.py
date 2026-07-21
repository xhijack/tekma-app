# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

import calendar
import json
import re
from datetime import date

import frappe

from frappe import _
from frappe.utils import flt

from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import (
    execute as execute_standard_pnl,
)

from erpnext.accounts.report.financial_statements import (
    get_period_list
)


MONTH_NUMBER_PATTERN = re.compile(
    r"^(0[1-9]|1[0-2])(?:\s|$)"
)



def execute(filters=None):
    filters = frappe._dict(filters or {})

    fiscal_year = filters.get(
        "from_fiscal_year"
    )

    if not fiscal_year:
        frappe.throw(
            _("Please select Fiscal Year")
        )

    selected_month_numbers = (
        parse_selected_month_numbers(
            filters.get("months")
        )
    )

    if not selected_month_numbers:
        frappe.throw(
            _("Please select at least one month")
        )

    # Jalankan report dalam satu Fiscal Year.
    filters.filter_based_on = "Fiscal Year"
    filters.from_fiscal_year = fiscal_year
    filters.to_fiscal_year = fiscal_year
    filters.periodicity = "Monthly"
    filters.accumulated_values = 0
    filters.selected_view = "Report"

    period_list = get_period_list(
        fiscal_year,
        fiscal_year,
        None,
        None,
        "Fiscal Year",
        "Monthly",
        accumulated_values=False,
        company=filters.company,
    )

    selected_period_keys = [
        period.key
        for period in period_list
        if period.to_date.month
        in selected_month_numbers
    ]

    if not selected_period_keys:
        frappe.throw(
            _(
                "Selected months are not available "
                "in Fiscal Year {0}"
            ).format(
                frappe.bold(fiscal_year)
            )
        )

    result = list(
        execute_standard_pnl(filters)
    )

    columns = result[0] or []
    data = result[1] or []
    chart = result[3] or {}

    all_period_columns = get_period_columns(
        columns
    )

    recalculate_selected_total(
        data,
        selected_period_keys,
    )

    filter_chart(
        chart,
        all_period_columns,
        selected_period_keys,
    )

    add_account_type_column(columns)

    rebuild_columns_with_percentage(
        columns,
        data,
        selected_period_keys,
    )

    currency = (
        filters.get("presentation_currency")
        or frappe.get_cached_value(
            "Company",
            filters.company,
            "default_currency",
        )
    )

    report_summary, primitive_summary = (
        build_selected_report_summary(
            data,
            currency,
        )
    )

    result[0] = columns
    result[1] = data
    result[3] = chart
    result[4] = report_summary
    result[5] = primitive_summary

    return tuple(result)


def parse_selected_month_numbers(value):
    if not value:
        return []

    if isinstance(value, str):
        value = value.strip()

        if value.startswith("["):
            value = frappe.parse_json(value)
        else:
            value = [
                item.strip()
                for item in value.split(",")
                if item.strip()
            ]

    if not isinstance(
        value,
        (list, tuple),
    ):
        frappe.throw(
            _("Invalid Months filter")
        )

    selected_months = set()

    for month_value in value:
        month_value = str(
            month_value
        ).strip()

        match = MONTH_NUMBER_PATTERN.match(
            month_value
        )

        if not match:
            frappe.throw(
                _(
                    "Invalid month value: {0}"
                ).format(
                    frappe.bold(month_value)
                )
            )

        selected_months.add(
            int(match.group(1))
        )

    return sorted(selected_months)

def apply_standard_date_filters(filters, selected_months):
    first_year, first_month = map(
        int,
        selected_months[0].split("-"),
    )

    last_year, last_month = map(
        int,
        selected_months[-1].split("-"),
    )

    last_day = calendar.monthrange(
        last_year,
        last_month,
    )[1]

    filters.filter_based_on = "Date Range"
    filters.periodicity = "Monthly"
    filters.accumulated_values = 0
    filters.selected_view = "Report"

    filters.period_start_date = date(
        first_year,
        first_month,
        1,
    ).isoformat()

    filters.period_end_date = date(
        last_year,
        last_month,
        last_day,
    ).isoformat()


def get_period_key(year_month):
    year, month = map(
        int,
        year_month.split("-"),
    )

    month_name = calendar.month_abbr[month].lower()

    return f"{month_name}_{year}"


def get_period_columns(columns):
    return [
        column
        for column in columns
        if (
            column.get("fieldtype") == "Currency"
            and column.get("fieldname") != "total"
        )
    ]


def recalculate_selected_total(
    data,
    selected_period_keys,
):
    """
    Total P&L standar mencakup semua bulan di antara
    period_start_date dan period_end_date.

    Karena bulan MultiSelect dapat tidak berurutan,
    hitung ulang Total hanya dari bulan yang dipilih.
    """

    for row in data:
        if not row:
            continue

        row["total"] = sum(
            flt(row.get(period_key))
            for period_key in selected_period_keys
        )


def add_account_type_column(columns):
    if any(
        column.get("fieldname") == "account_type"
        for column in columns
    ):
        return

    account_index = next(
        (
            index
            for index, column in enumerate(columns)
            if column.get("fieldname") == "account"
        ),
        0,
    )

    columns.insert(
        account_index + 1,
        {
            "fieldname": "account_type",
            "label": _("Account Type"),
            "fieldtype": "Data",
            "width": 180,
        },
    )


def rebuild_columns_with_percentage(
    columns,
    data,
    selected_period_keys,
):
    selected_period_keys = set(selected_period_keys)

    total_income_row = find_total_row(
        data,
        root_type="Income",
        balance_must_be="Credit",
    )

    new_columns = []

    for column in columns:
        fieldname = column.get("fieldname")
        fieldtype = column.get("fieldtype")

        if fieldtype != "Currency":
            new_columns.append(column)
            continue

        if fieldname == "total":
            new_columns.append(column)

            new_columns.append(
                make_percentage_column(
                    fieldname="total_percentage",
                    label=f"{column.get('label')} %",
                )
            )

            continue

        if fieldname not in selected_period_keys:
            # Buang bulan di antara rentang tanggal
            # yang tidak dipilih oleh pengguna.
            continue

        new_columns.append(column)

        new_columns.append(
            make_percentage_column(
                fieldname=f"{fieldname}_percentage",
                label=f"{column.get('label')} %",
            )
        )

    columns[:] = new_columns

    if not total_income_row:
        return

    percentage_fields = list(selected_period_keys)
    percentage_fields.append("total")

    for row in data:
        if not row:
            continue

        for fieldname in percentage_fields:
            total_income = flt(
                total_income_row.get(fieldname)
            )

            amount = flt(row.get(fieldname))

            percentage_fieldname = (
                f"{fieldname}_percentage"
            )

            if total_income > 0:
                row[percentage_fieldname] = round(
                    amount / total_income * 100,
                    2,
                )
            else:
                row[percentage_fieldname] = None


def make_percentage_column(fieldname, label):
    return {
        "fieldname": fieldname,
        "label": label,
        "fieldtype": "Percent",
        "precision": 2,
        "width": 95,
    }


def find_total_row(
    data,
    root_type,
    balance_must_be,
):
    total_label = (
        "'"
        + _("Total {0} ({1})").format(
            _(root_type),
            _(balance_must_be),
        )
        + "'"
    )

    for row in data:
        if not row:
            continue

        if (
            row.get("account") == total_label
            or row.get("account_name") == total_label
        ):
            return row

    return None


def find_profit_row(data):
    profit_label = (
        "'" + _("Profit for the year") + "'"
    )

    for row in data:
        if not row:
            continue

        if (
            row.get("account") == profit_label
            or row.get("account_name") == profit_label
        ):
            return row

    return None


def filter_chart(
    chart,
    all_period_columns,
    selected_period_keys,
):
    if not chart:
        return

    chart_data = chart.get("data") or {}
    labels = chart_data.get("labels") or []
    datasets = chart_data.get("datasets") or []

    selected_period_keys = set(selected_period_keys)

    selected_indexes = [
        index
        for index, column in enumerate(
            all_period_columns
        )
        if column.get("fieldname")
        in selected_period_keys
    ]

    chart_data["labels"] = [
        labels[index]
        for index in selected_indexes
        if index < len(labels)
    ]

    for dataset in datasets:
        values = dataset.get("values") or []

        dataset["values"] = [
            values[index]
            for index in selected_indexes
            if index < len(values)
        ]


def build_selected_report_summary(
    data,
    currency,
):
    income_row = find_total_row(
        data,
        root_type="Income",
        balance_must_be="Credit",
    )

    expense_row = find_total_row(
        data,
        root_type="Expense",
        balance_must_be="Debit",
    )

    profit_row = find_profit_row(data)

    net_income = (
        flt(income_row.get("total"))
        if income_row
        else 0
    )

    net_expense = (
        flt(expense_row.get("total"))
        if expense_row
        else 0
    )

    net_profit = (
        flt(profit_row.get("total"))
        if profit_row
        else net_income - net_expense
    )

    report_summary = [
        {
            "value": net_income,
            "label": _("Total Income"),
            "datatype": "Currency",
            "currency": currency,
        },
        {
            "type": "separator",
            "value": "-",
        },
        {
            "value": net_expense,
            "label": _("Total Expense"),
            "datatype": "Currency",
            "currency": currency,
        },
        {
            "type": "separator",
            "value": "=",
            "color": "blue",
        },
        {
            "value": net_profit,
            "label": _("Net Profit"),
            "datatype": "Currency",
            "currency": currency,
            "indicator": (
                "Green"
                if net_profit > 0
                else "Red"
            ),
        },
    ]

    return report_summary, net_profit