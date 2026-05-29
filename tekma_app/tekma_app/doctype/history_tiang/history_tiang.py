# Copyright (c) 2025, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class HistoryTiang(Document):
	def on_cancel(doc):
		if doc.document_type != "Stock Entry":
			total = get_total(doc.customer, doc.condition)
			if  total < 0.0:
				frappe.throw(f"Can't Cancel History Tiang <b>{doc.condition}</b>, is insufficient <b>{str(total)}</b>")

	def on_submit(doc):
		if doc.document_type == "Stock Entry":
			total = get_total(doc.customer, doc.condition)
			if total < 0.0:
				frappe.throw(f"Can't Submit History Tiang <b>{doc.condition}</b>, is insufficient <b>{str(total)}</b>")

def get_total(customer, condition):
	total_qty = frappe.db.sql(
        """
        SELECT COALESCE(SUM(qty), 0)
        FROM `tabHistory Tiang`
        WHERE customer = %s
          AND `condition` = %s
          AND docstatus = 1
        """,
        (customer, condition)
    )[0][0] or 0

	return total_qty