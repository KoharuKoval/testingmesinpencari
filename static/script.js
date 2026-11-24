const searchForm = document.getElementById("searchForm");
const queryInput = document.getElementById("queryInput");
const loadingState = document.getElementById("loadingState");
const metaPanel = document.getElementById("metaPanel");
const comparisonGrid = document.getElementById("comparisonGrid");

const tfidfResultsEl = document.getElementById("tfidfResults");
const bm25ResultsEl = document.getElementById("bm25Results");
const tfidfTimeEl = document.getElementById("tfidfTime");
const bm25TimeEl = document.getElementById("bm25Time");
const tokenListEl = document.getElementById("tokenList");
const overlapBadgeEl = document.getElementById("overlapBadge");

const modal = document.getElementById("articleModal");
const closeModalBtn = document.getElementById("closeModal");

function highlightText(text, query) {
    const words = query.trim().split(/\s+/).filter(w => w.length > 2);
    if (!words.length) return text;
    const escaped = words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    const regex = new RegExp(`(${escaped.join("|")})`, "gi");
    return text.replace(regex, "<mark>$1</mark>");
}

function openArticleModal(doc) {
    document.getElementById("modalSource").textContent = `${doc.source} • Doc #${doc.doc_id}`;
    document.getElementById("modalTitle").textContent = doc.title;
    document.getElementById("modalDate").textContent = doc.date ? `Dipublikasikan: ${doc.date}` : "";
    document.getElementById("modalBody").textContent = doc.content;
    document.getElementById("modalLink").href = doc.url;
    modal.classList.remove("hidden");
}

closeModalBtn.addEventListener("click", () => modal.classList.add("hidden"));
modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.add("hidden");
});

function renderCards(container, results, query) {
    container.innerHTML = "";
    if (!results.length) {
        container.innerHTML = `<p style="color:#64748b;text-align:center;padding:20px;">Tidak ada dokumen relevan ditemukan.</p>`;
        return;
    }

    results.forEach(item => {
        const card = document.createElement("div");
        card.className = "result-card";
        card.innerHTML = `
            <div class="card-top">
                <span class="rank-score">#${item.rank} • Skor: ${item.score}</span>
                <span class="source-tag">${item.source} (Doc #${item.doc_id})</span>
            </div>
            <div class="result-title">${highlightText(item.title, query)}</div>
            <p class="result-snippet">${highlightText(item.snippet, query)}</p>
        `;
        card.querySelector(".result-title").addEventListener("click", () => openArticleModal(item));
        container.appendChild(card);
    });
}

async function executeSearch(query) {
    if (!query) return;
    loadingState.classList.remove("hidden");
    metaPanel.classList.add("hidden");
    comparisonGrid.classList.add("hidden");

    try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&top_k=10`);
        const data = await res.json();

        tokenListEl.textContent = data.preprocessed_tokens.join(", ") || "-";
        overlapBadgeEl.textContent = `${data.overlap_count} dari 10 dokumen sama`;

        tfidfTimeEl.textContent = `${data.tfidf.time_ms} ms`;
        bm25TimeEl.textContent = `${data.bm25.time_ms} ms`;

        renderCards(tfidfResultsEl, data.tfidf.results, query);
        renderCards(bm25ResultsEl, data.bm25.results, query);

        loadingState.classList.add("hidden");
        metaPanel.classList.remove("hidden");
        comparisonGrid.classList.remove("hidden");
    } catch (err) {
        loadingState.textContent = "Terjadi kesalahan saat memproses pencarian.";
        console.error(err);
    }
}

searchForm.addEventListener("submit", (e) => {
    e.preventDefault();
    executeSearch(queryInput.value.trim());
});

document.querySelectorAll(".chip").forEach(chip => {
    chip.addEventListener("click", () => {
        const q = chip.getAttribute("data-q");
        queryInput.value = q;
        executeSearch(q);
    });
});