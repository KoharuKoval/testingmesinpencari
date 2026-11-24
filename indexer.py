import os
import json
import math
import time
from collections import Counter
from preprocessor import IndonesianPreprocessor

CORPUS_FILE = "data/korpus_finansial.json"
INDEX_FILE = "data/inverted_index.json"


class FinancialSearchEngine:
    def __init__(self):
        self.preprocessor = IndonesianPreprocessor()
        self.documents = {}
        self.inverted_index = {}
        self.doc_lengths = {}
        self.doc_norms = {}
        self.total_docs = 0
        self.avg_doc_len = 0.0

    def build_index(self, corpus_path: str = CORPUS_FILE, index_path: str = INDEX_FILE):
        """Membangun Inverted Index dari korpus JSON dan menyimpannya ke disk."""
        if not os.path.exists(corpus_path):
            raise FileNotFoundError(
                f"File korpus '{corpus_path}' belum ditemukan. Jalankan 'python crawler.py' terlebih dahulu."
            )

        with open(corpus_path, "r", encoding="utf-8") as f:
            corpus_list = json.load(f)

        self.total_docs = len(corpus_list)
        postings_map = {}
        total_tokens = 0

        print(f"[INDEXING] Memproses {self.total_docs} dokumen...")
        start_time = time.time()

        for doc in corpus_list:
            doc_id = str(doc["doc_id"])
            self.documents[doc_id] = doc

            weighted_text = f"{doc['title']} {doc['title']} {doc['content']}"
            tokens = self.preprocessor.preprocess(weighted_text)

            doc_len = len(tokens)
            self.doc_lengths[doc_id] = doc_len
            total_tokens += doc_len

            term_counts = Counter(tokens)
            for term, tf in term_counts.items():
                if term not in postings_map:
                    postings_map[term] = {}
                postings_map[term][doc_id] = tf

        self.avg_doc_len = total_tokens / self.total_docs if self.total_docs > 0 else 0.0
        doc_sq_sums = {doc_id: 0.0 for doc_id in self.documents}

        for term, postings in postings_map.items():
            df = len(postings)
            idf = math.log((self.total_docs + 1) / (df + 1)) + 1.0
            self.inverted_index[term] = {
                "df": df,
                "idf": idf,
                "postings": postings
            }

            for doc_id, tf in postings.items():
                tf_weight = 1.0 + math.log(tf)
                tfidf = tf_weight * idf
                doc_sq_sums[doc_id] += tfidf ** 2

        self.doc_norms = {
            doc_id: math.sqrt(sq_sum) if sq_sum > 0 else 1.0
            for doc_id, sq_sum in doc_sq_sums.items()
        }

        index_payload = {
            "total_docs": self.total_docs,
            "avg_doc_len": self.avg_doc_len,
            "doc_lengths": self.doc_lengths,
            "doc_norms": self.doc_norms,
            "inverted_index": self.inverted_index
        }

        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_payload, f, ensure_ascii=False)

        elapsed = time.time() - start_time
        print(f"[SELESAI] Inverted Index dibangun dalam {elapsed:.2f} detik "
              f"({len(self.inverted_index)} term unik) -> '{index_path}'.")

    def load_index(self, corpus_path: str = CORPUS_FILE, index_path: str = INDEX_FILE):
        """Memuat korpus dan Inverted Index yang sudah dibangun."""
        if not os.path.exists(index_path):
            self.build_index(corpus_path, index_path)
            return

        with open(corpus_path, "r", encoding="utf-8") as f:
            corpus_list = json.load(f)
            self.documents = {str(doc["doc_id"]): doc for doc in corpus_list}

        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.total_docs = data["total_docs"]
            self.avg_doc_len = data["avg_doc_len"]
            self.doc_lengths = data["doc_lengths"]
            self.doc_norms = data["doc_norms"]
            self.inverted_index = data["inverted_index"]

    def _create_snippet(self, content: str, raw_query: str, max_len: int = 220) -> str:
        lower_content = content.lower()
        terms = [t for t in raw_query.lower().split() if len(t) > 2]
        start_idx = 0
        for term in terms:
            pos = lower_content.find(term)
            if pos != -1:
                start_idx = max(0, pos - 60)
                break
        snippet = content[start_idx:start_idx + max_len].strip()
        if start_idx > 0:
            snippet = "..." + snippet
        if start_idx + max_len < len(content):
            snippet += "..."
        return snippet

    def search_tfidf(self, query: str, top_k: int = 10) -> tuple[list[dict], float]:
        """Algoritma 1: Vector Space Model (TF-IDF + Cosine Similarity)."""
        t0 = time.perf_counter()
        q_tokens = self.preprocessor.preprocess(query)
        if not q_tokens:
            return [], 0.0

        q_counts = Counter(q_tokens)
        q_weights = {}
        q_sq_sum = 0.0

        for term, tf in q_counts.items():
            if term in self.inverted_index:
                idf = self.inverted_index[term]["idf"]
                w = (1.0 + math.log(tf)) * idf
                q_weights[term] = w
                q_sq_sum += w ** 2

        q_norm = math.sqrt(q_sq_sum) if q_sq_sum > 0 else 1.0
        scores = {}

        for term, q_w in q_weights.items():
            entry = self.inverted_index[term]
            idf = entry["idf"]
            for doc_id, tf in entry["postings"].items():
                d_w = (1.0 + math.log(tf)) * idf
                scores[doc_id] = scores.get(doc_id, 0.0) + (q_w * d_w)

        ranked = []
        for doc_id, dot_product in scores.items():
            cosine_sim = dot_product / (self.doc_norms[doc_id] * q_norm)
            ranked.append((doc_id, cosine_sim))

        ranked.sort(key=lambda x: x[1], reverse=True)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        results = []
        for rank, (doc_id, score) in enumerate(ranked[:top_k], start=1):
            doc = self.documents[doc_id]
            results.append({
                "rank": rank,
                "doc_id": doc_id,
                "title": doc["title"],
                "url": doc["url"],
                "source": doc["source"],
                "date": doc["date"],
                "score": round(score, 4),
                "snippet": self._create_snippet(doc["content"], query),
                "content": doc["content"]
            })

        return results, round(elapsed_ms, 3)

    def search_bm25(self, query: str, top_k: int = 10, k1: float = 1.5, b: float = 0.75) -> tuple[list[dict], float]:
        """Algoritma 2: Okapi BM25 Probabilistic Retrieval."""
        t0 = time.perf_counter()
        q_tokens = self.preprocessor.preprocess(query)
        if not q_tokens:
            return [], 0.0

        scores = {}
        for term in set(q_tokens):
            if term not in self.inverted_index:
                continue

            entry = self.inverted_index[term]
            df = entry["df"]
            idf = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1.0)

            for doc_id, tf in entry["postings"].items():
                doc_len = self.doc_lengths[doc_id]
                denom = tf + k1 * (1.0 - b + b * (doc_len / self.avg_doc_len))
                bm25_term_score = idf * ((tf * (k1 + 1.0)) / denom)
                scores[doc_id] = scores.get(doc_id, 0.0) + bm25_term_score

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        results = []
        for rank, (doc_id, score) in enumerate(ranked[:top_k], start=1):
            doc = self.documents[doc_id]
            results.append({
                "rank": rank,
                "doc_id": doc_id,
                "title": doc["title"],
                "url": doc["url"],
                "source": doc["source"],
                "date": doc["date"],
                "score": round(score, 4),
                "snippet": self._create_snippet(doc["content"], query),
                "content": doc["content"]
            })

        return results, round(elapsed_ms, 3)


if __name__ == "__main__":
    engine = FinancialSearchEngine()
    engine.build_index()