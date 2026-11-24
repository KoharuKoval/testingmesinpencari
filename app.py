from flask import Flask, render_template, request, jsonify
from indexer import FinancialSearchEngine

app = Flask(__name__)
engine = FinancialSearchEngine()
engine.load_index()


@app.route("/")
def index():
    stats = {
        "total_docs": engine.total_docs,
        "total_terms": len(engine.inverted_index),
        "avg_doc_len": round(engine.avg_doc_len, 1)
    }
    return render_template("index.html", stats=stats)


@app.route("/api/search")
def search():
    query = request.args.get("q", "").strip()
    top_k = int(request.args.get("top_k", 10))

    if not query:
        return jsonify({"error": "Kueri pencarian tidak boleh kosong"}), 400

    tfidf_results, tfidf_time = engine.search_tfidf(query, top_k=top_k)
    bm25_results, bm25_time = engine.search_bm25(query, top_k=top_k)

    tfidf_ids = {r["doc_id"] for r in tfidf_results}
    bm25_ids = {r["doc_id"] for r in bm25_results}
    overlap_count = len(tfidf_ids.intersection(bm25_ids))

    return jsonify({
        "query": query,
        "preprocessed_tokens": engine.preprocessor.preprocess(query),
        "overlap_count": overlap_count,
        "tfidf": {
            "time_ms": tfidf_time,
            "count": len(tfidf_results),
            "results": tfidf_results
        },
        "bm25": {
            "time_ms": bm25_time,
            "count": len(bm25_results),
            "results": bm25_results
        }
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)