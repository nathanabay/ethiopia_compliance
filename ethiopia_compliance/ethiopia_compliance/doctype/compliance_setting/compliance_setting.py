# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class ComplianceSetting(Document):
	"""Central configuration for Ethiopian tax compliance thresholds and rates.

	All monetary thresholds and rates MUST be set here and referenced via
	frappe.get_cached_doc("Compliance Setting") — no hardcoding in logic files.
	"""

	def validate(self):
		self._validate_thresholds()

	def _validate_thresholds(self):
		"""Cross-validate that thresholds are internally consistent."""
		if self.wht_goods_threshold and self.wht_services_threshold:
			if self.wht_goods_threshold <= self.wht_services_threshold:
				frappe.throw(_("WHT Goods Threshold must be greater than Services Threshold."))

		if self.cash_limit and self.cash_limit <= 0:
			frappe.throw(_("Cash Limit must be a positive number."))

		if self.mat_rate and (self.mat_rate <= 0 or self.mat_rate > 100):
			frappe.throw(_("MAT Rate must be between 0 and 100."))

		if self.wht_rate and (self.wht_rate <= 0 or self.wht_rate > 100):
			frappe.throw(_("WHT Rate must be between 0 and 100."))

		if self.punitive_wht_rate and (self.punitive_wht_rate <= 0 or self.punitive_wht_rate > 100):
			frappe.throw(_("Punitive WHT Rate must be between 0 and 100."))