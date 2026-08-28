from datetime import datetime
from typing import Optional
from bson import ObjectId
from app.core.database import get_database
from fastapi import HTTPException, status
from app.schemas.weather import (
    CreateWeatherSnapshotRequest,
    WeatherSnapshotResponse,
    CreateWeatherAlertRequest,
    UpdateWeatherAlertRequest,
    WeatherAlertResponse,
    SeasonalTipResponse,
)

SNAPSHOTS_COLLECTION = "weather_snapshots"
ALERTS_COLLECTION = "weather_alerts"
TIPS_COLLECTION = "seasonal_tips"


def _snapshot_to_response(doc: dict) -> WeatherSnapshotResponse:
    return WeatherSnapshotResponse(
        id=str(doc["_id"]),
        region=doc["region"],
        location=doc.get("location"),
        temperature_celsius=doc.get("temperature_celsius"),
        condition=doc.get("condition"),
        rain_probability_percent=doc.get("rain_probability_percent"),
        wind_speed_kmh=doc.get("wind_speed_kmh"),
        air_quality_index=doc.get("air_quality_index"),
        forecast_date=doc["forecast_date"],
        source=doc.get("source"),
    )


async def create_snapshot(data: CreateWeatherSnapshotRequest) -> WeatherSnapshotResponse:
    db = get_database()
    doc = data.model_dump()
    doc["created_at"] = datetime.utcnow()
    result = await db[SNAPSHOTS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _snapshot_to_response(doc)


async def get_current_weather(region: str) -> Optional[WeatherSnapshotResponse]:
    db = get_database()
    doc = await db[SNAPSHOTS_COLLECTION].find_one({"region": region}, sort=[("forecast_date", -1)])
    return _snapshot_to_response(doc) if doc else None


async def get_forecast(region: str, days: int = 5) -> list:
    db = get_database()
    now = datetime.utcnow()
    docs = await db[SNAPSHOTS_COLLECTION].find(
        {"region": region, "forecast_date": {"$gte": now}}
    ).sort("forecast_date", 1).limit(days).to_list(length=days)
    return [_snapshot_to_response(d) for d in docs]


# --- Alertes météo ---

def _alert_to_response(doc: dict) -> WeatherAlertResponse:
    return WeatherAlertResponse(
        id=str(doc["_id"]),
        region=doc["region"],
        title=doc["title"],
        description=doc["description"],
        severity=doc.get("severity", "info"),
        is_active=doc.get("is_active", True),
        created_at=doc["created_at"],
    )


async def create_alert(data: CreateWeatherAlertRequest, published_by: str) -> WeatherAlertResponse:
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
        query["region"] = region
    docs = await db[ALERTS_COLLECTION].find(query).sort("created_at", -1).to_list(length=None)
    return [_alert_to_response(d) for d in docs]


async def update_alert(alert_id: str, data: UpdateWeatherAlertRequest) -> WeatherAlertResponse:
    db = get_database()
    if not ObjectId.is_valid(alert_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerte météo introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[ALERTS_COLLECTION].update_one({"_id": ObjectId(alert_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerte météo introuvable")
    doc = await db[ALERTS_COLLECTION].find_one({"_id": ObjectId(alert_id)})
    return _alert_to_response(doc)


async def delete_alert(alert_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(alert_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerte météo introuvable")
    result = await db[ALERTS_COLLECTION].delete_one({"_id": ObjectId(alert_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerte météo introuvable")


# --- Conseils saisonniers ---

def _tip_to_response(doc: dict) -> SeasonalTipResponse:
    return SeasonalTipResponse(
        id=str(doc["_id"]),
        season=doc["season"],
        title=doc["title"],
        content=doc["content"],
    )


async def list_seasonal_tips(season: Optional[str] = None) -> list:
    db = get_database()
    query: dict = {}
    if season:
        query["season"] = season
    docs = await db[TIPS_COLLECTION].find(query).to_list(length=None)
    return [_tip_to_response(d) for d in docs]
