const mainApp = document.getElementById("mainApp");
const logoHomeLink = document.getElementById("logoHomeLink");
const searchForm = document.getElementById("searchForm");
const queryInput = document.getElementById("queryInput");
const clearSearchBtn = document.getElementById("clearSearchBtn");
const searchSubmitBtn = document.getElementById("searchSubmitBtn");
const searchHint = document.getElementById("searchHint");
const themeToggleBtn = document.getElementById("themeToggle");

const retrySearchBtn = document.getElementById("retrySearchBtn");
const resultsPanelTitle = document.getElementById("resultsPanelTitle");
const comparisonWrap = document.getElementById("comparisonWrap");
const comparisonGrid = document.getElementById("comparisonGrid");
const tabTfidf = document.getElementById("tabTfidf");
const tabBm25 = document.getElementById("tabBm25");
const tabTfidfCount = document.getElementById("tabTfidfCount");
const tabBm25Count = document.getElementById("tabBm25Count");

const tfidfTimeEl = document.getElementById("tfidfTime");
const bm25TimeEl = document.getElementById("bm25Time");
const tfidfCountEl = document.getElementById("tfidfCount");
const bm25CountEl = document.getElementById("bm25Count");
const tokenListEl = document.getElementById("tokenList");
const overlapBadgeEl = document.getElementById("overlapBadge");
const overlapFillEl = document.getElementById("overlapFill");
const footerMediaCountEl = document.getElementById("footerMediaCount");

const modal = document.getElementById("articleModal");
const modalPanel = modal ? modal.querySelector(".fe-modal-panel") : null;
const closeModalBtn = document.getElementById("closeModal");

const THEME_STORAGE_KEY = "finedu-theme";
const dateFormatterId = new Intl.DateTimeFormat("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric"
});

let lastQuery = "";
let activeTab = "tfidf";
let modalTriggerEl = null;
let searchRequestId = 0;

function setPageState(state) {
    if (!mainApp) return;
    mainApp.setAttribute("data-state", state);
}

function getSystemTheme() {
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
        return "dark";
    }
    return "light";
}

function getSavedTheme() {
    try {
        const saved = localStorage.getItem(THEME_STORAGE_KEY);
        if (saved === "light" || saved === "dark") {
            return saved;
        }
    } catch (e) {}
    return null;
}

function applyTheme(theme) {
    const isDark = theme === "dark";
    document.documentElement.setAttribute("data-theme", theme);
    if (themeToggleBtn) {
        themeToggleBtn.setAttribute("aria-pressed", String(isDark));
        themeToggleBtn.setAttribute(
            "aria-label",
            isDark ? "Ganti ke mode terang" : "Ganti ke mode gelap"
        );
    }
}

function initTheme() {
    applyTheme(getSavedTheme() || getSystemTheme());

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener("click", () => {
            const current = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
            const next = current === "dark" ? "light" : "dark";
            applyTheme(next);
            try {
                localStorage.setItem(THEME_STORAGE_KEY, next);
            } catch (e) {}
        });
    }

    if (window.matchMedia) {
        const media = window.matchMedia("(prefers-color-scheme: dark)");
        const onSystemChange = (e) => {
            if (!getSavedTheme()) {
                applyTheme(e.matches ? "dark" : "light");
            }
        };
        if (typeof media.addEventListener === "function") {
            media.addEventListener("change", onSystemChange);
        }
    }
}

function formatNumberId(value, decimals) {
    const num = Number(value);
    if (Number.isNaN(num)) return String(value);
    if (typeof decimals === "number") {
        return num.toLocaleString("id-ID", {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    }
    return num.toLocaleString("id-ID");
}

function formatDateId(dateStr) {
    if (!dateStr) return "";
    const match = String(dateStr).trim().match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})/);
    if (!match) return String(dateStr);
    const year = Number(match[1]);
    const month = Number(match[2]);
    const day = Number(match[3]);
    const dt = new Date(year, month - 1, day);
    if (
        Number.isNaN(dt.getTime()) ||
        dt.getFullYear() !== year ||
        dt.getMonth() !== month - 1 ||
        dt.getDate() !== day
    ) {
        return String(dateStr);
    }
    return dateFormatterId.format(dt);
}

