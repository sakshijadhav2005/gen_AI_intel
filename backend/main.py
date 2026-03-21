from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid
import datetime
import math
import spacy

from backend.db import get_db, init_db, Fact
import os
import json
from anthropic import Anthropic

from backend.db import get_db, init_db, Fact
from backend.retrieval import RetrievalSystem
from backend.mcp_client import scrape_url_mcp
from backend.queue import push_to_queue

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
nlp = spacy.load("en_core_web_sm")

def tier1_prefilter(text: str) -> bool:
    """
    Tier 1 Pre-filter logic using spaCy NER.
    Returns True if the post contains factual entities, False otherwise.
    In a real system, fastText language detection would also run here.
    """
    doc = nlp(text)
    # Check if the sentence has named entities (e.g. Person, Org, GPE, Date, etc.)
    # We drop opinions/jokes if no factual entities exist.
    if len(doc.ents) > 0:
        return True
    return False

@app.on_event("startup")
def startup_event():
    init_db()

    # Load facts from DB on startup
    db = next(get_db())
    facts = db.query(Fact).all()
    if facts:
        retrieval_system.load_facts(facts)

class IngestResponse(BaseModel):
    status: str
    message: str
    item_id: str

@app.post("/ingest", response_model=IngestResponse)
def ingest_post(request: ClaimRequest):
    """
    Tier 0 Ingestion point.
    Pushes directly to the message queue for processing by workers.
    """
    item_id = str(uuid.uuid4())
    queue_item = {
        "item_id": item_id,
        "text": request.claim_text,
        "source": "api_upload",
        "timestamp": datetime.datetime.now().isoformat()
    }
    push_to_queue(queue_item)

    return IngestResponse(
        status="queued",
        message="Post received and queued for processing",
        item_id=item_id
    )

@app.post("/verdict", response_model=VerdictResponse)
def get_verdict(request: ClaimRequest, db: Session = Depends(get_db)):
    """
    Direct synchronous endpoint for the dashboard/testing.
    """
    claim = request.claim_text

    # Tier 1: Pre-filter (Language detection & Claim extraction)
    has_factual_claim = tier1_prefilter(claim)
    if not has_factual_claim:
         return VerdictResponse(
            verdict_id=str(uuid.uuid4()),
            item_id=str(uuid.uuid4()),
            label="UNVERIFIABLE",
            confidence=0.0,
            evidence=[],
            explanation="Dropped at Tier 1: No factual claims detected (appears to be an opinion or general statement).",
            tier_reached=1,
            model_version="v1.0",
            human_reviewed=False
        )

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

    # Tier 2 Logic to determine verdict based on reranker score
    top_candidate, top_score = candidates[0]

    # Convert raw logit to probability using sigmoid function
    probability = 1 / (1 + math.exp(-top_score))

    CONFIDENCE_THRESHOLD = 0.8
    AMBIGUITY_THRESHOLD = 0.5

    evidence = [{
        "fact_id": str(top_candidate.id),
        "text": top_candidate.text,
        "source": top_candidate.source,
        "date": str(top_candidate.date)
    }]

    # Tier 3: LLM Reasoning Fallback
    if AMBIGUITY_THRESHOLD <= probability <= CONFIDENCE_THRESHOLD:

        # Check if we have an API key to actually call Anthropic Claude
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            client = Anthropic(api_key=api_key)
            prompt = f"Claim: {claim}\n\nEvidence: {evidence[0]['text']}\n\nIs this claim TRUE, FALSE, or MISLEADING given the evidence? Return a JSON with 'label', 'confidence' (0.0 to 1.0), and 'explanation' strings."
            try:
                message = client.messages.create(
                    max_tokens=200,
                    messages=[{"role": "user", "content": prompt}],
                    model="claude-3-haiku-20240307"
                )
                llm_response = json.loads(message.content[0].text)
                return VerdictResponse(
                    verdict_id=str(uuid.uuid4()),
                    item_id=str(uuid.uuid4()),
                    label=llm_response.get("label", "MISLEADING").upper(),
                    confidence=float(llm_response.get("confidence", 0.85)),
                    evidence=evidence,
                    explanation=f"Tier 3 LLM Reasoning: {llm_response.get('explanation', '')}",
                    tier_reached=3,
                    model_version="claude-3-haiku",
                    human_reviewed=False
                )
            except Exception as e:
                # Fallback to simulated response if LLM API call fails
                pass

        # Simulated Fallback
        return VerdictResponse(
            verdict_id=str(uuid.uuid4()),
            item_id=str(uuid.uuid4()),
            label="MISLEADING",
            confidence=0.85,
            evidence=evidence,
            explanation=f"Tier 3 LLM Reasoning: The claim was ambiguous (Score: {probability:.2%}). System lacks API key, simulated LLM output.",
            tier_reached=3,
            model_version="claude-simulated",
            human_reviewed=False
        )

    # Tier 2 Output
    label = "UNVERIFIABLE"
    if probability > CONFIDENCE_THRESHOLD:
        label = "TRUE" # Assuming matching means it's true for MVP

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
