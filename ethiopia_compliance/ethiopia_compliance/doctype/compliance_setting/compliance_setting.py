# Copyright (c) 2024, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ComplianceSetting(Document):
	def validate(self):
		"""Validate tax rates and thresholds"""
		for field, label in [
			("wht_rate", "WHT Rate"),
			("vat_rate", "VAT Rate"),
			("tot_rate", "TOT Rate"),
		]:
			val = self.get(field)
			if val is not None and (val < 0 or val > 100):
				frappe.throw(_("{0} must be between 0 and 100").format(label))

		for field, label in [
			("wht_goods_threshold", "WHT Goods Threshold"),
			("wht_services_threshold", "WHT Services Threshold"),
		]:
			val = self.get(field)
			if val is not None and val < 0:
				frappe.throw(_("{0} cannot be negative").format(label))

		if self.wht_goods_threshold and self.wht_services_threshold:
			if self.wht_services_threshold > self.wht_goods_threshold:
				frappe.throw(_("WHT Services Threshold should not exceed Goods Threshold"))
