import time
from backend.task_queue import pop_from_queue
from backend.db import get_db, init_db, Fact
from backend.main import get_verdict, ClaimRequest, retrieval_system

def process_queue():
    print("Worker started. Initializing systems...")
    init_db()

    # Load facts into memory just like FastAPI startup
    db = next(get_db())
    facts = db.query(Fact).all()
    if facts:
        retrieval_system.load_facts(facts)
    db.close()

    print("Listening to VeriCheck queue...")

    while True:
        try:
            item = pop_from_queue()
            if item:
                print(f"Processing item: {item['item_id']}")
                claim = item['text']

                # Get a fresh DB session for each item
                db_session = next(get_db())

                # Process through the main pipeline
                request = ClaimRequest(claim_text=claim)
                verdict = get_verdict(request, db_session)

                db_session.close()
                print(f"Verdict for {item['item_id']}: {verdict.label} (Conf: {verdict.confidence:.2%})")

        except Exception as e:
            print(f"Worker Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    process_queue()
