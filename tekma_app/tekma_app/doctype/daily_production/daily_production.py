# Copyright (c) 2025, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import db


class DailyProduction(Document):
	def validate(self):
		for item in self.productions:
			item.qty_sales_order = self.get_qty_based_on_sales_order_undelivered(item.item_code)
			item.actual_qty = self.get_actul_qty_based_on_item_code_and_warehouse(item.item_code, self.warehouse)
			item.prediction_qty = item.actual_qty + item.qty_sales_order + item.qty_production
			item.sum_kg = self.calculate_ratio_item_with_prediction_qty(item.item_code, item.prediction_qty)

	def get_qty_based_on_sales_order_undelivered(self, item_code):
		sales_orders = db.get_all(
			"Sales Order",
			fields=["name"],
			filters={
				"docstatus": 1,
				"status": ["not in", ["Closed", "Completed"]],
			}
	 )

		total_qty = 0
		for so in sales_orders:
			items = db.get_all(
				"Sales Order Item",
				fields=["qty", "delivered_qty"],
				filters={
					"parent": so["name"],
					"item_code": item_code
				}
			)
			for item in items:
				undelivered_qty = item["qty"] - item.get("delivered_qty", 0)
				if undelivered_qty > 0:
					total_qty += undelivered_qty

		return total_qty

	def get_actul_qty_based_on_item_code_and_warehouse(self, item_code, warehouse):
		actual_qty = db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty")
		return actual_qty or 0

	def calculate_ratio_item_with_prediction_qty(self, item_code, prediction_qty):
		item = frappe.get_doc("Item", item_code)
		if item.ratio == 0:
			frappe.throw
		return item.ratio * prediction_qty if item.ratio else 0