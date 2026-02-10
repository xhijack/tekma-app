import frappe
from frappe import _
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note as _make_delivery_note
from erpnext.selling.doctype.sales_order.sales_order import (make_sales_invoice as _make_sales_invoice)

@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None):
	dn = _make_delivery_note(source_name, target_doc)

	so = frappe.get_doc("Sales Order", source_name)

	if so.keterangan:
		dn.remarks = so.keterangan

	return dn

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):
	si = _make_sales_invoice(source_name, target_doc)

	so = frappe.get_doc("Sales Order", source_name)

	if so.sales:
		si.sales_team = []

		si.append("sales_team", {
			"sales_person": so.sales,
			"allocated_percentage": 100,
			"allocated_amount": si.net_total
		})

	return si

def get_total_tiang_amount(doc):
    total = 0

    for row in doc.items:
        if row.get("tiang") == "Dengan Tiang":
            qty = row.qty or 0
            rate = row.get("tiang_rate") or 0
            total += qty * rate

    return total

def before_save(doc, method):
    ACCOUNT_TIANG = "4103 - Penjualan Tiang - MK"
    expected_amount = get_total_tiang_amount(doc)

    tax_row = None
    for tax in doc.taxes:
        if tax.account_head == ACCOUNT_TIANG and tax.charge_type == "Actual":
            tax_row = tax
            break

    if expected_amount > 0:
        if not tax_row:
            tax_row = doc.append("taxes", {
                "charge_type": "Actual",
                "account_head": ACCOUNT_TIANG,
                "description": "Penjualan Tiang"
            })

        tax_row.tax_amount = expected_amount

    else:
        if tax_row:
            doc.taxes.remove(tax_row)

    doc.calculate_taxes_and_totals()

def validate(doc, method):
    ACCOUNT_TIANG = "4103 - Penjualan Tiang - MK"
    expected_amount = get_total_tiang_amount(doc)

    for tax in doc.taxes:
        if tax.account_head == ACCOUNT_TIANG and tax.charge_type == "Actual":
            if abs((tax.tax_amount or 0) - expected_amount) > 1:
                frappe.throw(
                    _("Nilai Pajak Tiang harus {0} dan tidak boleh diubah manual.")
                    .format(frappe.format_value(expected_amount, "Currency"))
                )
