import os
from decimal import Decimal

TAX_RATE = Decimal(os.environ.get("TAX_RATE", "0.08"))
