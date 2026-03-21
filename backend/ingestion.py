import time
import datetime
import uuid
import random
from backend.queue import push_to_queue

# Mock news feed to simulate social media / RSS stream
mock_feed = [
    "The new 2000 rupee notes will have a GPS tracking chip embedded in them.",
    "India has launched the Chandrayaan-4 mission successfully.",
    "The COVID-19 vaccine has been proven safe by the WHO.",
    "The sun rose in the east today.", # General statement, will be dropped by Tier 1
    "Eating garlic completely cures all forms of cancer.",
    "A local politician was seen stealing from a store.", # Unverifiable
]

def ingest_feed():
    print("Starting automated feed ingestion...")
    while True:
        claim_text = random.choice(mock_feed)
        item_id = str(uuid.uuid4())

        queue_item = {
            "item_id": item_id,
            "text": claim_text,
            "source": "automated_feed",
            "timestamp": datetime.datetime.now().isoformat()
        }

        push_to_queue(queue_item)
        print(f"Ingested item {item_id}: {claim_text[:30]}...")

        # Simulate arrival rate (e.g. 1 post every 5 seconds)
        time.sleep(5)

if __name__ == "__main__":
    ingest_feed()
