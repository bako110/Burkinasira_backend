from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.business import QuoteRequestStatus, InvoiceStatus
from app.schemas.business import (
    CreateQuoteRequest,
    UpdateQuoteRequest,
    QuoteRequestResponse,
    CreateInvoiceRequest,
    InvoiceResponse,
    UpdateInvoiceStatusRequest,
    AddParticipantRequest,
    ParticipantResponse,
)

QUOTES_COLLECTION = "business_quote_requests"
INVOICES_COLLECTION = "business_invoices"
PARTICIPANTS_COLLECTION = "business_event_participants"


# --- Devis groupé ---

def _quote_to_response(doc: dict) -> QuoteRequestResponse:
    return QuoteRequestResponse(
        id=str(doc["_id"]),
        requester_id=doc["requester_id"],
        company_name=doc["company_name"],
        service_types=doc.get("service_types", []),
        region=doc.get("region"),
        event_date=doc.get("event_date"),
        participant_count=doc.get("participant_count", 1),
        notes=doc.get("notes"),
        quoted_amount=doc.get("quoted_amount"),
        currency=doc.get("currency", "XOF"),
        status=doc.get("status", QuoteRequestStatus.SUBMITTED.value),
        created_at=doc["created_at"],
    )


async def create_quote_request(data: CreateQuoteRequest, requester_id: str) -> QuoteRequestResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["requester_id"] = requester_id
    doc["quoted_amount"] = None
    doc["currency"] = "XOF"
    doc["status"] = QuoteRequestStatus.SUBMITTED.value
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[QUOTES_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _quote_to_response(doc)


async def list_my_quote_requests(requester_id: str) -> list:
    db = get_database()
    docs = await db[QUOTES_COLLECTION].find({"requester_id": requester_id}).sort("created_at", -1).to_list(length=None)
    return [_quote_to_response(d) for d in docs]


async def list_all_quote_requests(status_filter: Optional[QuoteRequestStatus] = None) -> list:
    db = get_database()
    query: dict = {}
    if status_filter:
        query["status"] = status_filter.value if isinstance(status_filter, QuoteRequestStatus) else status_filter
    docs = await db[QUOTES_COLLECTION].find(query).sort("created_at", -1).to_list(length=None)
    return [_quote_to_response(d) for d in docs]


async def get_quote_request(quote_id: str, current_user_id: str, is_admin: bool) -> QuoteRequestResponse:
    db = get_database()
    if not ObjectId.is_valid(quote_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande de devis introuvable")
    doc = await db[QUOTES_COLLECTION].find_one({"_id": ObjectId(quote_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande de devis introuvable")
    if doc["requester_id"] != current_user_id and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé")
    return _quote_to_response(doc)


async def update_quote_request(quote_id: str, data: UpdateQuoteRequest) -> QuoteRequestResponse:
    """(Admin/Provider) Répondre à une demande de devis."""
    db = get_database()
    if not ObjectId.is_valid(quote_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande de devis introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[QUOTES_COLLECTION].update_one({"_id": ObjectId(quote_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande de devis introuvable")
    doc = await db[QUOTES_COLLECTION].find_one({"_id": ObjectId(quote_id)})
    return _quote_to_response(doc)


# --- Facturation entreprise ---

def _invoice_to_response(doc: dict) -> InvoiceResponse:
    return InvoiceResponse(
        id=str(doc["_id"]),
        quote_request_id=doc["quote_request_id"],
        company_name=doc["company_name"],
        amount=doc["amount"],
        currency=doc.get("currency", "XOF"),
        status=doc.get("status", InvoiceStatus.DRAFT.value),
        due_date=doc.get("due_date"),
        created_at=doc["created_at"],
    )


async def create_invoice(data: CreateInvoiceRequest) -> InvoiceResponse:
    db = get_database()
    if not ObjectId.is_valid(data.quote_request_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande de devis introuvable")
    quote = await db[QUOTES_COLLECTION].find_one({"_id": ObjectId(data.quote_request_id)})
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande de devis introuvable")

    now = datetime.utcnow()
    doc = data.model_dump()
    doc["company_name"] = quote["company_name"]
    doc["status"] = InvoiceStatus.DRAFT.value
    doc["created_at"] = now
    result = await db[INVOICES_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _invoice_to_response(doc)


async def list_invoices_for_quote(quote_id: str) -> list:
    db = get_database()
    docs = await db[INVOICES_COLLECTION].find({"quote_request_id": quote_id}).to_list(length=None)
    return [_invoice_to_response(d) for d in docs]


async def update_invoice_status(invoice_id: str, data: UpdateInvoiceStatusRequest) -> InvoiceResponse:
    db = get_database()
    if not ObjectId.is_valid(invoice_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facture introuvable")
    result = await db[INVOICES_COLLECTION].update_one(
        {"_id": ObjectId(invoice_id)}, {"$set": {"status": data.status.value}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facture introuvable")
    doc = await db[INVOICES_COLLECTION].find_one({"_id": ObjectId(invoice_id)})
    return _invoice_to_response(doc)


# --- Participants ---

def _participant_to_response(doc: dict) -> ParticipantResponse:
    return ParticipantResponse(
        id=str(doc["_id"]),
        quote_request_id=doc["quote_request_id"],
        full_name=doc["full_name"],
        email=doc.get("email"),
        phone=doc.get("phone"),
    )


async def add_participant(quote_id: str, data: AddParticipantRequest) -> ParticipantResponse:
    db = get_database()
    if not ObjectId.is_valid(quote_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande de devis introuvable")
    quote = await db[QUOTES_COLLECTION].find_one({"_id": ObjectId(quote_id)})
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande de devis introuvable")

    doc = data.model_dump()
    doc["quote_request_id"] = quote_id
    doc["created_at"] = datetime.utcnow()
    result = await db[PARTICIPANTS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _participant_to_response(doc)


async def list_participants(quote_id: str) -> list:
    db = get_database()
    docs = await db[PARTICIPANTS_COLLECTION].find({"quote_request_id": quote_id}).to_list(length=None)
    return [_participant_to_response(d) for d in docs]


async def remove_participant(participant_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(participant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant introuvable")
    result = await db[PARTICIPANTS_COLLECTION].delete_one({"_id": ObjectId(participant_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant introuvable")
