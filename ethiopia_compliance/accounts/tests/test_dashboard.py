from unittest import mock

from frappe.tests.utils import FrappeTestCase
from ethiopia_compliance.page.compliance_dashboard.compliance_dashboard import get_overview_stats, get_chart_data


class TestDashboardStats(FrappeTestCase):
    """Test dashboard overview statistics with proper isolation."""

    def test_get_overview_stats_returns_correct_structure(self):
        """Test that overview stats returns expected structure and valid counts."""
        with mock.patch("frappe.db.count") as mock_count:
            # Configure mock return values
            mock_count.side_effect = [5, 3, 12, 7]

            result = get_overview_stats("Test Company")

        assert isinstance(result, dict)
        assert "total_companies" in result
        assert "fiscal_devices" in result
        assert "employees" in result
        assert "active_contracts" in result

        # Verify all values are non-negative integers
        for key, value in result.items():
            self.assertIsInstance(value, int, f"{key} should be an integer")
            self.assertGreaterEqual(value, 0, f"{key} should be non-negative")

    def test_get_overview_stats_handles_missing_company(self):
        """Test that missing company returns zero counts."""
        with mock.patch("frappe.db.count") as mock_count:
            result = get_overview_stats("NonExistent Company")

        # Without a valid company, should return zeros
        expected = {
            'total_companies': 0,
            'fiscal_devices': 0,
            'employees': 0,
            'active_contracts': 0
        }
        self.assertEqual(result, expected)

    def test_get_overview_stats_counts_are_reasonable(self):
        """Test that counts are within reasonable bounds."""
        with mock.patch("frappe.db.count") as mock_count:
            mock_count.side_effect = [100, 50, 200, 30]

            result = get_overview_stats("Test Company")

        # Verify counts are reasonable (not excessively large)
        self.assertLessEqual(result['total_companies'], 10000, "total_companies unexpectedly large")
        self.assertLessEqual(result['fiscal_devices'], 10000, "fiscal_devices unexpectedly large")
        self.assertLessEqual(result['employees'], 100000, "employees unexpectedly large")
        self.assertLessEqual(result['active_contracts'], 10000, "active_contracts unexpectedly large")


def test_get_chart_data():
    """Test that chart data returns expected structure"""
    from ethiopia_compliance.page.compliance_dashboard.compliance_dashboard import get_chart_data

    result = get_chart_data("this_month")

    assert isinstance(result, dict)
    assert "revenue" in result
    assert "expenses" in result
    assert "cash_flow" in result
    assert "taxes" in result
    assert result["taxes"].get("wht") is not None
    assert result["taxes"].get("vat") is not None
    assert result["taxes"].get("tot") is not None