function syncFooterStatsSource() {
    if (!footerMediaCountEl) return;
    const sourceBarsCount = document.querySelectorAll(".fe-bento-sources .fe-source-bar-item").length;
    if (sourceBarsCount > 0) {
        footerMediaCountEl.setAttribute("data-num", String(sourceBarsCount));
    }
}

function formatStaticNumbers() {
    syncFooterStatsSource();
    document.querySelectorAll("[data-num]").forEach((el) => {
        const raw = el.getAttribute("data-num");
        const decAttr = el.getAttribute("data-decimals");
        const decimals = decAttr !== null ? Number(decAttr) : undefined;
        el.textContent = formatNumberId(raw, decimals);
    });
}

function syncClearButton() {
    if (!clearSearchBtn || !queryInput) return;
    clearSearchBtn.classList.toggle("hidden", queryInput.value.length === 0);
}

function showSearchHint(message) {
    if (!searchHint) return;
    if (message) {
        searchHint.textContent = message;
        searchHint.classList.remove("hidden");
    } else {
        searchHint.textContent = "";
        searchHint.classList.add("hidden");
    }
}

function setSubmittingState(isLoading) {
    if (!searchSubmitBtn) return;
    searchSubmitBtn.disabled = isLoading;
    const spinner = searchSubmitBtn.querySelector(".fe-btn-spinner");
    const label = searchSubmitBtn.querySelector(".fe-btn-label");
    if (spinner) spinner.classList.toggle("hidden", !isLoading);
    if (label) label.textContent = isLoading ? "Mencari..." : "Cari";
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function cleanSnippetStart(snippet) {
    if (!snippet) return "";
    if (!snippet.startsWith("...")) return snippet;
    const rest = snippet.slice(3);
    if (!rest) return snippet;
    if (/^\s/.test(rest)) {
        return "..." + rest.trimStart();
    }
    const firstSpace = rest.search(/\s/);
    if (firstSpace === -1) return snippet;
    const trimmed = rest.slice(firstSpace).trimStart();
    return trimmed ? "..." + trimmed : snippet;
}

function highlightText(text, preprocessedTokens) {
    const tokens = (Array.isArray(preprocessedTokens) ? preprocessedTokens : [])
        .map((t) => String(t).toLowerCase().trim())
        .filter((t) => t.length >= 3);

    if (!tokens.length) {
        return escapeHtml(text);
    }

    const remaining = new Set(tokens);
    const parts = String(text).split(/([A-Za-zÀ-ÖØ-öø-ÿ]+)/);
    return parts
        .map((part, idx) => {
            const safePart = escapeHtml(part);
            if (idx % 2 === 1 && remaining.size > 0) {
                const lower = part.toLowerCase();
                const matched = [];
                for (const tok of remaining) {
                    if (lower.includes(tok)) {
                        matched.push(tok);
                    }
                }
                if (matched.length > 0) {
                    matched.forEach((tok) => remaining.delete(tok));
                    return `<mark>${safePart}</mark>`;
                }
            }
            return safePart;
        })
        .join("");
}

function getAlgoIconSvg(algo) {
    if (algo === "tfidf") {
        return `<svg class="fe-algo-icon-xs" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true" focusable="false"><path d="M8 2.5 14.2 13.5H1.8L8 2.5Z"></path></svg>`;
    }
    return `<svg class="fe-algo-icon-xs" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true" focusable="false"><circle cx="8" cy="8" r="5.5"></circle></svg>`;
}

function getDominantSource(results) {
    if (!results || !results.length) return null;
    const counts = new Map();
    results.forEach((item) => {
        const src = item.source || "";
        counts.set(src, (counts.get(src) || 0) + 1);
    });
    if (counts.size <= 1) {
        return results[0].source || null;
    }
    let dominant = null;
    let bestCount = -1;
    counts.forEach((count, src) => {
        if (count > bestCount) {
            bestCount = count;
            dominant = src;
        }
    });
    return dominant;
}

function setActiveTab(algo) {
    activeTab = algo === "bm25" ? "bm25" : "tfidf";
    const isTfidf = activeTab === "tfidf";

    if (comparisonWrap) {
        comparisonWrap.setAttribute("data-active-algo", activeTab);
    }

    if (tabTfidf && tabBm25) {
        tabTfidf.classList.toggle("is-active", isTfidf);
        tabTfidf.setAttribute("aria-selected", String(isTfidf));
        tabBm25.classList.toggle("is-active", !isTfidf);
        tabBm25.setAttribute("aria-selected", String(!isTfidf));
    }
}

function getFocusableInModal() {
    if (!modalPanel) return [];
    return Array.from(
        modalPanel.querySelectorAll(
            'button:not([disabled]), a[href], input:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )
    );
}

function openArticleModal(doc, triggerEl) {
    modalTriggerEl = triggerEl || document.activeElement;
    document.getElementById("modalSource").textContent = `${doc.source} (Doc #${formatNumberId(doc.doc_id)})`;
    document.getElementById("modalTitle").textContent = doc.title;
    const formattedDate = formatDateId(doc.date);
    document.getElementById("modalDate").textContent = formattedDate ? `Dipublikasikan ${formattedDate}` : "";
    document.getElementById("modalBody").textContent = doc.content;
    document.getElementById("modalLink").href = doc.url;

    modal.classList.remove("hidden");
    document.body.style.overflow = "hidden";
    if (closeModalBtn) {
        closeModalBtn.focus();
    } else if (modalPanel) {
        modalPanel.focus();
    }
}

function closeArticleModal() {
    if (modal.classList.contains("hidden")) return;
    modal.classList.add("hidden");
    document.body.style.overflow = "";
    if (modalTriggerEl && typeof modalTriggerEl.focus === "function") {
        modalTriggerEl.focus();
    }
    modalTriggerEl = null;
}

if (closeModalBtn) {
    closeModalBtn.addEventListener("click", closeArticleModal);
}

if (modal) {
    modal.addEventListener("click", (e) => {
        if (e.target === modal) closeArticleModal();
    });
}

document.addEventListener("keydown", (e) => {
    if (!modal || modal.classList.contains("hidden")) return;
    if (e.key === "Escape") {
        e.preventDefault();
        closeArticleModal();
        return;
    }
    if (e.key === "Tab") {
        const focusable = getFocusableInModal();
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
        }
    }
});

function setPairedHighlight(docId, active) {
    if (!comparisonGrid) return;
    const matches = comparisonGrid.querySelectorAll(`.fe-result-card[data-doc-id="${CSS.escape(docId)}"]`);
    if (matches.length < 2) {
        matches.forEach((el) => el.classList.remove("is-paired-highlight"));
        return;
    }
    matches.forEach((el) => {
        el.classList.toggle("is-paired-highlight", active);
    });
}

function bindPairedHover(card, docId) {
    card.addEventListener("mouseenter", () => setPairedHighlight(docId, true));
    card.addEventListener("mouseleave", () => setPairedHighlight(docId, false));
    card.addEventListener("focusin", () => setPairedHighlight(docId, true));
    card.addEventListener("focusout", (e) => {
        if (!card.contains(e.relatedTarget)) {
            setPairedHighlight(docId, false);
        }
    });
}

function renderTokens(tokens) {
    tokenListEl.innerHTML = "";
    if (!tokens || !tokens.length) {
        const emptyToken = document.createElement("span");
        emptyToken.className = "fe-token-chip";
        emptyToken.textContent = "-";
        tokenListEl.appendChild(emptyToken);
        return;
    }
    tokens.forEach((token) => {
        const chip = document.createElement("span");
        chip.className = "fe-token-chip";
        chip.textContent = token;
        tokenListEl.appendChild(chip);
    });
}

function createResultCard(item, otherRankById, dominantSource, algo, preprocessedTokens) {
    const docId = String(item.doc_id);
    const otherRank = otherRankById.get(docId);
    const isUnique = otherRank === undefined;

    const isTfidf = algo === "tfidf";
    const algoName = isTfidf ? "TF-IDF" : "BM25";
    const otherAlgoName = isTfidf ? "BM25" : "TF-IDF";
    const variantSuffix = isTfidf ? "a" : "b";
    const iconSvg = getAlgoIconSvg(algo);

    const diffHtml = isUnique
        ? `<span class="fe-diff-pill fe-diff-pill-${variantSuffix}">${iconSvg}<span>Hanya di ${algoName}</span></span>`
        : `<span class="fe-other-rank">Di ${otherAlgoName}: #${formatNumberId(otherRank)}</span>`;

    const isRareSource = dominantSource && item.source !== dominantSource;
    const sourceHtml = isRareSource
        ? `<span class="fe-source-badge">${escapeHtml(item.source)}</span>`
        : `<span class="fe-source-text">${escapeHtml(item.source)}</span>`;

    const formattedDate = formatDateId(item.date);
    const dateHtml = formattedDate ? `<span class="fe-card-date">${escapeHtml(formattedDate)}</span>` : "";
    const formattedScore = formatNumberId(item.score, 3);
    const cleanedSnippet = cleanSnippetStart(item.snippet);

    const card = document.createElement("article");
    card.className = `fe-result-card fe-result-card-${variantSuffix}`;
    card.setAttribute("data-algo", algo);
    card.setAttribute("data-doc-id", docId);
    card.innerHTML = `
        <div class="fe-card-meta">
            <div class="fe-card-meta-left">
                <span class="fe-rank-num">#${formatNumberId(item.rank)}</span>
                ${sourceHtml}
                ${dateHtml}
            </div>
            <div class="fe-card-meta-right">${diffHtml}</div>
        </div>
        <button type="button" class="fe-result-title-btn">${highlightText(item.title, preprocessedTokens)}</button>
        <p class="fe-result-snippet">${highlightText(cleanedSnippet, preprocessedTokens)}</p>
        <div class="fe-card-footer">
            <span class="fe-score-badge fe-score-badge-${variantSuffix}">${iconSvg}<span>skor ${formattedScore}</span></span>
            <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer" class="fe-source-link">Buka sumber asli</a>
        </div>
    `;

    const titleBtn = card.querySelector(".fe-result-title-btn");
    titleBtn.addEventListener("click", () => openArticleModal(item, titleBtn));
    bindPairedHover(card, docId);
    return card;
}

function createEmptySlot(algo, message) {
    const slot = document.createElement("div");
    slot.className = message ? "fe-col-empty-card" : "fe-card-slot-empty";
    slot.setAttribute("data-algo", algo);
    if (message) {
        slot.innerHTML = `<p class="fe-col-empty">${escapeHtml(message)}</p>`;
    } else {
        slot.setAttribute("aria-hidden", "true");
    }
    return slot;
}

function renderCards(tfidfResults, bm25Results, preprocessedTokens) {
    comparisonGrid.innerHTML = "";

    const tfidfRankById = new Map();
    tfidfResults.forEach((doc) => tfidfRankById.set(String(doc.doc_id), doc.rank));

    const bm25RankById = new Map();
    bm25Results.forEach((doc) => bm25RankById.set(String(doc.doc_id), doc.rank));

    const dominantTfidf = getDominantSource(tfidfResults);
    const dominantBm25 = getDominantSource(bm25Results);

    const maxLen = Math.max(tfidfResults.length, bm25Results.length);

    for (let i = 0; i < maxLen; i += 1) {
        if (i < tfidfResults.length) {
            comparisonGrid.appendChild(
                createResultCard(tfidfResults[i], bm25RankById, dominantTfidf, "tfidf", preprocessedTokens)
            );
        } else if (i === 0) {
            comparisonGrid.appendChild(createEmptySlot("tfidf", "Tidak ada dokumen yang cocok pada TF-IDF."));
        } else {
            comparisonGrid.appendChild(createEmptySlot("tfidf", ""));
        }

        if (i < bm25Results.length) {
            comparisonGrid.appendChild(
                createResultCard(bm25Results[i], tfidfRankById, dominantBm25, "bm25", preprocessedTokens)
            );
        } else if (i === 0) {
            comparisonGrid.appendChild(createEmptySlot("bm25", "Tidak ada dokumen yang cocok pada BM25."));
        } else {
            comparisonGrid.appendChild(createEmptySlot("bm25", ""));
        }
    }
}

function resetToIdle(shouldFocusInput) {
    searchRequestId += 1;
    lastQuery = "";
    if (queryInput) queryInput.value = "";
    if (tokenListEl) tokenListEl.innerHTML = "";
    if (comparisonGrid) comparisonGrid.innerHTML = "";
    if (overlapFillEl) overlapFillEl.style.width = "0";
    syncClearButton();
    showSearchHint("");
    setSubmittingState(false);
    setPageState("idle");
    if (shouldFocusInput && queryInput) {
        queryInput.focus();
    }
}

async function executeSearch(query) {
    if (!query) {
        showSearchHint("Masukkan kata kunci pencarian terlebih dahulu.");
        queryInput.focus();
        return;
    }

    const reqId = ++searchRequestId;
    lastQuery = query;
    showSearchHint("");
    setPageState("loading");
    setSubmittingState(true);

    try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&top_k=10`);
        if (reqId !== searchRequestId) return;
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        if (reqId !== searchRequestId) return;

        if (!data.tfidf.results.length && !data.bm25.results.length) {
            setPageState("empty");
            return;
        }

        const preprocessedTokens = data.preprocessed_tokens || [];
        renderTokens(preprocessedTokens);

        const maxCount = Math.max(data.tfidf.count, data.bm25.count, 1);
        const overlapPct = Math.round((data.overlap_count / maxCount) * 100);
        overlapBadgeEl.textContent = `${formatNumberId(data.overlap_count)} dari ${formatNumberId(maxCount)}`;
        if (overlapFillEl) {
            overlapFillEl.style.width = `${overlapPct}%`;
        }

        tfidfTimeEl.textContent = `${formatNumberId(data.tfidf.time_ms, 2)} ms`;
        bm25TimeEl.textContent = `${formatNumberId(data.bm25.time_ms, 2)} ms`;
        if (tfidfCountEl) tfidfCountEl.textContent = `${formatNumberId(data.tfidf.count)} hasil`;
        if (bm25CountEl) bm25CountEl.textContent = `${formatNumberId(data.bm25.count)} hasil`;
        if (tabTfidfCount) tabTfidfCount.textContent = formatNumberId(data.tfidf.count);
        if (tabBm25Count) tabBm25Count.textContent = formatNumberId(data.bm25.count);

        renderCards(data.tfidf.results, data.bm25.results, preprocessedTokens);

        setActiveTab(activeTab);
        setPageState("results");

        if (resultsPanelTitle) {
            resultsPanelTitle.focus({ preventScroll: true });
        }
    } catch (err) {
        if (reqId !== searchRequestId) return;
        setPageState("error");
        console.error(err);
    } finally {
        if (reqId === searchRequestId) {
            setSubmittingState(false);
        }
    }
}

if (queryInput) {
    queryInput.addEventListener("input", () => {
        syncClearButton();
        if (queryInput.value.trim()) {
            showSearchHint("");
        }
    });
}

if (clearSearchBtn) {
    clearSearchBtn.addEventListener("click", () => {
        resetToIdle(true);
    });
}

if (logoHomeLink) {
    logoHomeLink.addEventListener("click", (e) => {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
        e.preventDefault();
        resetToIdle(false);
    });
}

searchForm.addEventListener("submit", (e) => {
    e.preventDefault();
    executeSearch(queryInput.value.trim());
});

if (retrySearchBtn) {
    retrySearchBtn.addEventListener("click", () => {
        if (lastQuery) {
            executeSearch(lastQuery);
        } else {
            executeSearch(queryInput.value.trim());
        }
    });
}

document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
        const q = chip.getAttribute("data-q");
        queryInput.value = q;
        syncClearButton();
        executeSearch(q);
    });
});

[tabTfidf, tabBm25].forEach((tab) => {
    if (!tab) return;
    tab.addEventListener("click", () => {
        setActiveTab(tab.getAttribute("data-algo"));
    });
    tab.addEventListener("keydown", (e) => {
        if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
            e.preventDefault();
            const nextTab = tab === tabTfidf ? tabBm25 : tabTfidf;
            setActiveTab(nextTab.getAttribute("data-algo"));
            nextTab.focus();
        }
    });
});

initTheme();
formatStaticNumbers();
syncClearButton();
setPageState("idle");
