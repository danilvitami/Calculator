import logging
from fastapi import APIRouter

from app.models import CreditDto, LoanOfferDto, LoanStatementRequestDto, ScoringDataDto
from app.service import calculate_credit, generate_offers

logger = logging.getLogger("calculator")

router = APIRouter(prefix="/calculator", tags=["Calculator"])


@router.post(
    "/offers",
    response_model=list[LoanOfferDto],
    summary="Расчёт возможных условий кредита",
    description="Прескоринг и формирование 4 кредитных предложений от худшего к лучшему.",
)
def get_offers(request: LoanStatementRequestDto) -> list[LoanOfferDto]:
    logger.info(
        f"POST /calculator/offers request received: amount={request.amount}, "
        f"term={request.term}, email={request.email}"
    )
    offers = generate_offers(request)
    logger.info(f"POST /calculator/offers response returned with {len(offers)} offers")
    return offers


@router.post(
    "/calc",
    response_model=CreditDto,
    summary="Полный расчёт параметров кредита",
    description="Валидация скоринговых данных и расчёт ПСК, ежемесячного платежа и графика платежей.",
)
def calc_credit(request: ScoringDataDto) -> CreditDto:
    logger.info(
        f"POST /calculator/calc request received: amount={request.amount}, "
        f"term={request.term}, insurance={request.isInsuranceEnabled}, "
        f"salary={request.isSalaryClient}"
    )
    credit = calculate_credit(request)
    logger.info(f"POST /calculator/calc response returned: rate={credit.rate}, psk={credit.psk}")
    return credit
