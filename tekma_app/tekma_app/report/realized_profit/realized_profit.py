# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, add_months, flt, formatdate, get_first_day, getdate


ALL_MONTHS = "All"


def execute(filters=None):
    filters = frappe._dict(filters or {})
    set_defaults(filters)
    validate_filters(filters)

    currency = frappe.get_cached_value("Company", filters.company, "default_currency")
    precision = frappe.get_precision("GL Entry", "debit") or 2

    fiscal_year = frappe.db.get_value(
        "Fiscal Year",
        filters.fiscal_year,
        ["year_start_date", "year_end_date"],
        as_dict=True,
    )
    if not fiscal_year:
        frappe.throw(_("Fiscal Year {0} was not found").format(filters.fiscal_year))

    periods = get_month_periods(
        fiscal_year.year_start_date,
        fiscal_year.year_end_date,
        filters.month,
    )

    if not periods:
        return get_columns(), []

    from_date = periods[0].from_date
    to_date = periods[-1].to_date

    profit_and_loss = get_profit_and_loss(filters.company, from_date, to_date)
    actual_receipts = get_actual_receipts(filters.company, from_date, to_date)
    outstanding_invoices = get_outstanding_invoices(filters.company, from_date, to_date)

    data = []
    for period in periods:
        key = (period.from_date.year, period.from_date.month)
        pnl = profit_and_loss.get(key, frappe._dict())

        income = flt(pnl.get("income"), precision)
        expense = flt(pnl.get("expense"), precision)
        actual_receipt = flt(actual_receipts.get(key), precision)
        outstanding_invoice = flt(outstanding_invoices.get(key), precision)

        collection_ratio = flt((actual_receipt / income * 100) if income else 0, 2)
        accounting_profit = flt(income - expense, precision)
        realized_profit = flt(actual_receipt - expense, precision)
        accounting_vs_real_percentage = get_accounting_vs_real_percentage(
            accounting_profit,
            realized_profit,
        )

        data.append(
            frappe._dict(
                month=formatdate(period.from_date, "MMMM yyyy"),
                month_no=period.from_date.month,
                from_date=period.from_date,
                to_date=period.to_date,
                company=filters.company,
                income=income,
                expense=expense,
                actual_receipt=actual_receipt,
                collection_ratio=collection_ratio,
                accounting_profit=accounting_profit,
                realized_profit=realized_profit,
                accounting_vs_real_percentage=accounting_vs_real_percentage,
                outstanding_invoice=outstanding_invoice,
                currency=currency,
            )
        )
    if filters.get("hide_zero_month"):
        data = [
            row
            for row in data
            if any(
                flt(row.get(fieldname), precision) != 0
                for fieldname in (
                    "income",
                    "expense",
                    "actual_receipt",
                    "accounting_profit",
                    "realized_profit",
                    "outstanding_invoice",
                )
            )
        ]

    if filters.month == ALL_MONTHS and data:
        data.append(get_total_row(data, currency, precision))

    return (
        get_columns(),
        data,
        None,
        None,
        get_report_summary(data, currency, precision),
        1,
    )


def get_accounting_vs_real_percentage(accounting_profit, realized_profit):
    """Return realized profit as a percentage of accounting profit.

    The percentage is mathematically meaningful when accounting profit is non-zero.
    For a zero accounting profit, return 100% only when both profits are zero; otherwise
    return 0% to avoid an infinite or misleading percentage.
    """

    accounting_profit = flt(accounting_profit)
    realized_profit = flt(realized_profit)

    if accounting_profit:
        return flt(realized_profit / accounting_profit * 100, 2)
    return 0.0


def set_defaults(filters):
    filters.company = filters.get("company") or frappe.defaults.get_user_default("Company")

    if not filters.get("fiscal_year"):
        filters.fiscal_year = frappe.defaults.get_user_default("fiscal_year")

    if not filters.get("fiscal_year"):
        filters.fiscal_year = frappe.db.get_value(
            "Fiscal Year",
            {"year_start_date": ["<=", frappe.utils.today()], "year_end_date": [">=", frappe.utils.today()]},
            "name",
        )

    filters.month = filters.get("month") or ALL_MONTHS


def validate_filters(filters):
    if not filters.company:
        frappe.throw(_("Company is required"))

    if not filters.fiscal_year:
        frappe.throw(_("Fiscal Year is required"))

    if filters.month != ALL_MONTHS:
        try:
            month = int(filters.month)
        except (TypeError, ValueError):
            frappe.throw(_("Invalid month"))

        if month < 1 or month > 12:
            frappe.throw(_("Invalid month"))


def get_month_periods(year_start_date, year_end_date, selected_month):
    year_start_date = getdate(year_start_date)
    year_end_date = getdate(year_end_date)

    periods = []
    cursor = get_first_day(year_start_date)

    while cursor <= year_end_date:
        next_month = add_months(cursor, 1)
        period_from = max(cursor, year_start_date)
        period_to = min(add_days(next_month, -1), year_end_date)

        if selected_month == ALL_MONTHS or cursor.month == int(selected_month):
            periods.append(
                frappe._dict(
                    from_date=getdate(period_from),
                    to_date=getdate(period_to),
                )
            )

        cursor = next_month

    return periods


