from backend.db import get_db, init_db, Fact
from sentence_transformers import SentenceTransformer
import datetime

def seed():
    init_db()
    db = next(get_db())

    # check if facts exist
    existing = db.query(Fact).first()
    if existing:
        print("Facts already seeded.")
        return

    embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    facts = [
        {
            "text": "The Prime Minister inaugurated the XYZ bridge on January 15, 2024.",
            "source": "pib.gov.in",
            "date": datetime.date(2024, 1, 15)
        },
        {
            "text": "The COVID-19 vaccine has been proven safe and does not cause infertility according to the WHO.",
            "source": "who.int",
            "date": datetime.date(2024, 1, 10)
        },
        {
            "text": "The RBI has announced that Rs 2000 notes remain legal tender until further notice.",
            "source": "rbi.org.in",
            "date": datetime.date(2023, 12, 1)
        }
    ]

    for fact_data in facts:
        embedding = embedder.encode(fact_data["text"]).tolist()
        fact = Fact(
            text=fact_data["text"],
            source=fact_data["source"],
            date=fact_data["date"],
            embedding=embedding
        )
        db.add(fact)

    db.commit()
    print("Database seeded with verified facts.")

if __name__ == "__main__":
    seed()
