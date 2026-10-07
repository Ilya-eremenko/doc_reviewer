from app.services.new_summary_source_tables import expense_row_indices, verified_revenue_total


def test_expense_only_table_is_not_revenue_even_if_all_values_are_positive():
    rows = [
        ["Cost of Sales, mR", "2026", "2027", "2026-27 total"],
        ["Revenue", "10", "20", "30"],
    ]
    assert expense_row_indices(rows) == {0, 1}


def test_matching_total_under_cos_is_not_borrowed():
    block = {"id": "faq", "metadata": {"rows": [
        ["ToBe P&L, mR", "2026", "2027", "2026-27 total"],
        ["CoS", "10", "20", "30"],
        ["Revenue", "10", "20", "30"],
    ]}}
    assert verified_revenue_total(["2026", "2027"], ["10", "20"], [block]) is None
    block["metadata"]["rows"].insert(1, ["Revenue", "10", "20", "30"])
    assert verified_revenue_total(["2026", "2027"], ["10", "20"], [block]).value == "30"


def test_total_lookup_does_not_cross_into_another_table_or_scenario():
    block = {"id": "faq", "metadata": {"rows": [
        ["ToBe P&L, mR", "2026", "2027", "2026-27 total"],
        ["Revenue", "1", "2", "3"],
        ["CoS", "10", "20", "30"],
        ["Previous scenario", "2026", "2027", "2026-27 total"],
        ["Revenue", "10", "20", "30"],
    ]}}
    assert verified_revenue_total(["2026", "2027"], ["10", "20"], [block]) is None


def test_year_like_amounts_do_not_end_expense_section_or_block_real_revenue_total():
    rows = [
        ["ToBe P&L", "2026", "2027", "2026-27 total"],
        ["Revenue", "2026", "2027", "4053"],
        ["CoS", "2026", "2027", "4053"],
        ["Other", "2026", "2027", "4053"],
        ["Revenue", "2026", "2027", "4053"],
    ]
    assert expense_row_indices(rows) == {2, 3, 4}
    block = {"metadata": {"rows": rows}}
    assert verified_revenue_total(["2026", "2027"], ["2026", "2027"], [block]).value == "4053"
    block["metadata"]["rows"] = [rows[0], *rows[2:]]
    assert verified_revenue_total(["2026", "2027"], ["2026", "2027"], [block]) is None
