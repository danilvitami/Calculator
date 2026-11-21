import configparser
from decimal import Decimal
from pathlib import Path

config = configparser.ConfigParser()
config_path = Path(__file__).resolve().parent.parent.parent / "config.ini"
config.read(config_path)

BASE_RATE = Decimal(config.get("calculator", "base_rate", fallback="15.0"))
INSURANCE_COST = Decimal(config.get("calculator", "insurance_cost", fallback="100000.0"))
INSURANCE_DISCOUNT = Decimal(config.get("calculator", "insurance_rate_discount", fallback="3.0"))
SALARY_DISCOUNT = Decimal(config.get("calculator", "salary_client_rate_discount", fallback="1.0"))
