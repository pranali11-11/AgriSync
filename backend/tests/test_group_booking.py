from app.services.group_booking import calculate_group_costs


def test_worked_group_cost_example():
    result = calculate_group_costs([2, 3, 5], 1000, 1500)
    assert [member.share_paise for member in result["members"]] == [230000, 345000, 575000]
    assert result["total_paise"] == 1150000
    assert result["members"][0].solo_paise == 350000
    assert result["members"][0].savings_paise == 120000


def test_largest_remainder_rounding_in_paise():
    result = calculate_group_costs([1, 1, 1], 0, 10)
    shares = [member.share_paise for member in result["members"]]
    assert sum(shares) == 1000
    assert max(shares) - min(shares) <= 1
