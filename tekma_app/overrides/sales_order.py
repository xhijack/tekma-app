import frappe
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
