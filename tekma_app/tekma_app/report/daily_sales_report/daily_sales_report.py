# Copyright (c) 2025, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    if not filters:
        filters = {}

    columns = [
        {"label": "Tgl", "fieldname": "tgl", "fieldtype": "Date", "width": 120},
        {"label": "No Faktur", "fieldname": "no_faktur", "fieldtype": "Link", "options": "Sales Invoice", "width": 200},
        {"label": "ID", "fieldname": "id", "fieldtype": "Link", "options": "Customer", "width": 50},
        {"label": "Keterangan", "fieldname": "keterangan", "fieldtype": "Data", "width": 150},
        {"label": "Tunai", "fieldname": "tunai", "fieldtype": "Currency", "width": 150},
        {"label": "Bank", "fieldname": "bank", "fieldtype": "Currency", "width": 150},
        {"label": "Piutang", "fieldname": "piutang", "fieldtype": "Currency", "width": 150},
        {"label": "Jumlah", "fieldname": "jumlah", "fieldtype": "Currency", "width": 150},
        {"label": "Kasir", "fieldname": "cashier", "fieldtype": "Data", "width": 150}
    ]

    values = {}
    conditions = "si.docstatus = 1"

    if filters.get("company"):
        conditions += " AND si.company = %(company)s"
        values["company"] = filters.get("company")

    if filters.get("date"):
        conditions += " AND si.posting_date = %(date)s"
        values["date"] = filters.get("date")

    data = frappe.db.sql(f"""
        SELECT
            si.posting_date AS tgl,
            si.name AS no_faktur,
            si.customer AS id,
            si.customer_name AS keterangan,
            si.grand_total
                - SUM(
                    CASE WHEN pe.docstatus = 1 
                        AND pe.mode_of_payment = 'Bank Draft' THEN per.allocated_amount ELSE 0 END
                    )
                - SUM(
                    CASE WHEN pe.docstatus = 1 
                        AND pe.mode_of_payment = 'Cash'
                        AND TIME(pe.creation) <= '17:00:00'
                    THEN per.allocated_amount ELSE 0 END
            ) AS piutang,

            si.grand_total AS jumlah,
            SUM(CASE WHEN pe.docstatus = 1 AND pe.mode_of_payment = 'Bank Draft' THEN per.allocated_amount ELSE 0 END) AS bank,
            SUM(
                CASE WHEN pe.docstatus = 1 
                    AND pe.mode_of_payment = 'Cash'
                    AND TIME(pe.creation) <= '17:00:00'
                THEN per.allocated_amount ELSE 0 END
            ) AS tunai,

            u.full_name AS cashier
        FROM
            `tabSales Invoice` si
        LEFT JOIN
            `tabPayment Entry Reference` per ON per.reference_name = si.name
        LEFT JOIN
            `tabPayment Entry` pe ON per.parent = pe.name AND pe.docstatus = 1
        LEFT JOIN
            `tabUser` u ON u.name = si.owner
        WHERE {conditions}
        GROUP BY si.posting_date, si.name, si.customer, si.remarks
        ORDER BY si.posting_date DESC
    """, values, as_dict=True)

    return columns, data
