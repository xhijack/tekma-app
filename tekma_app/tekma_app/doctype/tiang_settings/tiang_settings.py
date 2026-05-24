# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TiangSettings(Document):
    @frappe.whitelist()
    def get_series(self):
        series = frappe.get_meta("Stock Entry").get_field("naming_series")
        if series:
            return series.options