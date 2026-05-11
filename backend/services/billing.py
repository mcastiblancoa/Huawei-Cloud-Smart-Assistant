import logging
import json
import time
from typing import Any

import httpx
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkbssintl.v2 import *
from huaweicloudsdkbssintl.v2.region.bssintl_region import BssintlRegion
from fastapi import HTTPException, status

from config.settings import Settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 5.0


def get_monthly_billing_summary(settings: Settings, bill_cycle: str) -> dict[str, Any]:
    ak = settings.huawei_ak
    sk = settings.huawei_sk

    if not all([ak, sk]):
        return {
            "month": bill_cycle, "total": 0.0, "currency": "USD",
            "services": [], "error": "Credentials not configured (AK or SK missing).",
        }

    for attempt in range(MAX_RETRIES + 1):
        try:
            credentials = GlobalCredentials(ak, sk)
            client = BssintlClient.new_builder() \
                .with_credentials(credentials) \
                .with_region(BssintlRegion.value_of("ap-southeast-1")) \
                .build()

            request = ShowCustomerMonthlySumRequest()
            request.bill_cycle = bill_cycle
            response = client.show_customer_monthly_sum(request)

            currency = response.currency if hasattr(response, 'currency') else "USD"
            total = 0.0
            services_dict = {}

            if hasattr(response, 'bill_sums') and response.bill_sums:
                for item in response.bill_sums:
                    amount = float(getattr(item, 'consume_amount', 0.0))
                    service_name = getattr(item, 'service_type_name', 'Unknown Service')
                    if service_name in services_dict:
                        services_dict[service_name] += amount
                    else:
                        services_dict[service_name] = amount
                    total += amount

            total = round(total, 2)
            services = []
            for name, amount in services_dict.items():
                if amount > 0:
                    services.append({"name": name, "amount": round(amount, 2)})

            return {
                "month": bill_cycle,
                "total": total,
                "currency": currency,
                "services": sorted(services, key=lambda x: x['amount'], reverse=True),
                "error": None,
            }

        except exceptions.ClientRequestException as exc:
            is_rate_limit = exc.status_code == 429 or "429" in str(exc.error_msg)
            if is_rate_limit and attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning("Billing 429 rate limit, retrying in %.1fs (attempt %d/%d)", delay, attempt + 1, MAX_RETRIES)
                time.sleep(delay)
                continue

            logger.exception("Huawei Cloud BSS API error")
            error_detail = f"Error {exc.status_code}: {exc.error_msg}"
            if is_rate_limit:
                error_detail = "Rate limit exceeded. Please try again in a moment."
            return {
                "month": bill_cycle, "total": 0.0, "currency": "USD",
                "services": [], "error": f"Failed to fetch billing: {error_detail}",
            }

        except Exception as exc:
            logger.exception("Unexpected error when calling BSS API")
            return {
                "month": bill_cycle, "total": 0.0, "currency": "USD",
                "services": [], "error": f"Unexpected error: {str(exc)}",
            }

    return {
        "month": bill_cycle, "total": 0.0, "currency": "USD",
        "services": [], "error": "Rate limit exceeded after all retries. Please try again later.",
    }


def generate_natural_billing_response(settings: Settings, billing_data: dict, language: str) -> str:
    url = settings.maas_api_url
    api_key = settings.maas_api_key

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    system_prompt = f"""You are an expert billing assistant for cloud services.
Given the structured billing data in JSON format, write a concise, natural sentence in {'Spanish' if language == 'es' else 'English'} summarizing the spending.
State the total spent and point out the highest cost service. Do not use markdown or external notes. Just the final sentence.
Example English: "You spent 17.19 USD in March 2026. Your highest spending was on Virtual Private Cloud."
Example Spanish: "Gastaste 17.19 USD en marzo de 2026. Tu mayor gasto fue en Virtual Private Cloud."
"""

    request_body = {
        "model": settings.intent_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Billing data: {json.dumps(billing_data)}"},
        ],
        "thinking": {"type": "disabled"},
    }

    try:
        response = httpx.post(url, json=request_body, headers=headers, timeout=20.0, verify=False)
        response.raise_for_status()
        response_data = response.json()
        if response_data.get("choices") and len(response_data["choices"]) > 0:
            return response_data["choices"][0].get("message", {}).get("content", "").strip()
        return "Could not generate response."
    except Exception as exc:
        logger.exception("Failed to generate natural response from MaaS")
        return ""
