from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import time
from datetime import datetime
import logging
from typing import List

from api.models.schemas import AnalysisRequest, AnalysisResponse, AspectResult, ErrorResponse
from dashboard.components.data_processor import ABSAProcessor

logger = logging.getLogger(__name__)
router = APIRouter()

# Métriques globales
request_count = 0
successful_analyses = 0
failed_analyses = 0
total_processing_time = 0.0

async def log_analysis_metrics(processing_time: float, success: bool):
    """Log des métriques d'analyse"""
    global request_count, successful_analyses, failed_analyses, total_processing_time
    
    request_count += 1
    total_processing_time += processing_time
    
    if success:
        successful_analyses += 1
    else:
        failed_analyses += 1

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    absa_processor: ABSAProcessor = Depends()
):
    """
    Analyse ABSA d'un texte individuel
    
    Extrait les aspects et classifie le sentiment pour chaque aspect.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Début analyse: {request.text[:100]}...")
        
        # Analyse ABSA
        results = absa_processor.analyze_text(request.text)
        
        # Filtrage par confiance
        filtered_results = [
            result for result in results 
            if result.confidence >= request.min_confidence
        ]
        
        # Construction de la réponse
        aspects = []
        for result in filtered_results:
            probabilities = result.probabilities if request.include_probabilities else {}
            
            aspect = AspectResult(
                aspect=result.aspect,
                sentiment=result.sentiment,
                confidence=result.confidence,
                probabilities=probabilities,
                extraction_method=result.extraction_method
            )
            aspects.append(aspect)
        
        # Calcul du résumé
        if aspects:
            sentiment_counts = {}
            total_confidence = 0
            
            for aspect in aspects:
                sentiment = aspect.sentiment
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
                total_confidence += aspect.confidence
            
            summary = {
                "total_aspects": len(aspects),
                "unique_aspects": len(set(a.aspect for a in aspects)),
                "average_confidence": total_confidence / len(aspects),
                "sentiment_distribution": sentiment_counts,
                "dominant_sentiment": max(sentiment_counts.items(), key=lambda x: x[1])[0] if sentiment_counts else None
            }
        else:
            summary = {
                "total_aspects": 0,
                "unique_aspects": 0,
                "average_confidence": 0,
                "sentiment_distribution": {},
                "dominant_sentiment": None
            }
        
        processing_time = time.time() - start_time
        
        # Log des métriques en arrière-plan
        background_tasks.add_task(log_analysis_metrics, processing_time, True)
        
        response = AnalysisResponse(
            success=True,
            text=request.text,
            aspects=aspects,
            summary=summary,
            processing_time=processing_time,
            timestamp=datetime.now()
        )
        
        logger.info(f"Analyse terminée: {len(aspects)} aspects en {processing_time:.3f}s")
        return response
        
    except Exception as e:
        processing_time = time.time() - start_time
        background_tasks.add_task(log_analysis_metrics, processing_time, False)
        
        logger.error(f"Erreur analyse: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'analyse: {str(e)}"
        )

@router.get("/analyze/stats")
async def get_analysis_stats():
    """Statistiques d'analyse"""
    avg_time = total_processing_time / max(request_count, 1)
    success_rate = successful_analyses / max(request_count, 1) * 100
    
    return {
        "total_requests": request_count,
        "successful_analyses": successful_analyses,
        "failed_analyses": failed_analyses,
        "success_rate_percent": success_rate,
        "average_processing_time": avg_time,
        "timestamp": datetime.now()
    }
