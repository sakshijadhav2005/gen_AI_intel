import numpy as np
import faiss
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder

# Load models
embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

class RetrievalSystem:
    def __init__(self):
        self.facts = []
        self.bm25 = None
        self.faiss_index = None

    def load_facts(self, facts_list):
        """Loads facts into BM25 and FAISS index"""
        self.facts = facts_list
        if not self.facts:
            return

        # Initialize BM25
        tokenized_corpus = [fact.text.lower().split(" ") for fact in self.facts]
        self.bm25 = BM25Okapi(tokenized_corpus)

        # Initialize FAISS
        dimension = 384 # paraphrase-multilingual-MiniLM-L12-v2 dim
        self.faiss_index = faiss.IndexFlatL2(dimension)
        embeddings = np.array([np.array(fact.embedding, dtype=np.float32) for fact in self.facts])
        if len(embeddings) > 0:
            self.faiss_index.add(embeddings)

    def search(self, claim_text, top_k=5):
        if not self.facts:
            return []

        # 1. BM25 Search
        tokenized_query = claim_text.lower().split(" ")
        bm25_scores = self.bm25.get_scores(tokenized_query)
        top_bm25_idx = np.argsort(bm25_scores)[::-1][:top_k]

        # 2. FAISS Semantic Search
        claim_embedding = embedder.encode([claim_text])[0]
        distances, indices = self.faiss_index.search(np.array([claim_embedding]), top_k)
        top_faiss_idx = indices[0]

        # Merge candidates
        candidate_indices = set(top_bm25_idx).union(set(top_faiss_idx))
        candidates = [self.facts[i] for i in candidate_indices if i != -1]

        if not candidates:
            return []

        # 3. Cross-Encoder Reranking
        pairs = [[claim_text, candidate.text] for candidate in candidates]
        rerank_scores = reranker.predict(pairs)

        # Sort by rerank score
        scored_candidates = sorted(zip(candidates, rerank_scores), key=lambda x: x[1], reverse=True)
        return scored_candidates
