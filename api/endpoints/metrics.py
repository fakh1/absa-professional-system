from fastapi import APIRouter, Response
import time
import psutil
from datetime import datetime
from collections import defaultdict
import json

from api.models.schemas import MetricsResponse

router = APIRouter()

# Stockage des métriques en mémoire (en production, utiliser Redis/DB)
metrics_storage = {
    "requests_total": 0,
    "requests_successful": 0,
    "requests_failed": 0,
    "response_times": [],
    "start_time": time.time()
}

endpoint_metrics = defaultdict(lambda: {
    "requests": 0,
    "success": 0,
    "errors": 0,
    "total_time": 0.0
})

@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Métriques détaillées du système"""
    
    # Métriques système
    memory = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent()
    
    # Calcul temps de réponse moyen
    avg_response_time = (
        sum(metrics_storage["response_times"]) / 
        max(len(metrics_storage["response_times"]), 1)
    )
    
    # Métriques par endpoint
    endpoints_stats = {}
    for endpoint, stats in endpoint_metrics.items():
        endpoints_stats[endpoint] = {
            "requests": stats["requests"],
            "success_rate": stats["success"] / max(stats["requests"], 1) * 100,
            "avg_response_time": stats["total_time"] / max(stats["requests"], 1),
            "errors": stats["errors"]
        }
    
    system_metrics = {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "memory_available_gb": memory.available / (1024**3),
        "uptime_seconds": time.time() - metrics_storage["start_time"],
        "endpoints": endpoints_stats
    }
    
    return MetricsResponse(
        timestamp=datetime.now(),
        requests_total=metrics_storage["requests_total"],
        requests_successful=metrics_storage["requests_successful"],
        requests_failed=metrics_storage["requests_failed"],
        average_response_time=avg_response_time,
        models_loaded=True,  # À améliorer avec vérification réelle
        system_metrics=system_metrics
    )

@router.get("/metrics/prometheus")
async def prometheus_metrics():
    """Métriques au format Prometheus"""
    
    # Métriques système
    memory = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent()
    
    # Format Prometheus
    metrics_text = f"""# HELP absa_requests_total Total number of requests
# TYPE absa_requests_total counter
absa_requests_total {metrics_storage["requests_total"]}

# HELP absa_requests_successful Total number of successful requests
# TYPE absa_requests_successful counter
absa_requests_successful {metrics_storage["requests_successful"]}

# HELP absa_requests_failed Total number of failed requests
# TYPE absa_requests_failed counter
absa_requests_failed {metrics_storage["requests_failed"]}

# HELP absa_response_time_seconds Average response time in seconds
# TYPE absa_response_time_seconds gauge
absa_response_time_seconds {sum(metrics_storage["response_times"]) / max(len(metrics_storage["response_times"]), 1)}

# HELP system_memory_percent Memory usage percentage
# TYPE system_memory_percent gauge
system_memory_percent {memory.percent}

# HELP system_cpu_percent CPU usage percentage
# TYPE system_cpu_percent gauge
system_cpu_percent {cpu_percent}

# HELP absa_uptime_seconds Service uptime in seconds
# TYPE absa_uptime_seconds counter
absa_uptime_seconds {time.time() - metrics_storage["start_time"]}
"""

    # Métriques par endpoint
    for endpoint, stats in endpoint_metrics.items():
        endpoint_clean = endpoint.replace("/", "_").replace("-", "_")
        metrics_text += f"""
# HELP absa_endpoint_requests_total Total requests for endpoint {endpoint}
# TYPE absa_endpoint_requests_total counter
absa_endpoint_requests_total{{endpoint="{endpoint}"}} {stats["requests"]}

# HELP absa_endpoint_errors_total Total errors for endpoint {endpoint}  
# TYPE absa_endpoint_errors_total counter
absa_endpoint_errors_total{{endpoint="{endpoint}"}} {stats["errors"]}
"""

    return Response(content=metrics_text, media_type="text/plain")

@router.post("/metrics/record")
async def record_metric(endpoint: str, response_time: float, success: bool):
    """Enregistrer une métrique (utilisé par les middlewares)"""
    
    # Métriques globales
    metrics_storage["requests_total"] += 1
    metrics_storage["response_times"].append(response_time)
    
    # Limiter la taille de l'historique
    if len(metrics_storage["response_times"]) > 1000:
        metrics_storage["response_times"] = metrics_storage["response_times"][-500:]
    
    if success:
        metrics_storage["requests_successful"] += 1
    else:
        metrics_storage["requests_failed"] += 1
    
    # Métriques par endpoint
    endpoint_metrics[endpoint]["requests"] += 1
    endpoint_metrics[endpoint]["total_time"] += response_time
    
    if success:
        endpoint_metrics[endpoint]["success"] += 1
    else:
        endpoint_metrics[endpoint]["errors"] += 1
    
    return {"status": "recorded"}

@router.get("/metrics/dashboard")
async def metrics_dashboard():
    """Données pour dashboard de monitoring"""
    
    # Historique des 100 derniers temps de réponse
    recent_times = metrics_storage["response_times"][-100:]
    
    # Métriques par minute (simulation)
    now = datetime.now()
    timeline = []
    for i in range(10):
        timeline.append({
            "timestamp": (now - timedelta(minutes=i)).isoformat(),
            "requests": max(0, metrics_storage["requests_total"] - i * 10),
            "avg_response_time": sum(recent_times[-10*(i+1):-10*i]) / max(10, 1) if recent_times else 0
        })
    
    return {
        "current_metrics": await get_metrics(),
        "timeline": timeline,
        "top_endpoints": dict(sorted(
            endpoint_metrics.items(), 
            key=lambda x: x[1]["requests"], 
            reverse=True
        )[:5])
    }

@router.delete("/metrics/reset")
async def reset_metrics():
    """Réinitialiser les métriques (dev/test seulement)"""
    global metrics_storage, endpoint_metrics
    
    metrics_storage = {
        "requests_total": 0,
        "requests_successful": 0,
        "requests_failed": 0,
        "response_times": [],
        "start_time": time.time()
    }
    endpoint_metrics.clear()
    
    return {"status": "metrics_reset", "timestamp": datetime.now()}
