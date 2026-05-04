def test_get_overview_stats():
    """Test that overview stats returns expected structure"""
    from ethiopia_compliance.page.compliance_dashboard.compliance_dashboard import get_overview_stats

    result = get_overview_stats("Demo Company")

    assert isinstance(result, dict)
    assert "total_companies" in result
    assert "fiscal_devices" in result
    assert "employees" in result
    assert "active_contracts" in result
    assert all(isinstance(v, int) for v in result.values())
