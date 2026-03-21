from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid
import datetime
import math

from backend.db import get_db, init_db, Fact
from backend.retrieval import RetrievalSystem
from backend.mcp_client import scrape_url_mcp

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ClaimRequest(BaseModel):
    claim_text: str

class VerdictResponse(BaseModel):
    verdict_id: str
    item_id: str
    label: str
    confidence: float
    evidence: list
    explanation: str
    tier_reached: int
    model_version: str
    human_reviewed: bool

class ScrapeRequest(BaseModel):
    url: str

class ScrapeResponse(BaseModel):
    scraped_text: str

# Initialize systems
retrieval_system = RetrievalSystem()

@app.on_event("startup")
def startup_event():
    init_db()

    # Load facts from DB on startup
    db = next(get_db())
    facts = db.query(Fact).all()
    if facts:
        retrieval_system.load_facts(facts)

@app.post("/verdict", response_model=VerdictResponse)
def get_verdict(request: ClaimRequest, db: Session = Depends(get_db)):
    claim = request.claim_text

    # Tier 2: Hybrid Retrieval and Ranking
    candidates = retrieval_system.search(claim, top_k=5)

    if not candidates:
        return VerdictResponse(
            verdict_id=str(uuid.uuid4()),
            item_id=str(uuid.uuid4()),
            label="UNVERIFIABLE",
            confidence=0.0,
            evidence=[],
            explanation="No matching verified facts found.",
            tier_reached=2,
            model_version="v1.0",
            human_reviewed=False
        )

    # Simple logic to determine verdict based on reranker score
    top_candidate, top_score = candidates[0]

    # Convert raw logit to probability using sigmoid function
    probability = 1 / (1 + math.exp(-top_score))

    CONFIDENCE_THRESHOLD = 0.8

    label = "UNVERIFIABLE"
    if probability > CONFIDENCE_THRESHOLD:
        label = "TRUE" # Assuming matching means it's true for MVP

    evidence = [{
        "fact_id": str(top_candidate.id),
        "text": top_candidate.text,
        "source": top_candidate.source,
        "date": str(top_candidate.date)
    }]

    return VerdictResponse(
        verdict_id=str(uuid.uuid4()),
        item_id=str(uuid.uuid4()),
        label=label,
        confidence=probability,
        evidence=evidence,
        explanation=f"Top fact matched with confidence {probability:.2%}",
        tier_reached=2,
        model_version="v1.0",
        human_reviewed=False
    )

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_endpoint(request: ScrapeRequest):
    try:
        text = await scrape_url_mcp(request.url)
        # Limit text length just for safety in MVP
        if len(text) > 2000:
            text = text[:2000] + "... (truncated)"
        return ScrapeResponse(scraped_text=text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
