import time
from backend.queue import pop_from_queue
from backend.db import get_db
from backend.main import get_verdict, ClaimRequest

def process_queue():
    print("Worker started. Listening to VeriCheck queue...")
    # Initialize DB connection generator
    db_gen = get_db()

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
