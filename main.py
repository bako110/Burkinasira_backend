from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.api.v1.routes import (
    auth, destinations, experiences, guides, guide_availability, hotels,
    cuisines, health, emergency, security, mobility, roads, finance,
    connectivity, tourist_info, airport, events, stories, artisans, markets,
    worship, family, accessibility, weather, trips, ai_assistant, community,
    passport, business, edu, diaspora, international, bookings, messaging,
    pro_workspace, operators, verified, impact, revenue_split,
    payment_security, notifications, offline, admin, data_quality, analytics,
    integrations, privacy, home, media, reviews, ws,
)
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Création de l'application FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API pour valoriser le tourisme local au Burkina Faso - Ultra complète avec sécurité et santé",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fichiers médias téléversés (images/vidéos), servis directement par le serveur
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Événements de cycle de vie
@app.on_event("startup")
async def startup_event():
    """Exécuté au démarrage de l'application"""
    logger.info("Démarrage de l'application...")
    await connect_to_mongo()
    logger.info("Connexion à MongoDB établie")


@app.on_event("shutdown")
async def shutdown_event():
    """Exécuté à l'arrêt de l'application"""
    logger.info("Arrêt de l'application...")
    await close_mongo_connection()
    logger.info("Connexion à MongoDB maintenant fermée")


# Routes de santé
@app.get("/health", tags=["Health"])
async def health_check():
    """Vérifier l'état de l'application"""
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


