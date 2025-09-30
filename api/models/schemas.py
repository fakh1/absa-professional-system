from pydantic import BaseModel, validator, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class SentimentEnum(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

class AnalysisRequest(BaseModel):
    """Requête d'analyse individuelle"""
    text: str = Field(..., min_length=1, max_length=5000, description="Texte à analyser")
    include_probabilities: bool = Field(True, description="Inclure les probabilités")
    min_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confiance minimale")
    
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Le texte ne peut pas être vide')
        return v.strip()

class AspectResult(BaseModel):
    """Résultat pour un aspect"""
    aspect: str = Field(..., description="Aspect identifié")
    sentiment: SentimentEnum = Field(..., description="Sentiment de l'aspect")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confiance du modèle")
    probabilities: Dict[str, float] = Field(..., description="Probabilités par sentiment")
    extraction_method: str = Field(..., description="Méthode d'extraction")

class AnalysisResponse(BaseModel):
    """Réponse d'analyse"""
    success: bool = Field(True, description="Statut de l'analyse")
    text: str = Field(..., description="Texte analysé")
    aspects: List[AspectResult] = Field(..., description="Résultats par aspect")
    summary: Dict[str, Any] = Field(..., description="Résumé global")
    processing_time: float = Field(..., description="Temps de traitement (secondes)")
    timestamp: datetime = Field(default_factory=datetime.now, description="Horodatage")

class BatchRequest(BaseModel):
    """Requête d'analyse par lot"""
    texts: List[str] = Field(..., min_items=1, max_items=100, description="Liste des textes")
    include_probabilities: bool = Field(True, description="Inclure les probabilités")
    min_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confiance minimale")
    
    @validator('texts')
    def validate_texts(cls, v):
        if not all(text.strip() for text in v):
            raise ValueError('Tous les textes doivent être non vides')
        return [text.strip() for text in v]

class BatchResult(BaseModel):
    """Résultat d'analyse par lot pour un texte"""
    index: int = Field(..., description="Index du texte")
    text: str = Field(..., description="Texte analysé")
    aspects: List[AspectResult] = Field(..., description="Aspects identifiés")
    success: bool = Field(True, description="Statut de l'analyse")
    error: Optional[str] = Field(None, description="Message d'erreur si échec")

class BatchResponse(BaseModel):
    """Réponse d'analyse par lot"""
    success: bool = Field(True, description="Statut global")
    total_texts: int = Field(..., description="Nombre total de textes")
    successful_analyses: int = Field(..., description="Analyses réussies")
    failed_analyses: int = Field(..., description="Analyses échouées")
    results: List[BatchResult] = Field(..., description="Résultats détaillés")
    summary: Dict[str, Any] = Field(..., description="Résumé global")
    processing_time: float = Field(..., description="Temps total de traitement")
    timestamp: datetime = Field(default_factory=datetime.now, description="Horodatage")

class HealthResponse(BaseModel):
    """Réponse de santé du système"""
    status: str = Field(..., description="Statut du service")
    timestamp: datetime = Field(default_factory=datetime.now, description="Horodatage")
    version: str = Field("1.0.0", description="Version de l'API")
    models_status: Dict[str, bool] = Field(..., description="Statut des modèles")
    uptime: float = Field(..., description="Temps de fonctionnement (secondes)")
    memory_usage: Dict[str, float] = Field(..., description="Usage mémoire")

class MetricsResponse(BaseModel):
    """Réponse des métriques système"""
    timestamp: datetime = Field(default_factory=datetime.now, description="Horodatage")
    requests_total: int = Field(..., description="Nombre total de requêtes")
    requests_successful: int = Field(..., description="Requêtes réussies")
    requests_failed: int = Field(..., description="Requêtes échouées")
    average_response_time: float = Field(..., description="Temps de réponse moyen")
    models_loaded: bool = Field(..., description="Statut des modèles")
    system_metrics: Dict[str, Any] = Field(..., description="Métriques système")

class ErrorResponse(BaseModel):
    """Réponse d'erreur standard"""
    error: str = Field(..., description="Type d'erreur")
    detail: str = Field(..., description="Détail de l'erreur")
    timestamp: datetime = Field(default_factory=datetime.now, description="Horodatage")
    request_id: Optional[str] = Field(None, description="ID de la requête")
