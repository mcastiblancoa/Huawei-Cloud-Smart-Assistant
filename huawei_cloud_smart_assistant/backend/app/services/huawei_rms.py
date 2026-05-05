import logging
import os
from typing import Any

from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkrms.v1 import *
from huaweicloudsdkrms.v1.region.rms_region import RmsRegion
from fastapi import HTTPException, status

from app.core.config import Settings

logger = logging.getLogger(__name__)


def list_all_resources(settings: Settings) -> dict[str, Any]:
    """
    Queries Huawei Cloud Resource Management Service to list all resources.
    
    Returns a dict with:
    - total: int (total number of resources)
    - resources: list (list of resources with relevant fields)
    - error: str | None (error message if any)
    """
    
    try:
        # Get credentials from environment or settings
        ak = settings.cloud_sdk_ak
        sk = settings.cloud_sdk_sk
        domain_id = settings.cloud_sdk_domain_id
        
        if not all([ak, sk, domain_id]):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Huawei Cloud credentials not configured (AK, SK, or Domain ID missing).",
            )
        
        # Create credentials
        credentials = GlobalCredentials(ak, sk, domain_id)
        
        # Create RMS client - use a generic region, it doesn't affect listing all resources
        client = RmsClient.new_builder() \
            .with_credentials(credentials) \
            .with_region(RmsRegion.value_of("cn-north-4")) \
            .build()
        
        # Create list request
        request = ListAllResourcesRequest()
        
        # Call API
        response = client.list_all_resources(request)
        
        # Extract resources from response
        resources = []
        if hasattr(response, 'resources') and response.resources:
            for resource in response.resources:
                # Try to get state - use provisioning_state if state is unknown
                state = getattr(resource, 'state', None)
                if not state or state.lower() == 'unknown':
                    state = getattr(resource, 'provisioning_state', None) or 'Unknown'
                
                resource_dict = {
                    "id": getattr(resource, 'id', None),
                    "name": getattr(resource, 'name', None),
                    "provider": getattr(resource, 'provider', None),
                    "type": getattr(resource, 'type', None),
                    "region_id": getattr(resource, 'region_id', None),
                    "project_id": getattr(resource, 'project_id', None),
                    "project_name": getattr(resource, 'project_name', None),
                    "created": str(getattr(resource, 'created', None)) if getattr(resource, 'created', None) else None,
                    "updated": str(getattr(resource, 'updated', None)) if getattr(resource, 'updated', None) else None,
                    "provisioning_state": getattr(resource, 'provisioning_state', None),
                    "state": state,
                    "properties": getattr(resource, 'properties', None),
                }
                resources.append(resource_dict)
        
        return {
            "total": len(resources),
            "resources": resources,
            "error": None,
        }
        
    except exceptions.ClientRequestException as exc:
        logger.exception("Huawei Cloud RMS API error")
        error_detail = f"Error {exc.status_code}: {exc.error_msg}"
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch resources from Huawei Cloud RMS: {error_detail}",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error when calling RMS API")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected error when fetching resources from Huawei Cloud.",
        ) from exc
