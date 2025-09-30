from fastapi import APIRouter, Depends
import psutil
import time
from datetime import datetime
import sys
import os
from pathlib import Path

from api.models.schemas import HealthResponse
from dashboard.components.data_processor import ABSAProcessor

router = APIRouter()

# Temps de démarrage du serveur
start_time = time.time()

@router.get("/health", response_model=HealthResponse)
async def health_check(absa_processor: ABSAProcessor = Depends()):
    """
    Vérification de la santé du système
    
    Retourne l'état des modèles, la mémoire utilisée et le temps de fonctionnement.
    """
    try:
        # Vérification des modèles
        models_status = {
            "aspect_extraction": False,
            "sentiment_classification": False
        }
        
        # Test simple des modèles
        try:
            test_results = absa_processor.analyze_text("Test de santé")
            if test_results and len(test_results) > 0:
                models_status["aspect_extraction"] = True
                models_status["sentiment_classification"] = True
        except Exception as e:
            print(f"Erreur test modèles: {e}")
        
        # Métriques système
        memory = psutil.virtual_memory()
        memory_usage = {
            "total_gb": memory.total / (1024**3),
            "available_gb": memory.available / (1024**3),
            "used_gb": memory.used / (1024**3),
            "percent": memory.percent
        }
        
        # Temps de fonctionnement
        uptime = time.time() - start_time
        
        # Statut global
        all_models_ok = all(models_status.values())
        memory_ok = memory.percent < 90
        status = "healthy" if all_models_ok and memory_ok else "degraded"
        
        return HealthResponse(
            status=status,
            timestamp=datetime.now(),
            version="1.0.0",
            models_status=models_status,
            uptime=uptime,
            memory_usage=memory_usage
        )
        
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            version="1.0.0",
            models_status={"error": str(e)},
            uptime=time.time() - start_time,
            memory_usage={"error": "Unable to get memory info"}
        )

@router.get("/health/deep")
async def deep_health_check(absa_processor: ABSAProcessor = Depends()):
    """Vérification approfondie de la santé du système"""
    
    health_checks = {}
    
    # Test des modèles avec différents types de textes
    test_texts = [
        "Le service était excellent",
        "La nourriture était horrible",
        "Ambiance correcte, prix élevé"
    ]
    
    for i, text in enumerate(test_texts):
        try:
            start = time.time()
            results = absa_processor.analyze_text(text)
            duration = time.time() - start
            
            health_checks[f"model_test_{i+1}"] = {
                "status": "pass",
                "text": text,
                "aspects_found": len(results),
                "response_time": duration,
                "results_sample": [
                    {
                        "aspect": r.aspect,
                        "sentiment": r.sentiment,
                        "confidence": r.confidence
                    } for r in results[:3]  # Max 3 premiers résultats
                ]
            }
        except Exception as e:
            health_checks[f"model_test_{i+1}"] = {
                "status": "fail",
                "error": str(e),
                "text": text
            }
    
    # Vérifications système
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        disk_usage = psutil.disk_usage('/')
        
        health_checks["system"] = {
            "cpu_percent": cpu_percent,
            "disk_free_gb": disk_usage.free / (1024**3),
            "disk_total_gb": disk_usage.total / (1024**3),
            "python_version": sys.version,
            "platform": sys.platform
        }
    except Exception as e:
        health_checks["system"] = {"error": str(e)}
    
    # Vérification des fichiers modèles
    project_root = Path(__file__).parent.parent.parent
    models_paths = [
        "outputs/tokencls_working",
        "outputs/sentiment_simple_fixed"
    ]
    
    health_checks["model_files"] = {}
    for model_path in models_paths:
        full_path = project_root / model_path
        health_checks["model_files"][model_path] = {
            "exists": full_path.exists(),
            "is_directory": full_path.is_dir() if full_path.exists() else False,
            "files_count": len(list(full_path.glob("*"))) if full_path.exists() and full_path.is_dir() else 0
        }
    
    # Statut global
    failed_checks = sum(1 for check in health_checks.values() 
                       if isinstance(check, dict) and check.get("status") == "fail")
    
    return {
        "timestamp": datetime.now(),
        "overall_status": "healthy" if failed_checks == 0 else f"{failed_checks} checks failed",
        "detailed_checks": health_checks,
        "summary": {
            "total_checks": len(health_checks),
            "passed_checks": len(health_checks) - failed_checks,
            "failed_checks": failed_checks
        }
    }

@router.get("/health/ready")
async def readiness_check(absa_processor: ABSAProcessor = Depends()):
    """Check de préparation pour les load balancers"""
    try:
        # Test rapide des modèles
        results = absa_processor.analyze_text("Test rapide")
        if results:
            return {"status": "ready", "timestamp": datetime.now()}
        else:
            return {"status": "not ready", "reason": "Models not responding"}
    except Exception as e:
        return {"status": "not ready", "reason": str(e)}

@router.get("/health/live")
async def liveness_check():
    """Check de vivacité pour les orchestrateurs"""
    return {
        "status": "alive",
        "timestamp": datetime.now(),
        "uptime": time.time() - start_time
    }
@router.get("/debug/paths")
async def debug_paths():
    """Debug des chemins et modèles pour diagnostic"""
    import os
    from pathlib import Path
    
    current_dir = Path.cwd()
    api_dir = Path(__file__).parent.parent
    project_root = api_dir.parent
    
    debug_info = {
        "current_working_directory": str(current_dir),
        "api_directory": str(api_dir),
        "project_root": str(project_root),
        "sys_path": sys.path[:5],  # Premiers 5 éléments
        "outputs_exists": (project_root / "outputs").exists(),
        "models_check": {}
    }
    
    # Vérifier modèles
    models_to_check = [
        "outputs/tokencls_working",
        "outputs/sentiment_simple_fixed"
    ]
    
    for model_path in models_to_check:
        full_path = project_root / model_path
        debug_info["models_check"][model_path] = {
            "exists": full_path.exists(),
            "is_dir": full_path.is_dir() if full_path.exists() else False,
            "absolute_path": str(full_path.absolute()),
            "files": list(str(f) for f in full_path.glob("*")) if full_path.exists() else []
        }
    
    return debug_info
