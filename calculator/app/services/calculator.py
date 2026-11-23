import calendar
import logging
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from fastapi import HTTPException

from app.core.config import BASE_RATE, INSURANCE_COST, INSURANCE_DISCOUNT, SALARY_DISCOUNT
from app.schemas.models import (
    CreditDto,
    LoanOfferDto,
    LoanStatementRequestDto,
    PaymentScheduleElementDto,
    ScoringDataDto,
)

logger = logging.getLogger("calculator")

MIN_AGE = 20
MAX_AGE = 65
MAX_TERM = 120
MAX_AMOUNT = Decimal("30000000")


def round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def add_months(start_date: date, months: int) -> date:
    month = start_date.month - 1 + months
    year = start_date.year + month // 12
    month = month % 12 + 1
    day = min(start_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def get_age(birthdate: date, current_date: date) -> int:
    age = current_date.year - birthdate.year
    if (current_date.month, current_date.day) < (birthdate.month, birthdate.day):
        age -= 1
    return age


def prescore_request(amount: Decimal, term: int, birthdate: date) -> None:
    today = date.today()
    age = get_age(birthdate, today)
    age_at_loan_end = get_age(birthdate, add_months(today, term))

    if age < MIN_AGE:
        raise HTTPException(status_code=400, detail="Prescoring failed: age must be at least 20 years")
    if age_at_loan_end > MAX_AGE:
        raise HTTPException(status_code=400, detail="Prescoring failed: age at loan end must be 65 years or less")
    if term > MAX_TERM:
        raise HTTPException(status_code=400, detail="Prescoring failed: term must be 120 months or less")
    if amount > MAX_AMOUNT:
        raise HTTPException(status_code=400, detail="Prescoring failed: amount must be 30000000 or less")


def calculate_rate_and_amount(
    requested_amount: Decimal, is_insurance_enabled: bool, is_salary_client: bool
) -> tuple[Decimal, Decimal]:
    rate = BASE_RATE
    total_amount = requested_amount

    if is_insurance_enabled:
        rate -= INSURANCE_DISCOUNT
        total_amount += INSURANCE_COST

    if is_salary_client:
        rate -= SALARY_DISCOUNT

    logger.info(
        f"Calculated rate={rate} and total_amount={total_amount} "
        f"(insurance={is_insurance_enabled}, salary={is_salary_client})"
    )
    return round_money(rate), round_money(total_amount)


def calculate_monthly_payment(total_amount: Decimal, term: int, rate: Decimal) -> Decimal:
    monthly_rate = (rate / Decimal("100")) / Decimal("12")
    if monthly_rate == 0:
        return round_money(total_amount / Decimal(term))

    factor = (Decimal("1") + monthly_rate) ** term
    payment = total_amount * (monthly_rate * factor) / (factor - Decimal("1"))
    return round_money(payment)


def calculate_psk(amount: Decimal, payments: list[Decimal]) -> Decimal:
    low = Decimal("0")
    high = Decimal("1")

    for _ in range(100):
        mid = (low + high) / 2
        npv = -amount
        for index, payment in enumerate(payments, start=1):
            npv += payment / ((Decimal("1") + mid) ** index)

        if npv > 0:
            low = mid
        else:
            high = mid

    monthly_rate = (low + high) / 2
    return round_money(monthly_rate * Decimal("12") * Decimal("100"))


def generate_offers(request: LoanStatementRequestDto) -> list[LoanOfferDto]:
    logger.info(f"Generating offers for amount={request.amount}, term={request.term}")
    prescore_request(request.amount, request.term, request.birthdate)
    logger.info("Prescoring passed")

    combinations = [
        (False, False),
        (False, True),
        (True, False),
        (True, True),
    ]

    offers = []
    for is_insurance, is_salary in combinations:
        rate, total_amount = calculate_rate_and_amount(request.amount, is_insurance, is_salary)
        monthly_payment = calculate_monthly_payment(total_amount, request.term, rate)

        offer = LoanOfferDto(
            statementId=uuid4(),
            requestedAmount=round_money(request.amount),
            totalAmount=total_amount,
            term=request.term,
            monthlyPayment=monthly_payment,
            rate=rate,
            isInsuranceEnabled=is_insurance,
            isSalaryClient=is_salary,
        )
        offers.append(offer)

    offers.sort(key=lambda x: x.rate, reverse=True)
    logger.info(f"Generated {len(offers)} offers sorted from highest rate to lowest rate")
    return offers


def calculate_credit(data: ScoringDataDto) -> CreditDto:
    logger.info(f"Calculating full credit parameters for amount={data.amount}, term={data.term}")
    prescore_request(data.amount, data.term, data.birthdate)
    logger.info("Prescoring passed")

    rate, total_amount = calculate_rate_and_amount(
        data.amount, data.isInsuranceEnabled, data.isSalaryClient
    )
    monthly_payment = calculate_monthly_payment(total_amount, data.term, rate)
    monthly_rate = (rate / Decimal("100")) / Decimal("12")

    schedule = []
    remaining_debt = total_amount
    start_date = date.today()
    payments = []

    for number in range(1, data.term + 1):
        payment_date = add_months(start_date, number)
        interest_payment = round_money(remaining_debt * monthly_rate)

        if number == data.term:
            debt_payment = remaining_debt
            current_total_payment = round_money(debt_payment + interest_payment)
            remaining_debt = Decimal("0.00")
        else:
            current_total_payment = monthly_payment
            debt_payment = round_money(current_total_payment - interest_payment)
            remaining_debt = round_money(remaining_debt - debt_payment)

        payments.append(current_total_payment)

        element = PaymentScheduleElementDto(
            number=number,
            date=payment_date,
            totalPayment=current_total_payment,
            interestPayment=interest_payment,
            debtPayment=debt_payment,
            remainingDebt=remaining_debt,
        )
        schedule.append(element)

    psk = calculate_psk(data.amount, payments)

    logger.info(f"Credit calculation finished: monthlyPayment={monthly_payment}, psk={psk}%")

    return CreditDto(
        amount=total_amount,
        term=data.term,
        monthlyPayment=monthly_payment,
        rate=rate,
        psk=psk,
        isInsuranceEnabled=data.isInsuranceEnabled,
        isSalaryClient=data.isSalaryClient,
        paymentSchedule=schedule,
    )
