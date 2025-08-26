import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_ar_summary_by_customer(company, customer):
    """Return credit_limit & outstanding_amount saja."""
    credit_limit = flt(frappe.db.get_value(
        "Customer Credit Limit",
        {"parent": customer, "company": company},
        "credit_limit"
    ) or 0)

    res = frappe.db.get_all(
        "Sales Invoice",
        filters={"docstatus": 1, "company": company, "customer": customer},
        fields=["sum(outstanding_amount) as outstanding"],
        limit_page_length=1,
    )
    outstanding_amount = flt((res[0].get("outstanding") if res else 0) or 0)

    return {
        "credit_limit": credit_limit,
        "outstanding_amount": outstanding_amount
    }


@frappe.whitelist()
def get_ar_invoices_by_customer(company, customer):
    """
    Return daftar Sales Invoice posted (docstatus=1) dengan outstanding > 0
    dalam currency perusahaan (pakai base_*), plus ringkasan total.
    """
    company_currency = frappe.db.get_value("Company", company, "default_currency") or "IDR"

    rows = frappe.db.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "company": company,
            "customer": customer,
            "outstanding_amount": [">", 0],
        },
        fields=[
            "name",
            "posting_date",
            "base_grand_total",
            "outstanding_amount",
        ],
        order_by="posting_date desc",
        limit_page_length=500,
    )

    invoices, tot_gt, tot_paid, tot_out = [], 0.0, 0.0, 0.0
    for r in rows:
        grand_total = flt(r.base_grand_total)
        outstanding = flt(r.outstanding_amount)
        paid_amount = flt(grand_total - outstanding)

        invoices.append({
            "name": r.name,
            "posting_date": r.posting_date,
            "grand_total": grand_total,
            "paid_amount": paid_amount,
            "outstanding_amount": outstanding,
        })

        tot_gt += grand_total
        tot_paid += paid_amount
        tot_out += outstanding

    return {
        "currency": company_currency,
        "invoices": invoices,
        "totals": {
            "grand_total": tot_gt,
            "paid_amount": tot_paid,
            "outstanding_amount": tot_out,
        },
    }

import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_item_price_history(company, item_code, customer=None, limit=100):
    """
    Riwayat harga item dari Sales Invoice yang sudah submit (docstatus=1).
    Kolom yang dikembalikan dipangkas sesuai permintaan (tanpa customer, currency, price_list_rate, net_rate).
    """
    try:
        limit = int(limit or 100)
    except Exception:
        limit = 100
    limit = min(max(limit, 1), 500)  # safety: 1..500

    params = {
        "company": company,
        "item_code": item_code,
    }

    extra_customer_cond = ""
    if customer:
        extra_customer_cond = " AND si.customer = %(customer)s "
        params["customer"] = customer

    rows = frappe.db.sql(
        """
        SELECT
            si.name            AS invoice,
            si.posting_date    AS posting_date,
            sii.item_code      AS item_code,
            sii.item_name      AS item_name,
            sii.qty            AS qty,
            sii.uom            AS uom,
            sii.discount_percentage,
            sii.rate,
            sii.net_amount
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si
            ON si.name = sii.parent
        WHERE
            si.docstatus = 1
            AND si.company = %(company)s
            AND sii.item_code = %(item_code)s
            {extra_customer_cond}
        ORDER BY si.posting_date DESC, sii.idx DESC
        LIMIT {limit}
        """.format(extra_customer_cond=extra_customer_cond, limit=limit),
        params,
        as_dict=True,
    )

    return {
        "count": len(rows),
        "rows": rows,
    }

@frappe.whitelist()
def get_ap_summary_by_supplier(company, supplier):
    """
    Ringkas hutang ke supplier: hanya outstanding_amount dari Purchase Invoice (docstatus=1).
    """
    res = frappe.db.get_all(
        "Purchase Invoice",
        filters={"docstatus": 1, "company": company, "supplier": supplier},
        fields=["sum(outstanding_amount) as outstanding"],
        limit_page_length=1,
    )
    outstanding_amount = flt((res[0].get("outstanding") if res else 0) or 0)
    return {
        "outstanding_amount": outstanding_amount
    }


@frappe.whitelist()
def get_ap_invoices_by_supplier(company, supplier):
    """
    Daftar Purchase Invoice (docstatus=1) dengan outstanding > 0 untuk supplier.
    Nilai Grand Total & Outstanding pakai base_* (mata uang company).
    """
    company_currency = frappe.db.get_value("Company", company, "default_currency") or "IDR"

    rows = frappe.db.get_all(
        "Purchase Invoice",
        filters={
            "docstatus": 1,
            "company": company,
            "supplier": supplier,
            "outstanding_amount": [">", 0],
        },
        fields=[
            "name",
            "posting_date",
            "base_grand_total",
            "outstanding_amount",
        ],
        order_by="posting_date desc",
        limit_page_length=500,
    )

    invoices, tot_gt, tot_paid, tot_out = [], 0.0, 0.0, 0.0
    for r in rows:
        grand_total = flt(r.base_grand_total)
        outstanding = flt(r.outstanding_amount)
        paid_amount = flt(grand_total - outstanding)

        invoices.append({
            "name": r.name,
            "posting_date": r.posting_date,
            "grand_total": grand_total,
            "paid_amount": paid_amount,
            "outstanding_amount": outstanding,
        })

        tot_gt += grand_total
        tot_paid += paid_amount
        tot_out += outstanding

    return {
        "currency": company_currency,
        "invoices": invoices,
        "totals": {
            "grand_total": tot_gt,
            "paid_amount": tot_paid,
            "outstanding_amount": tot_out,
        },
    }


@frappe.whitelist()
def get_item_cost_history(company, item_code, supplier=None, limit=100):
    """
    Riwayat harga BELI item dari Purchase Invoice (docstatus=1, non-return).
    Kolom ramping: tanggal, no invoice, qty, uom, %disc, rate, net_amount.
    """
    try:
        limit = int(limit or 100)
    except Exception:
        limit = 100
    limit = min(max(limit, 1), 500)

    params = {
        "company": company,
        "item_code": item_code,
    }
    extra_supplier_cond = ""
    if supplier:
        extra_supplier_cond = " AND pi.supplier = %(supplier)s "
        params["supplier"] = supplier

    rows = frappe.db.sql(
        """
        SELECT
            pi.name         AS invoice,
            pi.posting_date AS posting_date,
            pii.item_code   AS item_code,
            pii.item_name   AS item_name,
            pii.qty         AS qty,
            pii.uom         AS uom,
            pii.discount_percentage,
            pii.rate,
            pii.net_amount
        FROM `tabPurchase Invoice Item` pii
        INNER JOIN `tabPurchase Invoice` pi
            ON pi.name = pii.parent
        WHERE
            pi.docstatus = 1
            AND pi.is_return = 0
            AND pi.company = %(company)s
            AND pii.item_code = %(item_code)s
            {extra_supplier_cond}
        ORDER BY pi.posting_date DESC, pii.idx DESC
        LIMIT {limit}
        """.format(extra_supplier_cond=extra_supplier_cond, limit=limit),
        params,
        as_dict=True,
    )

    return {
        "count": len(rows),
        "rows": rows,
    }