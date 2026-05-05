from pydantic import BaseModel, Field
from typing import Optional, Any


class HealthResponse(BaseModel):
    status: str = "ok"


class IntentClassification(BaseModel):
    intent: str = Field(description="The detected user intent")
    confidence: float = Field(description="Confidence score (0-1)")
    should_call_rms: bool = Field(description="Whether to query Resource Management Service")
    should_call_bss: bool = Field(default=False, description="Whether to call Huawei BSS for billing")
    bill_cycle: Optional[str] = Field(default=None, description="The billing cycle in YYYY-MM format")
    language: Optional[str] = Field(default="en", description="The language detected (en or es)")
    summary: str = Field(description="Brief description of the intent")
    user_message: str = Field(description="Message explaining what will be done")


class ServiceBilling(BaseModel):
    name: str = Field(description="Name of the service")
    amount: float = Field(description="Amount spent")


class BillingSummary(BaseModel):
    month: str = Field(description="Billing cycle (YYYY-MM)")
    total: float = Field(description="Total amount spent")
    currency: str = Field(description="Currency (e.g., USD)")
    services: list[ServiceBilling] = Field(description="List of services and their costs")
    error: Optional[str] = None
    natural_response: Optional[str] = None


class ResourceInfo(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    provider: Optional[str] = None
    type: Optional[str] = None
    region_id: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None
    provisioning_state: Optional[str] = None
    state: Optional[str] = None
    properties: Optional[dict] = None


class ResourcesResponse(BaseModel):
    total: int
    resources: list[ResourceInfo]
    error: Optional[str] = None


class TranscriptionResponse(BaseModel):
    text: str = ""
    request_id: str | None = None
    audio_format: str = Field(description="Format sent to Huawei SIS")
    audio_size_bytes: int
    provider_raw_response: dict
    
    # Intent classification fields
    intent_classification: Optional[IntentClassification] = None
    
    # Resources response (if intent was query_services)
    resources_response: Optional[ResourcesResponse] = None

    # Billing response (if intent was query_billing)
    billing_response: Optional[BillingSummary] = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="User message to send to the chat assistant")
    session_id: str = Field(description="Persistent chat session identifier")


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    raw_messages: Optional[list[dict[str, Any]]] = None
