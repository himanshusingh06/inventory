from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    phonepe_env: str = os.getenv("PHONEPE_ENV", "UAT")
    phonepe_merchant_id: str = os.getenv("PHONEPE_MERCHANT_ID", "")
    phonepe_merchant_secret: str = os.getenv("PHONEPE_MERCHANT_SECRET", "")
    phonepe_client_id: str = os.getenv("PHONEPE_CLIENT_ID", "")
    phonepe_client_secret: str = os.getenv("PHONEPE_CLIENT_SECRET", "")
    phonepe_base_url: str = os.getenv("PHONEPE_BASE_URL", "https://api-preprod.phonepe.com")
    phonepe_callback_url: str = os.getenv(
        "PHONEPE_CALLBACK_URL", "http://localhost:8000/api/payments/phonepe/callback"
    )
    phonepe_redirect_url: str = os.getenv(
        "PHONEPE_REDIRECT_URL", "http://localhost:5173/payment/status"
    )
    phonepe_webhook_secret: str = os.getenv("PHONEPE_WEBHOOK_SECRET", "")
    payment_expiry_minutes: int = int(os.getenv("PAYMENT_EXPIRY_MINUTES", "15"))
    database_url: str = os.getenv("DATABASE_URL", "postgresql://inventory_a64m_user:0rvU2Okz9BPqIRlJryqfR4JusdQUJ5mu@dpg-d98a1m67r5hc73coh1og-a/inventory_a64m")
    app_secret_key: str = os.getenv("APP_SECRET_KEY", "change-this-secret-in-production")
    cors_origins: list[str] = field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv("APP_CORS_ORIGINS", "http://localhost:5173").split(",")
            if origin.strip()
        ]
    )


settings = Settings()
