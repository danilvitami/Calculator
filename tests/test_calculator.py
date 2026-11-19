import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from pydantic import ValidationError

from main import app
from app.models import (
    CreditDto,
    LoanOfferDto,
    LoanStatementRequestDto,
    ScoringDataDto,
)
from app.router import calc_credit, get_offers
from app.service import (
    add_months,
    calculate_credit,
    calculate_monthly_payment,
    calculate_rate_and_amount,
    generate_offers,
)


def get_valid_statement_data() -> dict:
    return {
        "amount": Decimal("100000"),
        "term": 12,
        "firstName": "Ivan",
        "lastName": "Ivanov",
        "middleName": "Ivanovich",
        "email": "ivan@example.com",
        "birthdate": date(1995, 5, 15),
        "passportSeries": "1234",
        "passportNumber": "567890",
    }


def get_valid_scoring_data() -> dict:
    return {
        "amount": Decimal("100000"),
        "term": 12,
        "firstName": "Ivan",
        "lastName": "Ivanov",
        "middleName": "Ivanovich",
        "birthdate": date(1995, 5, 15),
        "passportSeries": "1234",
        "passportNumber": "567890",
        "isInsuranceEnabled": True,
        "isSalaryClient": True,
    }


def test_generate_offers_returns_four_sorted_offers():
    request = LoanStatementRequestDto(**get_valid_statement_data())
    offers = generate_offers(request)

    assert len(offers) == 4
    rates = [offer.rate for offer in offers]
    assert rates == sorted(rates, reverse=True)
    assert offers[0].isInsuranceEnabled is False and offers[0].isSalaryClient is False
    assert offers[-1].isInsuranceEnabled is True and offers[-1].isSalaryClient is True


def test_calculate_rate_and_amount_combinations():
    amount = Decimal("100000")

    rate_ff, total_ff = calculate_rate_and_amount(amount, False, False)
    assert rate_ff == Decimal("15.00")
    assert total_ff == Decimal("100000.00")

    rate_ft, total_ft = calculate_rate_and_amount(amount, False, True)
    assert rate_ft == Decimal("14.00")
    assert total_ft == Decimal("100000.00")

    rate_tf, total_tf = calculate_rate_and_amount(amount, True, False)
    assert rate_tf == Decimal("12.00")
    assert total_tf == Decimal("200000.00")

    rate_tt, total_tt = calculate_rate_and_amount(amount, True, True)
    assert rate_tt == Decimal("11.00")
    assert total_tt == Decimal("200000.00")


def test_calculate_monthly_payment_zero_and_positive_rate():
    payment_zero = calculate_monthly_payment(Decimal("120000"), 12, Decimal("0"))
    assert payment_zero == Decimal("10000.00")

    payment_positive = calculate_monthly_payment(Decimal("100000"), 12, Decimal("12"))
    assert payment_positive == Decimal("8884.88")


def test_add_months_end_of_month():
    result = add_months(date(2025, 1, 31), 1)
    assert result == date(2025, 2, 28)


def test_calculate_credit_schedule_and_psk():
    data = ScoringDataDto(**get_valid_scoring_data())
    credit = calculate_credit(data)

    assert credit.amount == Decimal("200000.00")
    assert credit.term == 12
    assert credit.rate == Decimal("11.00")
    assert len(credit.paymentSchedule) == 12
    assert credit.paymentSchedule[-1].remainingDebt == Decimal("0.00")
    assert credit.psk > Decimal("0.00")


def test_validation_underage_raises_error():
    data = get_valid_statement_data()
    data["birthdate"] = date.today()
    with pytest.raises(ValidationError):
        LoanStatementRequestDto(**data)


def test_validation_invalid_email_raises_error():
    data = get_valid_statement_data()
    data["email"] = "invalid-email"
    with pytest.raises(ValidationError):
        LoanStatementRequestDto(**data)


def test_validation_small_amount_raises_error():
    data = get_valid_scoring_data()
    data["amount"] = Decimal("5000")
    with pytest.raises(ValidationError):
        ScoringDataDto(**data)


def test_router_get_offers_with_mock():
    request = LoanStatementRequestDto(**get_valid_statement_data())
    mock_offer = LoanOfferDto(
        statementId=uuid4(),
        requestedAmount=Decimal("100000.00"),
        totalAmount=Decimal("100000.00"),
        term=12,
        monthlyPayment=Decimal("9025.83"),
        rate=Decimal("15.00"),
        isInsuranceEnabled=False,
        isSalaryClient=False,
    )
    with patch("app.router.generate_offers", return_value=[mock_offer]) as mocked:
        result = get_offers(request)
        mocked.assert_called_once_with(request)
        assert len(result) == 1
        assert result[0].rate == Decimal("15.00")


def test_router_calc_credit_with_mock():
    request = ScoringDataDto(**get_valid_scoring_data())
    mock_credit = CreditDto(
        amount=Decimal("200000.00"),
        term=12,
        monthlyPayment=Decimal("17676.33"),
        rate=Decimal("11.00"),
        psk=Decimal("112.12"),
        isInsuranceEnabled=True,
        isSalaryClient=True,
        paymentSchedule=[],
    )
    with patch("app.router.calculate_credit", return_value=mock_credit) as mocked:
        result = calc_credit(request)
        mocked.assert_called_once_with(request)
        assert result.rate == Decimal("11.00")


def test_openapi_schema_contains_endpoints():
    schema = app.openapi()
    assert "/calculator/offers" in schema["paths"]
    assert "/calculator/calc" in schema["paths"]
