from datetime import datetime, timedelta
from collections import OrderedDict
from app.core.database import get_database
from app.models.booking import BookingStatus
from app.schemas.guide_analytics import TimeSeriesPoint, GuideAnalyticsSummary

COLLECTION = "bookings"

# Réservations comptant comme "revenu réel" (pas juste une demande en attente/annulée).
REVENUE_STATUSES = {BookingStatus.CONFIRMED.value, BookingStatus.COMPLETED.value}


def _last_n_days(n: int) -> list:
    today = datetime.utcnow().date()
    return [(today - timedelta(days=i)) for i in range(n - 1, -1, -1)]


def _last_n_months(n: int) -> list:
    today = datetime.utcnow().date()
    months = []
    y, m = today.year, today.month
    for _ in range(n):
        months.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(months))


async def get_guide_analytics(guide_id: str, currency: str = "XOF") -> GuideAnalyticsSummary:
    db = get_database()
    query = {"item_type": "guide", "item_id": guide_id}
    docs = await db[COLLECTION].find(query).to_list(length=None)

    total_customers = len({d["customer_id"] for d in docs})
    total_bookings = len(docs)
    revenue_docs = [d for d in docs if d.get("status") in REVENUE_STATUSES]
    total_revenue = sum(d["total_price"] for d in revenue_docs)
    average_booking_value = round(total_revenue / len(revenue_docs), 2) if revenue_docs else 0.0

    decided_docs = [d for d in docs if d.get("status") in REVENUE_STATUSES | {BookingStatus.CANCELLED.value, BookingStatus.REFUNDED.value}]
    completed_docs = [d for d in docs if d.get("status") == BookingStatus.COMPLETED.value]
    completion_rate = round(len(completed_docs) / len(decided_docs) * 100, 1) if decided_docs else 0.0

    # --- Quotidien : 30 derniers jours ---
    daily_buckets: "OrderedDict[str, dict]" = OrderedDict(
        (d.isoformat(), {"customers": set(), "bookings": 0, "revenue": 0.0}) for d in _last_n_days(30)
    )
    # --- Mensuel : 12 derniers mois ---
    monthly_buckets: "OrderedDict[str, dict]" = OrderedDict(
        (f"{y:04d}-{m:02d}", {"customers": set(), "bookings": 0, "revenue": 0.0}) for y, m in _last_n_months(12)
    )
    # --- Annuel : toutes les années présentes dans les données (au moins l'année en cours) ---
    years = sorted({d["created_at"].year for d in docs} | {datetime.utcnow().year})
    yearly_buckets: "OrderedDict[str, dict]" = OrderedDict(
        (str(y), {"customers": set(), "bookings": 0, "revenue": 0.0}) for y in years
    )

    for d in docs:
        created = d["created_at"]
        day_key = created.date().isoformat()
        month_key = f"{created.year:04d}-{created.month:02d}"
        year_key = str(created.year)
        is_revenue = d.get("status") in REVENUE_STATUSES

        for bucket, key in ((daily_buckets, day_key), (monthly_buckets, month_key), (yearly_buckets, year_key)):
            if key in bucket:
                bucket[key]["customers"].add(d["customer_id"])
                bucket[key]["bookings"] += 1
                if is_revenue:
                    bucket[key]["revenue"] += d["total_price"]

    def to_points(buckets: "OrderedDict[str, dict]") -> list:
        return [
            TimeSeriesPoint(
                period=key,
                customer_count=len(val["customers"]),
                booking_count=val["bookings"],
                revenue=round(val["revenue"], 2),
            )
            for key, val in buckets.items()
        ]

    return GuideAnalyticsSummary(
        currency=currency,
        total_customers=total_customers,
        total_bookings=total_bookings,
        total_revenue=round(total_revenue, 2),
        average_booking_value=average_booking_value,
        completion_rate=completion_rate,
        daily=to_points(daily_buckets),
        monthly=to_points(monthly_buckets),
        yearly=to_points(yearly_buckets),
    )
