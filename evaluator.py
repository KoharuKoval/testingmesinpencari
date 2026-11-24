import os
import csv
import numpy as np
import matplotlib.pyplot as plt
from indexer import FinancialSearchEngine

TEST_QUERIES = [
    {"query": "cara mengatur gaji bulanan", "must_terms": ["gaji", "atur"]},
    {"query": "tips menabung dana darurat", "must_terms": ["dana", "darurat"]},
    {"query": "investasi reksadana untuk pemula", "must_terms": ["reksadana"]},
    {"query": "cara melunasi utang dan cicilan", "must_terms": ["utang"]},
    {"query": "investasi saham untuk pemula", "must_terms": ["saham", "investasi"]},
    {"query": "tips hemat pengeluaran harian", "must_terms": ["hemat", "uang"]},
    {"query": "investasi emas jangka panjang", "must_terms": ["emas", "investasi"]},
    {"query": "cara menabung untuk beli rumah", "must_terms": ["tabung", "rumah"]},
    {"query": "manfaat asuransi kesehatan dan jiwa", "must_terms": ["asuransi"]},
    {"query": "persiapan dana pensiun dini", "must_terms": ["pensiun"]}
]


def build_ground_truth(engine: FinancialSearchEngine, must_terms: list[str]) -> set[str]:
    relevant_ids = set()
    for doc_id, doc in engine.documents.items():
        tokens = set(engine.preprocessor.preprocess(f"{doc['title']} {doc['content']}"))
        if all(term in tokens for term in must_terms):
            relevant_ids.add(doc_id)
    return relevant_ids


def compute_metrics(retrieved_ids: list[str], relevant_ids: set[str], k: int = 5) -> dict:
    if not relevant_ids:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "ap": 0.0, "rr": 0.0}

    top_k_ids = retrieved_ids[:k]
    hits = [1 if doc_id in relevant_ids else 0 for doc_id in top_k_ids]

    precision = sum(hits) / k
    recall = sum(hits) / len(relevant_ids)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    cum_hits = 0
    precisions_at_hits = []
    for idx, is_rel in enumerate(hits, start=1):
        if is_rel:
            cum_hits += 1
            precisions_at_hits.append(cum_hits / idx)
    ap = sum(precisions_at_hits) / min(len(relevant_ids), k) if precisions_at_hits else 0.0

    rr = 0.0
    for idx, is_rel in enumerate(hits, start=1):
        if is_rel:
            rr = 1.0 / idx
            break

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "ap": round(ap, 4),
        "rr": round(rr, 4)
    }


def run_evaluation():
    os.makedirs("evaluation", exist_ok=True)
    engine = FinancialSearchEngine()
    engine.load_index()

    rows = []
    tfidf_summary = {"precision": [], "recall": [], "f1": [], "ap": [], "rr": [], "time": []}
    bm25_summary = {"precision": [], "recall": [], "f1": [], "ap": [], "rr": [], "time": []}

    print("=" * 85)
    print(f"{'QUERY':<35} | {'REL':<4} | {'TF-IDF P@5 / MAP':<18} | {'BM25 P@5 / MAP':<18}")
    print("=" * 85)

    for item in TEST_QUERIES:
        q = item["query"]
        rel_docs = build_ground_truth(engine, item["must_terms"])

        res_tfidf, time_tfidf = engine.search_tfidf(q, top_k=10)
        res_bm25, time_bm25 = engine.search_bm25(q, top_k=10)

        m_tfidf = compute_metrics([r["doc_id"] for r in res_tfidf], rel_docs, k=5)
        m_bm25 = compute_metrics([r["doc_id"] for r in res_bm25], rel_docs, k=5)

        for key in ["precision", "recall", "f1", "ap", "rr"]:
            tfidf_summary[key].append(m_tfidf[key])
            bm25_summary[key].append(m_bm25[key])
        tfidf_summary["time"].append(time_tfidf)
        bm25_summary["time"].append(time_bm25)

        print(f"{q:<35} | {len(rel_docs):<4} | "
              f"{m_tfidf['precision']:.2f} / {m_tfidf['ap']:.2f} ({time_tfidf:.1f}ms) | "
              f"{m_bm25['precision']:.2f} / {m_bm25['ap']:.2f} ({time_bm25:.1f}ms)")

        rows.append({
            "Query": q,
            "Jumlah_Relevan": len(rel_docs),
            "TFIDF_Precision@5": m_tfidf["precision"],
            "TFIDF_Recall@5": m_tfidf["recall"],
            "TFIDF_F1@5": m_tfidf["f1"],
            "TFIDF_MAP@5": m_tfidf["ap"],
            "TFIDF_MRR": m_tfidf["rr"],
            "TFIDF_Latency_ms": time_tfidf,
            "BM25_Precision@5": m_bm25["precision"],
            "BM25_Recall@5": m_bm25["recall"],
            "BM25_F1@5": m_bm25["f1"],
            "BM25_MAP@5": m_bm25["ap"],
            "BM25_MRR": m_bm25["rr"],
            "BM25_Latency_ms": time_bm25
        })

    csv_path = "evaluation/hasil_evaluasi.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    metrics_labels = ["Precision@5", "Recall@5", "F1-Score@5", "MAP@5", "MRR"]
    tfidf_means = [
        np.mean(tfidf_summary["precision"]),
        np.mean(tfidf_summary["recall"]),
        np.mean(tfidf_summary["f1"]),
        np.mean(tfidf_summary["ap"]),
        np.mean(tfidf_summary["rr"])
    ]
    bm25_means = [
        np.mean(bm25_summary["precision"]),
        np.mean(bm25_summary["recall"]),
        np.mean(bm25_summary["f1"]),
        np.mean(bm25_summary["ap"]),
        np.mean(bm25_summary["rr"])
    ]

    x = np.arange(len(metrics_labels))
    width = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    rects1 = ax1.bar(x - width / 2, tfidf_means, width, label="TF-IDF (VSM)", color="#3b82f6")
    rects2 = ax1.bar(x + width / 2, bm25_means, width, label="Okapi BM25", color="#10b981")

    ax1.set_ylabel("Skor Rata-rata (0.0 - 1.0)")
    ax1.set_title("Perbandingan Akurasi Pencarian: TF-IDF vs BM25")
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics_labels)
    ax1.set_ylim(0, 1.1)
    ax1.legend()
    ax1.grid(axis="y", linestyle="--", alpha=0.5)

    for rect in rects1 + rects2:
        h = rect.get_height()
        ax1.annotate(f"{h:.2f}", xy=(rect.get_x() + rect.get_width() / 2, h),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9)

    latencies = [np.mean(tfidf_summary["time"]), np.mean(bm25_summary["time"])]
    bars_lat = ax2.bar(["TF-IDF (VSM)", "Okapi BM25"], latencies, color=["#3b82f6", "#10b981"], width=0.45)
    ax2.set_ylabel("Rata-rata Waktu Pencarian (ms)")
    ax2.set_title("Perbandingan Kecepatan Eksekusi Kueri")
    ax2.grid(axis="y", linestyle="--", alpha=0.5)

    for bar in bars_lat:
        h = bar.get_height()
        ax2.annotate(f"{h:.2f} ms", xy=(bar.get_x() + bar.get_width() / 2, h),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=10)

    plt.tight_layout()
    chart_path = "evaluation/grafik_perbandingan.png"
    plt.savefig(chart_path, dpi=300)
    print("=" * 85)
    print(f"[SELESAI] CSV evaluasi disimpan di '{csv_path}'")
    print(f"[SELESAI] Grafik laporan disimpan di '{chart_path}'")


if __name__ == "__main__":
    run_evaluation()   