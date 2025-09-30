from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
import uvicorn
import sys
import os
from pathlib import Path
import logging
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager

PORT = int(os.getenv("PORT", 8000))
# CORRECTION: Configuration des chemins AVANT les imports
api_dir = Path(__file__).parent
project_root = api_dir.parent

# Ajouter les chemins nécessaires
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(api_dir))

# Changer le répertoire de travail
os.chdir(str(project_root))

# NOUVEAU: Configuration directe (sans api.config)
MODELS_BASE_PATH = project_root / "outputs"
ASPECT_MODEL_PATH = MODELS_BASE_PATH / "tokencls_working"
SENTIMENT_MODEL_PATH = MODELS_BASE_PATH / "sentiment_simple_fixed"

def setup_environment():
    """Configure l'environnement pour l'API"""
    logger.info(f"🔍 Configuration environnement API...")
    logger.info(f"📁 Répertoire projet: {project_root}")
    logger.info(f"📁 Répertoire courant: {os.getcwd()}")
    logger.info(f"📁 Répertoire modèles: {MODELS_BASE_PATH}")
    
    model_status = {
        "project_root": str(project_root),
        "current_working_dir": os.getcwd(),
        "models_dir_exists": MODELS_BASE_PATH.exists(),
        "aspect_model_exists": ASPECT_MODEL_PATH.exists(),
        "sentiment_model_exists": SENTIMENT_MODEL_PATH.exists(),
    }
    
    for key, value in model_status.items():
        if isinstance(value, bool):
            status = "✅" if value else "❌"
            logger.info(f"{status} {key}: {value}")
        else:
            logger.info(f"📂 {key}: {value}")
    
    return model_status

# Configuration de l'environnement
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
model_status = setup_environment()

# Maintenant importer les modules du projet
try:
    from dashboard.components.data_processor import ABSAProcessor
    from dashboard.components.analytics import ABSAAnalytics
    MODELS_AVAILABLE = True
    logger.info("✅ Modules ABSA importés avec succès")
except ImportError as e:
    logger.error(f"❌ Erreur import modules ABSA: {e}")
    MODELS_AVAILABLE = False

# Imports locaux (sans api.)
try:
    from endpoints import analysis, batch, health, metrics
    from models.schemas import *
    logger.info("✅ Modules API importés avec succès")
except ImportError as e:
    logger.error(f"❌ Erreur import modules API: {e}")

# Variables globales
absa_processor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie de l'application"""
    global absa_processor
    
    # Startup
    logger.info("🚀 Initialisation du serveur ABSA API...")
    logger.info(f"📊 Statut modèles: {model_status}")
    
    try:
        if MODELS_AVAILABLE:
            absa_processor = ABSAProcessor()
            success = absa_processor.initialize_models()
            if success:
                logger.info("✅ Modèles ABSA chargés avec succès")
            else:
                logger.warning("⚠️ Modèles ABSA en mode fallback")
        else:
            logger.warning("⚠️ Modules ABSA non disponibles - API en mode dégradé")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Erreur initialisation: {e}")
        yield
    finally:
        # Shutdown
        logger.info("🛑 Arrêt du serveur ABSA API")

# Création de l'application FastAPI
app = FastAPI(
    title="ABSA Professional API",
    description="API REST pour l'analyse de sentiment par aspects",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de logging des requêtes
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds()
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    return response

# Routes principales
@app.get("/", response_model=dict)
async def root():
    """Page d'accueil de l'API"""
    return {
        "message": "ABSA Professional API",
        "version": "1.0.0",
        "status": "active",
        "timestamp": datetime.now().isoformat(),
        "models_status": model_status,
        "endpoints": {
            "docs": "/api/docs",
            "health": "/api/health",
            "analyze": "/api/analyze",
            "batch": "/api/batch",
            "metrics": "/api/metrics"
        }
    }

# Fonction pour obtenir le processeur ABSA
def get_absa_processor():
    """Dépendance pour obtenir le processeur ABSA"""
    if absa_processor is None:
        raise HTTPException(
            status_code=503,
            detail="Service non disponible - Modèles ABSA non initialisés"
        )
    return absa_processor

# Inclusion des routers (si disponibles)
try:
    app.include_router(
        analysis.router,
        prefix="/api",
        tags=["Analysis"],
        dependencies=[Depends(get_absa_processor)]
    )
    
    app.include_router(
        batch.router,
        prefix="/api",
        tags=["Batch Processing"]
    )
    
    app.include_router(
        health.router,
        prefix="/api",
        tags=["Health & Status"]
    )
    
    app.include_router(
        metrics.router,
        prefix="/api",
        tags=["Metrics & Monitoring"]
    )
    
    logger.info("✅ Tous les routers inclus avec succès")
    
except Exception as e:
    logger.error(f"❌ Erreur inclusion routers: {e}")

# Gestionnaire d'erreurs global
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Erreur non gérée: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Erreur interne du serveur", "detail": str(exc)}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,  # ← MODIFIÉ: utilise PORT de Railway
        reload=False,  # ← MODIFIÉ: pas de reload en production
        log_level="info"
    )