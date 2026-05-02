import frappe
from frappe import _

def apply_withholding_tax(doc, method):
	"""
	Applies Withholding Tax (WHT) based on Compliance Settings.
	Hooked to Purchase Invoice before_save.
	"""
	# 1. Check if Supplier is WHT Eligible
	supplier_wht = frappe.db.get_value("Supplier", doc.supplier, "custom_wht_eligible")
	if not supplier_wht:
		return

	# 2. Fetch Compliance Settings (cached)
	settings = frappe.get_cached_doc("Compliance Setting")

	goods_threshold = settings.wht_goods_threshold or 10000
	services_threshold = settings.wht_services_threshold or 3000
	wht_rate = (settings.wht_rate or 3) / 100

	# 3. Determine Threshold - batch fetch item types in one query
	current_threshold = goods_threshold
	item_codes = list({item.item_code for item in doc.items if item.item_code})
	if item_codes:
		is_stock_map = dict(frappe.db.get_values("Item", item_codes, ["name", "is_stock_item"]))
		for item in doc.items:
			if not is_stock_map.get(item.item_code, True):
				current_threshold = services_threshold
				break

	# 4. Check for missing Supplier TIN — apply 30% penalty rate (Directive 1104/2025 Art. 8)
	PENALTY_RATE = 0.30
	penalty_applied = False
	if not doc.custom_supplier_tin or str(doc.custom_supplier_tin).strip() == "":
		wht_rate = PENALTY_RATE
		penalty_applied = True

	# 5. Apply Tax if Grand Total exceeds threshold
	if doc.grand_total >= current_threshold:
		wht_account = settings.wht_account
		if not wht_account:
			wht_account = frappe.db.get_value("Account", {
				"account_name": ["like", "%Withholding%"],
				"company": doc.company,
				"is_group": 0
			})

		if not wht_account:
			return

		# Check for duplicates
		wht_exists = any(t.account_head == wht_account for t in doc.taxes)

		if not wht_exists:
			if penalty_applied:
				desc = _("30% Penalty WHT — Missing Supplier TIN")
			else:
				desc = f"{settings.wht_rate or 3}% WHT (Threshold: {current_threshold:,.0f} ETB)"

			doc.append("taxes", {
				"charge_type": "Actual",
				"account_head": wht_account,
				"description": desc,
				"tax_amount": -(doc.total * wht_rate),
				"category": "Total",
				"add_deduct_tax": "Deduct"
			})

			doc.calculate_taxes_and_totals()
