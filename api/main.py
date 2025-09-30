import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Railway port configuration
PORT = int(os.getenv("PORT", 8000))

# Pydantic models for requests
class AnalyzeRequest(BaseModel):
    text: str
    include_probabilities: bool = False

class BatchRequest(BaseModel):
    texts: list[str]

# Create FastAPI app
app = FastAPI(
    title="ABSA Professional API",
    description="Aspect-Based Sentiment Analysis API (Fallback Mode)",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple fallback analyzer
class FallbackAnalyzer:
    def __init__(self):
        self.positive_words = ["good", "great", "excellent", "amazing", "wonderful", "perfect", "love", "best"]
        self.negative_words = ["bad", "terrible", "awful", "horrible", "hate", "worst", "disgusting"]
        self.aspects = ["service", "food", "quality", "price", "staff", "ambiance", "location"]
    
    def analyze(self, text: str):
        text_lower = text.lower()
        
        # Simple sentiment analysis
        pos_count = sum(1 for word in self.positive_words if word in text_lower)
        neg_count = sum(1 for word in self.negative_words if word in text_lower)
        
        if pos_count > neg_count:
            sentiment = "positive"
            confidence = min(0.7 + pos_count * 0.1, 0.95)
        elif neg_count > pos_count:
            sentiment = "negative"
            confidence = min(0.7 + neg_count * 0.1, 0.95)
        else:
            sentiment = "neutral"
            confidence = 0.6
        
        # Simple aspect detection
        detected_aspects = [aspect for aspect in self.aspects if aspect in text_lower]
        if not detected_aspects:
            detected_aspects = ["general"]
        
        return {
            "sentiment": sentiment,
            "confidence": round(confidence, 3),
            "aspects": detected_aspects,
            "analysis_mode": "fallback"
        }

# Initialize analyzer
analyzer = FallbackAnalyzer()

# Routes
@app.get("/")
async def root():
    return {
        "message": "ABSA Professional API - Fallback Mode",
        "version": "1.0.0",
        "status": "healthy",
        "mode": "fallback",
        "endpoints": {
            "docs": "/api/docs",
            "health": "/api/health",
            "analyze": "/api/analyze"
        }
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ABSA API",
        "mode": "fallback",
        "timestamp": datetime.now().isoformat(),
        "uptime": "running"
    }

@app.post("/api/analyze")
async def analyze_text(request: AnalyzeRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    try:
        result = analyzer.analyze(request.text)
        result["text"] = request.text
        result["timestamp"] = datetime.now().isoformat()
        
        if request.include_probabilities:
            result["probabilities"] = {
                "positive": result["confidence"] if result["sentiment"] == "positive" else 1 - result["confidence"],
                "negative": result["confidence"] if result["sentiment"] == "negative" else 1 - result["confidence"],
                "neutral": result["confidence"] if result["sentiment"] == "neutral" else 0.3
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail="Analysis failed")

@app.post("/api/batch")
async def batch_analyze(request: BatchRequest):
    if not request.texts:
        raise HTTPException(status_code=400, detail="Texts list cannot be empty")
    
    if len(request.texts) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 texts per batch")
    
    results = []
    for text in request.texts:
        if text.strip():
            result = analyzer.analyze(text)
            result["text"] = text
            results.append(result)
    
    return {
        "results": results,
        "count": len(results),
        "timestamp": datetime.now().isoformat(),
        "mode": "fallback"
    }

@app.get("/api/metrics")
async def get_metrics():
    return {
        "api_status": "healthy",
        "mode": "fallback",
        "features": {
            "sentiment_analysis": True,
            "aspect_detection": True,
            "batch_processing": True,
            "ml_models": False
        },
        "performance": {
            "response_time": "< 100ms",
            "throughput": "high"
        }
    }

if __name__ == "__main__":
    logger.info(f"🚀 Starting ABSA API in fallback mode on port {PORT}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=False
    )
