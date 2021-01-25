from datetime import date

import pytest

from sprints.sustainability.models import (
    Budget,
    SustainabilityAccount,
)

pytestmark = pytest.mark.django_db


class TestSustainabilityAccount:
    @pytest.mark.parametrize(
        "start, end, hours, expected",
        [
            (date(2020, 1, 1), date(2020, 1, 1), 62, 2),
            (date(2020, 1, 1), date(2020, 1, 10), 62, 20),
            (date(2020, 1, 1), date(2020, 1, 31), 62, 62),
        ],
    )
    def test__calculate_partial_budget(self, start, end, hours, expected):
        assert (
            SustainabilityAccount._calculate_partial_budget(start, end, hours)
            == expected
        )

    def test__calculate_partial_budget_different_months(self):
        with pytest.raises(AttributeError):
            SustainabilityAccount._calculate_partial_budget(
                date(2020, 1, 1), date(2020, 2, 1), 0
            )

    @pytest.mark.parametrize(
        "start, end, hours, expected",
        [
            (date(2020, 1, 1), date(2020, 1, 1), 62, 2),
            (date(2020, 1, 2), date(2020, 1, 10), 62, 18),
            (date(2020, 1, 1), date(2020, 1, 10), 62, 20),
            (date(2020, 1, 1), date(2020, 1, 31), 62, 62),
            (date(2020, 1, 2), date(2020, 1, 31), 62, 60),
            (date(2020, 1, 1), date(2020, 3, 1), 62, 126),
            (date(2020, 1, 1), date(2020, 2, 29), 62, 124),
            (date(2001, 1, 1), date(2020, 12, 31), 1, 240),
            (date(2020, 1, 1), date(2020, 3, 28), 62, 180),
            (date(2020, 1, 2), date(2020, 3, 29), 62, 180),
        ],
    )
    def test__calculate_budget(self, start, end, hours, expected):
        assert SustainabilityAccount._calculate_budget(start, end, hours) == expected

    def test_calculate_budgets_none(self):
        assert (
            SustainabilityAccount("test")._calculate_budgets(
                date(2020, 1, 1), date(2020, 3, 1), []
            )
            == 0
        )

    def test__calculate_budgets(self):
        account = SustainabilityAccount("test")

        Budget.objects.create(name="test", date=date(2020, 1, 1), hours=62)
        budgets = list(Budget.objects.filter(name="test").order_by("date"))
        assert (
            account._calculate_budgets(date(2020, 1, 1), date(2020, 1, 1), budgets) == 2
        )
        assert (
            account._calculate_budgets(date(2020, 1, 1), date(2020, 3, 1), budgets)
            == 126
        )
        assert (
            account._calculate_budgets(date(2020, 2, 1), date(2020, 2, 29), budgets)
            == 62
        )

        Budget.objects.create(name="test", date=date(2020, 2, 1), hours=0)
        budgets = list(Budget.objects.filter(name="test").order_by("date"))
        assert (
            account._calculate_budgets(date(2020, 1, 1), date(2020, 3, 1), budgets)
            == 62
        )

        Budget.objects.create(name="test", date=date(2020, 3, 1), hours=62)
        budgets = list(Budget.objects.filter(name="test").order_by("date"))
        assert (
            account._calculate_budgets(date(2020, 1, 1), date(2020, 3, 1), budgets)
            == 64
        )

        Budget.objects.create(name="test", date=date(2030, 3, 1), hours=62)
        budgets = list(Budget.objects.filter(name="test").order_by("date"))
        assert (
            account._calculate_budgets(date(2001, 1, 1), date(2020, 3, 1), budgets)
            == 64
        )

        Budget.objects.create(name="test", date=date(2021, 1, 1), hours=0)
        budgets = list(Budget.objects.filter(name="test").order_by("date"))
        assert (
            account._calculate_budgets(date(2021, 1, 1), date(2021, 1, 31), budgets)
            == 0
        )

        assert (
            len(account.budgets) == 4
        ), "Only the budgets for the calculated period should be available."
