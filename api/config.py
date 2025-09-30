from pathlib import Path
import os
import sys
import logging

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration des chemins
API_DIR = Path(__file__).parent
PROJECT_ROOT = API_DIR.parent

# Vérification et ajustement du répertoire de travail
if os.getcwd() != str(PROJECT_ROOT):
    logger.info(f"Changement répertoire: {os.getcwd()} -> {PROJECT_ROOT}")
    os.chdir(str(PROJECT_ROOT))

# Ajout des chemins au sys.path
paths_to_add = [
    str(PROJECT_ROOT),
    str(PROJECT_ROOT / "src"),  # Si vous avez un dossier src
    str(PROJECT_ROOT / "dashboard"),
]

for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)

MODELS_DIR = PROJECT_ROOT / "outputs"

# Chemins des modèles
ASPECT_MODEL_PATH = MODELS_DIR / "tokencls_working"
SENTIMENT_MODEL_PATH = MODELS_DIR / "sentiment_simple_fixed"

# Configuration du processeur ABSA
ABSA_CONFIG = {
    "aspect_model_path": str(ASPECT_MODEL_PATH),
    "sentiment_model_path": str(SENTIMENT_MODEL_PATH),
    "use_fallback": True,  # Utiliser fallback si modèles indisponibles
    "max_text_length": 5000,
    "batch_size": 32
}

def check_models():
    """Vérifie la présence des modèles"""
    checks = {
        "project_root": str(PROJECT_ROOT),
        "current_working_dir": os.getcwd(),
        "models_dir_exists": MODELS_DIR.exists(),
        "aspect_model_exists": ASPECT_MODEL_PATH.exists(),
        "sentiment_model_exists": SENTIMENT_MODEL_PATH.exists(),
        "aspect_model_path": str(ASPECT_MODEL_PATH),
        "sentiment_model_path": str(SENTIMENT_MODEL_PATH)
    }
    
    if MODELS_DIR.exists():
        checks["models_in_outputs"] = list(MODELS_DIR.glob("*"))
    
    if ASPECT_MODEL_PATH.exists():
        checks["aspect_model_files"] = list(ASPECT_MODEL_PATH.glob("*"))
        
    if SENTIMENT_MODEL_PATH.exists():
        checks["sentiment_model_files"] = list(SENTIMENT_MODEL_PATH.glob("*"))
    
    return checks

def setup_environment():
    """Configure l'environnement pour l'API"""
    logger.info(f"Configuration environnement API...")
    logger.info(f"Répertoire projet: {PROJECT_ROOT}")
    logger.info(f"Répertoire courant: {os.getcwd()}")
    logger.info(f"Répertoire modèles: {MODELS_DIR}")
    
    # Vérification des modèles
    model_status = check_models()
    
    for key, value in model_status.items():
        if isinstance(value, bool):
            status = "✅" if value else "❌"
            logger.info(f"{status} {key}: {value}")
        else:
            logger.info(f"📂 {key}: {value}")
    
    return model_status