def get_profit_and_loss(company, from_date, to_date):
    rows = frappe.db.sql(
        """
        SELECT
            YEAR(gle.posting_date) AS year,
            MONTH(gle.posting_date) AS month,
            SUM(
                CASE
                    WHEN account.root_type = 'Income'
                    THEN gle.credit - gle.debit
                    ELSE 0
                END
            ) AS income,
            SUM(
                CASE
                    WHEN account.root_type = 'Expense'
                    THEN gle.debit - gle.credit
                    ELSE 0
                END
            ) AS expense
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` account
            ON account.name = gle.account
        WHERE
            gle.company = %(company)s
            AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND gle.is_cancelled = 0
            AND gle.voucher_type != 'Period Closing Voucher'
            AND account.report_type = 'Profit and Loss'
            AND account.root_type IN ('Income', 'Expense')
        GROUP BY YEAR(gle.posting_date), MONTH(gle.posting_date)
        """,
        {
            "company": company,
            "from_date": from_date,
            "to_date": to_date,
        },
        as_dict=True,
    )

    return {
        (row.year, row.month): frappe._dict(
            income=flt(row.income),
            expense=flt(row.expense),
        )
        for row in rows
    }


def get_actual_receipts(company, from_date, to_date):
    """Return real cash/bank receipts from customers, grouped by posting month."""

    rows = frappe.db.sql(
        """
        SELECT
            YEAR(receipt.posting_date) AS year,
            MONTH(receipt.posting_date) AS month,
            SUM(receipt.amount) AS amount
        FROM (
            SELECT
                pe.posting_date,
                CASE
                    WHEN pe.payment_type = 'Receive' THEN pe.base_received_amount
                    WHEN pe.payment_type = 'Pay' THEN -pe.base_paid_amount
                    ELSE 0
                END AS amount
            FROM `tabPayment Entry` pe
            WHERE
                pe.company = %(company)s
                AND pe.docstatus = 1
                AND pe.posting_date BETWEEN %(from_date)s AND %(to_date)s
                AND pe.party_type = 'Customer'
                AND (
                    (
                        pe.payment_type = 'Receive'
                        AND pe.paid_to_account_type IN ('Cash', 'Bank')
                    )
                    OR
                    (
                        pe.payment_type = 'Pay'
                        AND pe.paid_from_account_type IN ('Cash', 'Bank')
                    )
                )

            UNION ALL

            SELECT
                pos.posting_date,
                CASE
                    WHEN pos.is_return = 1
                    THEN -ABS(IFNULL(pos.base_paid_amount, 0) - IFNULL(pos.base_change_amount, 0))
                    ELSE ABS(IFNULL(pos.base_paid_amount, 0) - IFNULL(pos.base_change_amount, 0))
                END AS amount
            FROM `tabPOS Invoice` pos
            WHERE
                pos.company = %(company)s
                AND pos.docstatus = 1
                AND pos.posting_date BETWEEN %(from_date)s AND %(to_date)s

            UNION ALL

            SELECT
                si.posting_date,
                CASE
                    WHEN si.is_return = 1
                    THEN -ABS(IFNULL(si.base_paid_amount, 0) - IFNULL(si.base_change_amount, 0))
                    ELSE ABS(IFNULL(si.base_paid_amount, 0) - IFNULL(si.base_change_amount, 0))
                END AS amount
            -- Compatibility for legacy POS transactions created directly as Sales Invoice.
            -- ERPNext v15 POS Invoice transactions are counted by the POS Invoice branch above.
            -- Consolidated Sales Invoices are excluded to prevent counting the same POS cash twice.
            FROM `tabSales Invoice` si
            WHERE
                si.company = %(company)s
                AND si.docstatus = 1
                AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
                AND si.is_pos = 1
                AND IFNULL(si.is_consolidated, 0) = 0
                AND ABS(IFNULL(si.base_paid_amount, 0) - IFNULL(si.base_change_amount, 0)) > 0


            UNION ALL

            SELECT
                bank_gl.posting_date,
                SUM(bank_gl.debit - bank_gl.credit) AS amount
            FROM `tabGL Entry` bank_gl
            INNER JOIN `tabAccount` bank_account
                ON bank_account.name = bank_gl.account
            WHERE
                bank_gl.company = %(company)s
                AND bank_gl.is_cancelled = 0
                AND bank_gl.voucher_type = 'Journal Entry'
                AND bank_gl.posting_date BETWEEN %(from_date)s AND %(to_date)s
                AND bank_account.account_type IN ('Cash', 'Bank')
                AND EXISTS (
                    SELECT 1
                    FROM `tabGL Entry` customer_gl
                    WHERE
                        customer_gl.company = bank_gl.company
                        AND customer_gl.voucher_type = bank_gl.voucher_type
                        AND customer_gl.voucher_no = bank_gl.voucher_no
                        AND customer_gl.is_cancelled = 0
                        AND customer_gl.party_type = 'Customer'
                        AND IFNULL(customer_gl.party, '') != ''
                )
            GROUP BY bank_gl.posting_date, bank_gl.voucher_no
        ) receipt
        GROUP BY YEAR(receipt.posting_date), MONTH(receipt.posting_date)
        """,
        {
            "company": company,
            "from_date": from_date,
            "to_date": to_date,
        },
        as_dict=True,
    )

    return {(row.year, row.month): flt(row.amount) for row in rows}


