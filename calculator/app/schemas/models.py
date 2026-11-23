import re
from datetime import date
from decimal import Decimal

from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def check_adult(birthdate: date) -> date:
    today = date.today()
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    if age < 18:
        raise ValueError("Age must be at least 18 years")
    return birthdate


class LoanStatementRequestDto(BaseModel):
    amount: Decimal = Field(..., ge=Decimal("10000"))
    term: int = Field(..., ge=6)
    firstName: str = Field(..., min_length=2, max_length=30, pattern=r"^[a-zA-Zа-яА-ЯёЁ]+$")
    lastName: str = Field(..., min_length=2, max_length=30, pattern=r"^[a-zA-Zа-яА-ЯёЁ]+$")
    middleName: str = Field(..., min_length=2, max_length=30, pattern=r"^[a-zA-Zа-яА-ЯёЁ]+$")
    email: str
    birthdate: date
    passportSeries: str = Field(..., pattern=r"^\d{4}$")
    passportNumber: str = Field(..., pattern=r"^\d{6}$")

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_!#$%&'*+/=?`{|}~^.-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", value):
            raise ValueError("Invalid email format")
        return value

    @field_validator("birthdate")
    @classmethod
    def validate_birthdate(cls, value: date) -> date:
        return check_adult(value)


class LoanOfferDto(BaseModel):
    statementId: UUID
    requestedAmount: Decimal
    totalAmount: Decimal
    term: int
    monthlyPayment: Decimal
    rate: Decimal
    isInsuranceEnabled: bool
    isSalaryClient: bool


class ScoringDataDto(BaseModel):
    amount: Decimal = Field(..., ge=Decimal("10000"))
    term: int = Field(..., ge=6)
    firstName: str = Field(..., min_length=2, max_length=30, pattern=r"^[a-zA-Zа-яА-ЯёЁ]+$")
    lastName: str = Field(..., min_length=2, max_length=30, pattern=r"^[a-zA-Zа-яА-ЯёЁ]+$")
    middleName: str = Field(..., min_length=2, max_length=30, pattern=r"^[a-zA-Zа-яА-ЯёЁ]+$")
    birthdate: date
    passportSeries: str = Field(..., pattern=r"^\d{4}$")
    passportNumber: str = Field(..., pattern=r"^\d{6}$")
    isInsuranceEnabled: bool
    isSalaryClient: bool

    @field_validator("birthdate")
    @classmethod
    def validate_birthdate(cls, value: date) -> date:
        return check_adult(value)


class PaymentScheduleElementDto(BaseModel):
    number: int
    date: date
    totalPayment: Decimal
    interestPayment: Decimal
    debtPayment: Decimal
    remainingDebt: Decimal


class CreditDto(BaseModel):
    amount: Decimal
    term: int
    monthlyPayment: Decimal
    rate: Decimal
    psk: Decimal
    isInsuranceEnabled: bool
    isSalaryClient: bool
    paymentSchedule: list[PaymentScheduleElementDto]
