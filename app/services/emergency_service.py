from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.emergency import EmergencyServiceType, IncidentStatus
from app.schemas.emergency import (
    CreateEmergencyContactRequest,
    UpdateEmergencyContactRequest,
    EmergencyContactResponse,
    ReportIncidentRequest,
    IncidentReportResponse,
    ModerateIncidentRequest,
    CreateSecurityAlertRequest,
    UpdateSecurityAlertRequest,
    SecurityAlertResponse,
    TriggerSOSRequest,
    SOSAlertResponse,
)

CONTACTS_COLLECTION = "emergency_contacts"
INCIDENTS_COLLECTION = "incident_reports"
ALERTS_COLLECTION = "security_alerts"
SOS_COLLECTION = "sos_alerts"


# --- Contacts officiels ---

def _contact_to_response(doc: dict) -> EmergencyContactResponse:
    return EmergencyContactResponse(
        id=str(doc["_id"]),
        type=doc["type"],
        label=doc["label"],
        phone_number=doc["phone_number"],
        region=doc.get("region"),
        is_active=doc.get("is_active", True),
    )


async def create_contact(data: CreateEmergencyContactRequest) -> EmergencyContactResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["is_active"] = True
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[CONTACTS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _contact_to_response(doc)


async def list_contacts(region: Optional[str] = None) -> list:
    db = get_database()
    query: dict = {"is_active": True}
    if region:
        query["$or"] = [{"region": region}, {"region": None}]
    docs = await db[CONTACTS_COLLECTION].find(query).to_list(length=None)
    return [_contact_to_response(d) for d in docs]


async def update_contact(contact_id: str, data: UpdateEmergencyContactRequest) -> EmergencyContactResponse:
    db = get_database()
    if not ObjectId.is_valid(contact_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[CONTACTS_COLLECTION].update_one({"_id": ObjectId(contact_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact introuvable")
    doc = await db[CONTACTS_COLLECTION].find_one({"_id": ObjectId(contact_id)})
    return _contact_to_response(doc)


async def delete_contact(contact_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(contact_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact introuvable")
    result = await db[CONTACTS_COLLECTION].delete_one({"_id": ObjectId(contact_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact introuvable")


# --- Signalement d'incident ---

def _incident_to_response(doc: dict) -> IncidentReportResponse:
    return IncidentReportResponse(
        id=str(doc["_id"]),
        reporter_id=doc.get("reporter_id"),
        title=doc["title"],
        description=doc["description"],
        location=doc.get("location"),
        status=doc.get("status", IncidentStatus.REPORTED.value),
        created_at=doc["created_at"],
    )


async def report_incident(data: ReportIncidentRequest, reporter_id: Optional[str]) -> IncidentReportResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["reporter_id"] = reporter_id
    doc["status"] = IncidentStatus.REPORTED.value
    doc["moderated_by"] = None
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[INCIDENTS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _incident_to_response(doc)


async def list_incidents(status_filter: Optional[IncidentStatus] = None) -> list:
    db = get_database()
    query: dict = {}
    if status_filter:
        query["status"] = status_filter.value if isinstance(status_filter, IncidentStatus) else status_filter
    docs = await db[INCIDENTS_COLLECTION].find(query).sort("created_at", -1).to_list(length=None)
    return [_incident_to_response(d) for d in docs]


async def moderate_incident(incident_id: str, data: ModerateIncidentRequest, moderator_id: str) -> IncidentReportResponse:
    db = get_database()
    if not ObjectId.is_valid(incident_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signalement introuvable")
    result = await db[INCIDENTS_COLLECTION].update_one(
        {"_id": ObjectId(incident_id)},
        {"$set": {"status": data.status.value, "moderated_by": moderator_id, "updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signalement introuvable")
    doc = await db[INCIDENTS_COLLECTION].find_one({"_id": ObjectId(incident_id)})
    return _incident_to_response(doc)


# --- Alertes sécurité ---

def _alert_to_response(doc: dict) -> SecurityAlertResponse:
    return SecurityAlertResponse(
        id=str(doc["_id"]),
        title=doc["title"],
        description=doc["description"],
        severity=doc.get("severity", "info"),
        region=doc.get("region"),
        location=doc.get("location"),
        radius_km=doc.get("radius_km"),
        is_active=doc.get("is_active", True),
        created_at=doc["created_at"],
    )


async def create_alert(data: CreateSecurityAlertRequest, published_by: str) -> SecurityAlertResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["is_active"] = True
    doc["published_by"] = published_by
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[ALERTS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _alert_to_response(doc)


async def list_active_alerts(region: Optional[str] = None) -> list:
    db = get_database()
    query: dict = {"is_active": True}
    if region:
        query["$or"] = [{"region": region}, {"region": None}]
    docs = await db[ALERTS_COLLECTION].find(query).sort("created_at", -1).to_list(length=None)
    return [_alert_to_response(d) for d in docs]


async def update_alert(alert_id: str, data: UpdateSecurityAlertRequest) -> SecurityAlertResponse:
    db = get_database()
    if not ObjectId.is_valid(alert_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerte introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[ALERTS_COLLECTION].update_one({"_id": ObjectId(alert_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerte introuvable")
    doc = await db[ALERTS_COLLECTION].find_one({"_id": ObjectId(alert_id)})
    return _alert_to_response(doc)


async def delete_alert(alert_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(alert_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerte introuvable")
    result = await db[ALERTS_COLLECTION].delete_one({"_id": ObjectId(alert_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerte introuvable")


# --- SOS ---

async def trigger_sos(data: TriggerSOSRequest, user_id: str) -> SOSAlertResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["user_id"] = user_id
    doc["created_at"] = now
    result = await db[SOS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    contacts = await list_contacts()

    return SOSAlertResponse(
        id=str(doc["_id"]),
        user_id=user_id,
        location=data.location,
        trusted_contact_phone=data.trusted_contact_phone,
        message=data.message,
        emergency_contacts=contacts,
        created_at=now,
    )