def get_outstanding_invoices(company, from_date, to_date):
    """Return current outstanding of invoices posted in each report month."""

    rows = frappe.db.sql(
        """
        SELECT
            YEAR(si.posting_date) AS year,
            MONTH(si.posting_date) AS month,
            SUM(
                GREATEST(IFNULL(si.outstanding_amount, 0), 0)
                * IFNULL(NULLIF(si.conversion_rate, 0), 1)
            ) AS outstanding_invoice
        FROM `tabSales Invoice` si
        WHERE
            si.company = %(company)s
            AND si.docstatus = 1
            AND si.is_return = 0
            AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND si.outstanding_amount > 0
        GROUP BY YEAR(si.posting_date), MONTH(si.posting_date)
        """,
        {
            "company": company,
            "from_date": from_date,
            "to_date": to_date,
        },
        as_dict=True,
    )

    return {(row.year, row.month): flt(row.outstanding_invoice) for row in rows}


def get_total_row(data, currency, precision):
    detail_rows = [row for row in data if not row.get("is_total")]

    income = flt(sum(row.income for row in detail_rows), precision)
    expense = flt(sum(row.expense for row in detail_rows), precision)
    actual_receipt = flt(sum(row.actual_receipt for row in detail_rows), precision)
    accounting_profit = flt(income - expense, precision)
    realized_profit = flt(actual_receipt - expense, precision)
    accounting_vs_real_percentage = get_accounting_vs_real_percentage(
        accounting_profit,
        realized_profit,
    )
    outstanding_invoice = flt(sum(row.outstanding_invoice for row in detail_rows), precision)

    return frappe._dict(
        month=_("Total"),
        income=income,
        expense=expense,
        actual_receipt=actual_receipt,
        collection_ratio=flt((actual_receipt / income * 100) if income else 0, 2),
        accounting_profit=accounting_profit,
        realized_profit=realized_profit,
        accounting_vs_real_percentage=accounting_vs_real_percentage,
        outstanding_invoice=outstanding_invoice,
        currency=currency,
        is_total=1,
        bold=1,
    )


def get_columns():
    return [
        {
            "fieldname": "month",
            "label": _("Month"),
            "fieldtype": "Data",
            "width": 145,
        },
        {
            "fieldname": "income",
            "label": _("Income"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 145,
        },
        {
            "fieldname": "expense",
            "label": _("Expense"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 145,
        },
        {
            "fieldname": "actual_receipt",
            "label": _("Actual Receipt"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 155,
        },
        {
            "fieldname": "collection_ratio",
            "label": _("Collection Ratio"),
            "fieldtype": "Percent",
            "width": 135,
        },
        {
            "fieldname": "accounting_profit",
            "label": _("Accounting Profit"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 165,
        },
        {
            "fieldname": "realized_profit",
            "label": _("Realized Profit"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 155,
        },
        {
            "fieldname": "accounting_vs_real_percentage",
            "label": _("Real vs Accounting %"),
            "fieldtype": "Percent",
            "width": 175,
        },
        {
            "fieldname": "outstanding_invoice",
            "label": _("Outstanding Invoice"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 175,
        },
    ]


def get_report_summary(data, currency, precision):
    detail_rows = [row for row in data if not row.get("is_total")]
    if not detail_rows:
        return []

    income = flt(sum(row.income for row in detail_rows), precision)
    expense = flt(sum(row.expense for row in detail_rows), precision)
    actual_receipt = flt(sum(row.actual_receipt for row in detail_rows), precision)
    accounting_profit = flt(income - expense, precision)
    realized_profit = flt(actual_receipt - expense, precision)
    outstanding_invoice = flt(sum(row.outstanding_invoice for row in detail_rows), precision)

    return [
        {
            "value": income,
            "indicator": "Blue",
            "label": _("Income"),
            "datatype": "Currency",
            "currency": currency,
        },
        {
            "value": actual_receipt,
            "indicator": "Green",
            "label": _("Actual Receipt"),
            "datatype": "Currency",
            "currency": currency,
        },
        {
            "value": accounting_profit,
            "indicator": "Green" if accounting_profit >= 0 else "Red",
            "label": _("Accounting Profit"),
            "datatype": "Currency",
            "currency": currency,
        },
        {
            "value": realized_profit,
            "indicator": "Green" if realized_profit >= accounting_profit else "Red",
            "label": _("Realized Profit"),
            "datatype": "Currency",
            "currency": currency,
        },
        {
            "value": outstanding_invoice,
            "indicator": "Orange" if outstanding_invoice > 0 else "Green",
            "label": _("Outstanding Invoice"),
            "datatype": "Currency",
            "currency": currency,
        },
    ]