# ============================================
# ROUTES AUTHENTIFICATION (TOUJOURS EN PREMIER)
# ============================================
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES EXPLORER / FICHE LIEU (§3, §4)
# ============================================
app.include_router(destinations.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES EXPÉRIENCES COMMUNAUTAIRES (§5)
# ============================================
app.include_router(experiences.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES GUIDES TOURISTIQUES (§6)
# ============================================
app.include_router(guides.router, prefix=settings.API_V1_PREFIX)
app.include_router(guide_availability.router, prefix=settings.API_V1_PREFIX + "/availability", tags=["Guide Availability"])

# ============================================
# ROUTES HÉBERGEMENTS (§7)
# ============================================
app.include_router(hotels.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES RESTAURATION — GOTOURS FOOD (§8)
# ============================================
app.include_router(cuisines.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES SANTÉ (§9)
# ============================================
app.include_router(health.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES URGENCES ET SÉCURITÉ (§10)
# ============================================
app.include_router(emergency.router, prefix=settings.API_V1_PREFIX)
app.include_router(security.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES TRANSPORT ET MOBILITÉ (§11)
# ============================================
app.include_router(mobility.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES SERVICES AUTOMOBILES ET ROUTIERS (§12)
# ============================================
app.include_router(roads.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES ARGENT, BANQUES ET PAIEMENTS (§13)
# ============================================
app.include_router(finance.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES CONNECTIVITÉ (§14)
# ============================================
app.include_router(connectivity.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES ADMINISTRATIONS ET FORMALITÉS DU VOYAGE (§15)
# ============================================
app.include_router(tourist_info.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES AÉROPORT, FRONTIÈRES ET ARRIVÉE (§16)
# ============================================
app.include_router(airport.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES ÉVÉNEMENTS ET CALENDRIER NATIONAL (§17)
# ============================================
app.include_router(events.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES CULTURE, PATRIMOINE ET MÉMOIRE (§18)
# ============================================
app.include_router(stories.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES ARTISANAT ET MARKETPLACE — GOTOURS MARKET (§19)
# ============================================
app.include_router(artisans.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES MARCHÉS ET COMMERCE LOCAL (§20)
# ============================================
app.include_router(markets.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES RELIGION, LIEUX DE CULTE ET SERVICES ASSOCIÉS (§21)
# ============================================
app.include_router(worship.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES FAMILLE, ENFANTS ET SERVICES DU QUOTIDIEN (§22)
# ============================================
app.include_router(family.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES ACCESSIBILITÉ ET INCLUSION (§23)
# ============================================
app.include_router(accessibility.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES MÉTÉO, ENVIRONNEMENT ET CONDITIONS DE VOYAGE (§24)
# ============================================
app.include_router(weather.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES ITINÉRAIRE ET PLANIFICATION (§25)
# ============================================
app.include_router(trips.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES IA — GOTOURS AI (§26)
# ============================================
app.include_router(ai_assistant.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES COMMUNAUTÉ (§27)
# ============================================
app.include_router(community.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES PASSEPORT GOTOURS ET GAMIFICATION (§28)
# ============================================
app.include_router(passport.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES TOURISME D'AFFAIRES — GOTOURS BUSINESS (§29)
# ============================================
app.include_router(business.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES TOURISME ÉDUCATIF — GOTOURS EDU (§30)
# ============================================
app.include_router(edu.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES DIASPORA ET TOURISME DE RETOUR (§31)
# ============================================
app.include_router(diaspora.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES TOURISME INTERNATIONAL (§32)
# ============================================
app.include_router(international.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES RÉSERVATION ET BILLETTERIE (§33)
# ============================================
app.include_router(bookings.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES MESSAGERIE ET RELATION CLIENT (§34)
# ============================================
app.include_router(messaging.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES ESPACE PROFESSIONNEL (§35)
# ============================================
app.include_router(pro_workspace.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES OPÉRATEURS ET PARTENAIRES TOURISTIQUES (§36)
# ============================================
app.include_router(operators.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES GOTOURS VERIFIED — CONFIANCE (§37)
# ============================================
app.include_router(verified.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES TOURISME RESPONSABLE ET IMPACT LOCAL (§38)
# ============================================
app.include_router(impact.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES « OÙ VA MON ARGENT ? » (§39)
# ============================================
app.include_router(revenue_split.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES SÉCURITÉ DES PAIEMENTS ET PROTECTION (§40)
# ============================================
app.include_router(payment_security.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES NOTIFICATIONS (§41)
# ============================================
app.include_router(notifications.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES MODE HORS CONNEXION (§42)
# ============================================
app.include_router(offline.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES ADMINISTRATION GOTOURS (§43)
# ============================================
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES DONNÉES, CARTOGRAPHIE ET QUALITÉ (§44)
# ============================================
app.include_router(data_quality.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES ANALYTICS TOURISME (§45)
# ============================================
app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES API ET INTÉGRATIONS (§46)
# ============================================
app.include_router(integrations.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES CONFIDENTIALITÉ ET GOUVERNANCE DES DONNÉES (§47)
# ============================================
app.include_router(privacy.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES ACCUEIL INTELLIGENT (§2)
# ============================================
app.include_router(home.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES MÉDIAS (upload local vers le serveur)
# ============================================
app.include_router(media.router, prefix=settings.API_V1_PREFIX)

# ============================================
# ROUTES AVIS CLIENTS (§37 GoTours Verified)
# ============================================
app.include_router(reviews.router, prefix=settings.API_V1_PREFIX)

# ============================================
# CANAL TEMPS RÉEL (messagerie + notifications)
# ============================================
app.include_router(ws.router)

# Les 47 domaines fonctionnels du cahier GoTours (§2 à §47) sont désormais
# tous reconstruits et câblés.


# Route racine
@app.get("/", tags=["Root"])
async def root():
    """Route racine - Information sur l'API"""
    return {
        "message": f"Bienvenue dans {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "description": "API complète pour tourisme Burkina Faso",
        "documentation": "/api/docs",
        "structure": {
            "auth": f"{settings.API_V1_PREFIX}/auth",
            "destinations": f"{settings.API_V1_PREFIX}/destinations",
            "experiences": f"{settings.API_V1_PREFIX}/experiences",
            "guides": f"{settings.API_V1_PREFIX}/guides",
            "hotels": f"{settings.API_V1_PREFIX}/hotels",
            "restaurants": f"{settings.API_V1_PREFIX}/restaurants",
            "health_facilities": f"{settings.API_V1_PREFIX}/health-facilities",
            "emergency_services": f"{settings.API_V1_PREFIX}/emergency-services",
            "security_alerts": f"{settings.API_V1_PREFIX}/security-alerts",
            "mobility": f"{settings.API_V1_PREFIX}/mobility",
            "roads": f"{settings.API_V1_PREFIX}/roads",
            "money_services": f"{settings.API_V1_PREFIX}/money-services",
            "connectivity": f"{settings.API_V1_PREFIX}/connectivity",
            "tourist_info": f"{settings.API_V1_PREFIX}/tourist-info",
            "airport": f"{settings.API_V1_PREFIX}/airport",
            "events": f"{settings.API_V1_PREFIX}/events",
            "culture": f"{settings.API_V1_PREFIX}/culture",
            "market": f"{settings.API_V1_PREFIX}/market",
            "marketplaces": f"{settings.API_V1_PREFIX}/marketplaces",
            "worship_places": f"{settings.API_V1_PREFIX}/worship-places",
            "family_services": f"{settings.API_V1_PREFIX}/family-services",
            "accessibility": f"{settings.API_V1_PREFIX}/accessibility",
            "weather": f"{settings.API_V1_PREFIX}/weather",
            "trips": f"{settings.API_V1_PREFIX}/trips",
            "ai": f"{settings.API_V1_PREFIX}/ai",
            "community": f"{settings.API_V1_PREFIX}/community",
            "passport": f"{settings.API_V1_PREFIX}/passport",
            "business": f"{settings.API_V1_PREFIX}/business",
            "edu": f"{settings.API_V1_PREFIX}/edu",
            "diaspora": f"{settings.API_V1_PREFIX}/diaspora",
            "international": f"{settings.API_V1_PREFIX}/international",
            "bookings": f"{settings.API_V1_PREFIX}/bookings",
            "messaging": f"{settings.API_V1_PREFIX}/messaging",
            "pro": f"{settings.API_V1_PREFIX}/pro",
            "operators": f"{settings.API_V1_PREFIX}/operators",
            "verified": f"{settings.API_V1_PREFIX}/verified",
            "impact": f"{settings.API_V1_PREFIX}/impact",
            "revenue_split": f"{settings.API_V1_PREFIX}/revenue-split",
            "payment_security": f"{settings.API_V1_PREFIX}/payment-security",
            "notifications": f"{settings.API_V1_PREFIX}/notifications",
            "offline": f"{settings.API_V1_PREFIX}/offline",
            "admin": f"{settings.API_V1_PREFIX}/admin",
            "data_quality": f"{settings.API_V1_PREFIX}/data-quality",
            "analytics": f"{settings.API_V1_PREFIX}/analytics",
            "integrations": f"{settings.API_V1_PREFIX}/integrations",
            "privacy": f"{settings.API_V1_PREFIX}/privacy",
            "home": f"{settings.API_V1_PREFIX}/home",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
