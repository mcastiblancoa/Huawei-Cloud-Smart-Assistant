import logging
import json
import httpx
from typing import Any

from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkbssintl.v2 import *
from huaweicloudsdkbssintl.v2.region.bssintl_region import BssintlRegion
from fastapi import HTTPException, status

from app.core.config import Settings

logger = logging.getLogger(__name__)

def get_monthly_billing_summary(settings: Settings, bill_cycle: str) -> dict[str, Any]:
    """
    Queries Huawei Cloud BSS to get monthly billing summary.
    
    bill_cycle: str in YYYY-MM format
    
    Returns a dict with:
    - month: str (YYYY-MM)
    - total: float
    - currency: str
    - services: list of dicts with name and amount
    - error: str | None
    """
    try:
        ak = settings.cloud_sdk_ak
        sk = settings.cloud_sdk_sk
        
        # BSS uses global region ap-southeast-1 or cn-north-1 typically
        # Default region configuration
        region = getattr(settings, 'cloud_sdk_region', 'ap-southeast-1')
        
        if not all([ak, sk]):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Huawei Cloud credentials not configured (AK or SK missing).",
            )
            
        credentials = GlobalCredentials(ak, sk)
        client = BssintlClient.new_builder() \
            .with_credentials(credentials) \
            .with_region(BssintlRegion.value_of(region)) \
            .build()
            
        request = ShowCustomerMonthlySumRequest()
        request.bill_cycle = bill_cycle
        
        response = client.show_customer_monthly_sum(request)
        
        # Process and aggregate data
        currency = response.currency if hasattr(response, 'currency') else "USD"
        
        # Get total amount: Some responses might use consume_amount or something else depending on structure
        total = 0.0
        services_dict = {}
        
        if hasattr(response, 'bill_sums') and response.bill_sums:
            for item in response.bill_sums:
                amount = float(getattr(item, 'consume_amount', 0.0))
                service_name = getattr(item, 'service_type_name', 'Unknown Service')
                
                # We need to compute total. The response might have total or we can sum here.
                # However, bill_sums might be structured deeply or uniquely
                # Let's sum it up based on service_type_name
                if service_name in services_dict:
                    services_dict[service_name] += amount
                else:
                    services_dict[service_name] = amount
                total += amount
                
        # Handle decimal precision
        total = round(total, 2)
        services = []
        for name, amount in services_dict.items():
            # Keep only services with cost > 0
            if amount > 0:
                services.append({
                    "name": name,
                    "amount": round(amount, 2)
                })
            
        return {
            "month": bill_cycle,
            "total": total,
            "currency": currency,
            "services": sorted(services, key=lambda x: x['amount'], reverse=True),
            "error": None
        }
        
    except exceptions.ClientRequestException as exc:
        logger.exception("Huawei Cloud BSS API error")
        error_detail = f"Error {exc.status_code}: {exc.error_msg}"
        return {
            "month": bill_cycle,
            "total": 0.0,
            "currency": "USD",
            "services": [],
            "error": f"Failed to fetch billing from Huawei Cloud BSS: {error_detail}"
        }
    except Exception as exc:
        logger.exception("Unexpected error when calling BSS API")
        return {
            "month": bill_cycle,
            "total": 0.0,
            "currency": "USD",
            "services": [],
            "error": f"Unexpected error: {str(exc)}"
        }

def generate_natural_billing_response(settings: Settings, billing_data: dict, language: str) -> str:
    """
    Uses DeepSeek MaaS to generate a natural language summary of the billing data.
    """
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
        "model": "deepseek-v3.2",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Billing data: {json.dumps(billing_data)}"},
        ],
        "thinking": {"type": "disabled"}
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
