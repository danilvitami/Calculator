import logging
from fastapi import FastAPI

from app.router import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title="Микросервис Калькулятор (calculator)",
    description="MVP Level 1. Расчёт кредитных предложений и полного графика платежей.",
    version="1.0.0",
)

app.include_router(router)
