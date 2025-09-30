from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import asyncio
import time
from datetime import datetime
import logging
from typing import List, Dict, Any

from api.models.schemas import BatchRequest, BatchResponse, BatchResult, AspectResult
from dashboard.components.data_processor import ABSAProcessor
from dashboard.components.analytics import ABSAAnalytics

logger = logging.getLogger(__name__)
router = APIRouter()

async def analyze_single_text(
    text: str, 
    index: int, 
    absa_processor: ABSAProcessor,
    min_confidence: float,
    include_probabilities: bool
) -> BatchResult:
    """Analyse un texte individuel de manière asynchrone"""
    try:
        # Analyse ABSA
        results = absa_processor.analyze_text(text)
        
        # Filtrage par confiance
        filtered_results = [
            result for result in results 
            if result.confidence >= min_confidence
        ]
        
        # Construction des aspects
        aspects = []
        for result in filtered_results:
            probabilities = result.probabilities if include_probabilities else {}
            
            aspect = AspectResult(
                aspect=result.aspect,
                sentiment=result.sentiment,
                confidence=result.confidence,
                probabilities=probabilities,
                extraction_method=result.extraction_method
            )
            aspects.append(aspect)
        
        return BatchResult(
            index=index,
            text=text[:200] + ("..." if len(text) > 200 else ""),
            aspects=aspects,
            success=True,
            error=None
        )
        
    except Exception as e:
        logger.error(f"Erreur analyse texte {index}: {str(e)}")
        return BatchResult(
            index=index,
            text=text[:200] + ("..." if len(text) > 200 else ""),
            aspects=[],
            success=False,
            error=str(e)
        )

@router.post("/batch", response_model=BatchResponse)
async def analyze_batch(
    request: BatchRequest,
    background_tasks: BackgroundTasks,
    absa_processor: ABSAProcessor = Depends()
):
    """
    Analyse ABSA par lot
    
    Traite plusieurs textes en parallèle pour optimiser les performances.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Début analyse batch: {len(request.texts)} textes")
        
        # Traitement en parallèle (limité pour éviter la surcharge)
        semaphore = asyncio.Semaphore(5)  # Max 5 analyses simultanées
        
        async def bounded_analyze(text: str, index: int):
            async with semaphore:
                return await analyze_single_text(
                    text, index, absa_processor,
                    request.min_confidence,
                    request.include_probabilities
                )
        
        # Lancer toutes les analyses
        tasks = [
            bounded_analyze(text, idx) 
            for idx, text in enumerate(request.texts)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Traiter les résultats
        valid_results = []
        successful_count = 0
        failed_count = 0
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Exception dans batch: {result}")
                failed_count += 1
            elif isinstance(result, BatchResult):
                valid_results.append(result)
                if result.success:
                    successful_count += 1
                else:
                    failed_count += 1
        
        # Calculer le résumé global
        all_aspects = []
        for result in valid_results:
            if result.success:
                all_aspects.extend(result.aspects)
        
        if all_aspects:
            # Utiliser ABSAAnalytics pour calculer le résumé
            import pandas as pd
            
            # Convertir en DataFrame pour analytics
            df_data = []
            for result in valid_results:
                for aspect in result.aspects:
                    df_data.append({
                        'text': result.text,
                        'aspect': aspect.aspect,
                        'sentiment': aspect.sentiment,
                        'confidence': aspect.confidence
                    })
            
            if df_data:
                df = pd.DataFrame(df_data)
                metrics = ABSAAnalytics.compute_basic_metrics(df)
                scores = ABSAAnalytics.calculate_sentiment_scores(df)
                
                summary = {
                    "total_aspects": metrics.total_aspects,
                    "unique_aspects": metrics.unique_aspects,
                    "average_confidence": metrics.avg_confidence,
                    "satisfaction_score": scores['satisfaction_score'],
                    "sentiment_distribution": {
                        "positive": scores['positivity_rate'],
                        "negative": scores['negativity_rate'],
                        "neutral": scores['neutrality_rate']
                    },
                    "top_aspects": df['aspect'].value_counts().head(5).to_dict()
                }
            else:
                summary = {"message": "Aucun aspect identifié"}
        else:
            summary = {"message": "Aucune analyse réussie"}
        
        processing_time = time.time() - start_time
        
        response = BatchResponse(
            success=True,
            total_texts=len(request.texts),
            successful_analyses=successful_count,
            failed_analyses=failed_count,
            results=valid_results,
            summary=summary,
            processing_time=processing_time,
            timestamp=datetime.now()
        )
        
        logger.info(
            f"Batch terminé: {successful_count}/{len(request.texts)} réussis "
            f"en {processing_time:.3f}s"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Erreur batch: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'analyse batch: {str(e)}"
        )

@router.get("/batch/limits")
async def get_batch_limits():
    """Limites et recommandations pour l'analyse batch"""
    return {
        "max_texts_per_request": 100,
        "max_text_length": 5000,
        "recommended_batch_size": 20,
        "concurrent_analyses": 5,
        "estimated_time_per_text": "0.1-0.5 seconds",
        "tips": [
            "Utilisez des lots de 10-20 textes pour des performances optimales",
            "Les textes plus longs prennent plus de temps à traiter",
            "Ajustez min_confidence pour filtrer les résultats peu fiables"
        ]
    }
