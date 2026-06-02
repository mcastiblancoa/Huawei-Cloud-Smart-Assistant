from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum


class IntentType(str, Enum):
    LIST = "list"
    DESCRIBE = "describe"
    CREATE = "create"
    DELETE = "delete"
    MANAGE = "manage"
    BILLING = "billing"
    DISCOVERY = "discovery"
    CHAT = "chat"
    UNKNOWN = "unknown"


class CloudService(str, Enum):
    ECS = "ECS"
    VPC = "VPC"
    ELB = "ELB"
    EIP = "EIP"
    RDS = "RDS"
    OBS = "OBS"
    IAM = "IAM"
    BSSINTL = "BSSINTL"
    RMS = "RMS"
    SG = "SG"
    CCE = "CCE"
    DNS = "DNS"
    AS = "AS"
    MONITOR = "MONITOR"


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


class TranscriptionResult(BaseModel):
    text: str = ""
    request_id: str | None = None
    audio_format: str = ""
    audio_size_bytes: int = 0
    provider_raw_response: dict = {}


class VoiceResponse(BaseModel):
    transcription: str = Field(default="", description="STT transcribed text")
    reply: str = Field(default="", description="Agent response text")
    session_id: str = Field(description="Session identifier for conversation continuity")
    has_audio: bool = Field(default=False, description="Whether TTS audio was generated")
    latency_ms: Optional[int] = None
    tool_calls: Optional[int] = None
    path: Optional[str] = None
    error: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="User message to send to the chat assistant")
    session_id: str = Field(description="Persistent chat session identifier")


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    raw_messages: Optional[list[dict[str, Any]]] = None
    latency_ms: Optional[int] = None
    tool_calls: Optional[int] = None
    path: Optional[str] = None


class FaceEmotion(BaseModel):
    dominant_emotion: str = Field(description="Dominant emotion for this face")
    confidence: float = Field(description="Confidence percentage for dominant emotion")
    all_scores: dict[str, float] = Field(description="All emotion scores")
    face_index: int = Field(default=0, description="Index of the detected face")


class SentimentResponse(BaseModel):
    status: str = Field(description="Result status: success, no_face, error")
    dominant_emotion: Optional[str] = Field(default=None, description="Dominant emotion detected")
    confidence: Optional[float] = Field(default=None, description="Confidence percentage")
    all_scores: Optional[dict[str, float]] = Field(default=None, description="All emotion scores")
    faces: list[dict[str, Any]] = Field(default_factory=list, description="Per-face emotion results")
    face_count: int = Field(default=0, description="Number of faces detected")
    latency_ms: Optional[int] = Field(default=None, description="Processing latency in ms")
    error: Optional[str] = Field(default=None, description="Error message if status is error")


class SafetyResponse(BaseModel):
    status: str = Field(description="Result status: success, error")
    total_persons: int = Field(default=0, description="Number of persons detected")
    compliant_persons: int = Field(default=0, description="Number of fully compliant persons")
    compliance_rate: float = Field(default=0.0, description="Compliance percentage 0-100")
    persons: list[dict[str, Any]] = Field(default_factory=list, description="Per-person PPE detection results")
    all_detections: list[dict[str, Any]] = Field(default_factory=list, description="All detected objects")
    ppe_summary: dict[str, int] = Field(default_factory=dict, description="Count of each PPE type detected")
    latency_ms: Optional[int] = Field(default=None, description="Processing latency in ms")
    error: Optional[str] = Field(default=None, description="Error message if status is error")
