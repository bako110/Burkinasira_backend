from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint
from app.models.emergency import (
    EmergencyServiceType,
    IncidentStatus,
    SecurityAlertSeverity,
)


# --- Contacts officiels ---

class CreateEmergencyContactRequest(BaseModel):
    type: EmergencyServiceType
    label: str
    phone_number: str
    region: Optional[str] = None


class UpdateEmergencyContactRequest(BaseModel):
    label: Optional[str] = None
    phone_number: Optional[str] = None
    region: Optional[str] = None
    is_active: Optional[bool] = None


class EmergencyContactResponse(BaseModel):
    id: str
    type: EmergencyServiceType
    label: str
    phone_number: str
    region: Optional[str] = None
    is_active: bool


# --- Signalement d'incident ---

class ReportIncidentRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    description: str = Field(..., min_length=5)
    location: Optional[GeoPoint] = None


class IncidentReportResponse(BaseModel):
    id: str
    reporter_id: Optional[str] = None
    title: str
    description: str
    location: Optional[GeoPoint] = None
    status: IncidentStatus
    created_at: datetime


class ModerateIncidentRequest(BaseModel):
    status: IncidentStatus


# --- Alertes sécurité ---

class CreateSecurityAlertRequest(BaseModel):
    title: str
    description: str
    severity: SecurityAlertSeverity = SecurityAlertSeverity.INFO
    region: Optional[str] = None
    location: Optional[GeoPoint] = None
    radius_km: Optional[float] = None


class UpdateSecurityAlertRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[SecurityAlertSeverity] = None
    region: Optional[str] = None
    location: Optional[GeoPoint] = None
    radius_km: Optional[float] = None
    is_active: Optional[bool] = None


class SecurityAlertResponse(BaseModel):
    id: str
    title: str
    description: str
    severity: SecurityAlertSeverity
    region: Optional[str] = None
    location: Optional[GeoPoint] = None
    radius_km: Optional[float] = None
    is_active: bool
    created_at: datetime


# --- SOS ---

class TriggerSOSRequest(BaseModel):
    location: GeoPoint
    trusted_contact_phone: Optional[str] = None
    message: Optional[str] = None


class SOSAlertResponse(BaseModel):
    id: str
    user_id: str
    location: GeoPoint
    trusted_contact_phone: Optional[str] = None
    message: Optional[str] = None
    emergency_contacts: List[EmergencyContactResponse]
    created_at: datetime
