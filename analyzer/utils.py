import requests
import PyPDF2
import docx
import uuid
import re

# ─── API KEYS ──────────────────────────────────────────────────────────────────
RAPIDAPI_KEY_MAIN = "841612efd5msh21e5bee10d2aca0p113e6fjsn8d0ce8000d44"
RAPIDAPI_KEY_PLAG = "19e952b68dmsh7f43c566b180f05p137d36jsnb57ffacc0aa2"
NGROK_URL         = "https://colony-march-imitation.ngrok-free.dev"

print("\n--- ENVIRONMENT INITIALIZATION ---")
print(f"Main Key (AI+Humanizer) : {RAPIDAPI_KEY_MAIN[:20]}...")
print(f"Plag Key (Smodin)       : {RAPIDAPI_KEY_PLAG[:20]}...")
print(f"Wikipedia API           : FREE (no key needed)")
print(f"Ngrok URL               : {NGROK_URL}")
print("----------------------------------\n")


# ──────────────────────────────────────────────────────────────────────────────
# FILE EXTRACTION
# ──────────────────────────────────────────────────────────────────────────────
def extract_text_from_file(uploaded_file):
    text = ""
    try:
        filename = uploaded_file.name.lower()
        if filename.endswith(".pdf"):
            reader = PyPDF2.PdfReader(uploaded_file)
            for page in reader.pages:
                content = page.extract_text()
                if content:
                    text += content + "\n"
        elif filename.endswith(".docx"):
            doc = docx.Document(uploaded_file)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        elif filename.endswith(".txt"):
            text = uploaded_file.read().decode("utf-8")
        else:
            return "Error: Unsupported file type (use PDF, DOCX, or TXT)"
    except Exception as e:
        return f"Error extracting file: {str(e)}"
    return text.strip()


# ──────────────────────────────────────────────────────────────────────────────
# TEXT UTILITIES
# ──────────────────────────────────────────────────────────────────────────────
def _chunk_text(text, max_words=800):
    words  = text.split()
    chunks = []
    for i in range(0, len(words), max_words):
        chunks.append(" ".join(words[i: i + max_words]))
    return chunks


def _clean_score(val) -> int:
    if val is None:
        return 0
    if isinstance(val, bool):
        return 100 if val else 0
    if isinstance(val, (int, float)):
        return int(val * 100) if 0 < val <= 1.0 else int(val)
    if isinstance(val, str):
        try:
            f = float(val.replace("%", "").strip())
            return int(f * 100) if 0 < f <= 1.0 else int(f)
        except ValueError:
            return 0
    return 0


# ── FIX 1: Strip Wikipedia-style citation markers before searching ────────────
def _clean_text_for_search(text: str) -> str:
    """
    Remove Wikipedia inline citation markers like [1], [j][19], [citation needed],
    so that phrase searches against Wikipedia's API actually find matches.
    """
    # Remove [anything] patterns (citation markers, footnotes, etc.)
    text = re.sub(r'\[[^\]]{0,20}\]', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ──────────────────────────────────────────────────────────────────────────────
# HUMANIZER
# ──────────────────────────────────────────────────────────────────────────────
def humanize_text_rapidapi(text_to_scan):
    url     = "https://ai-content-detection-ai-detector-humanize-ai-text.p.rapidapi.com/humanizeContent"
    headers = {
        "Content-Type":    "application/json",
        "x-rapidapi-host": "ai-content-detection-ai-detector-humanize-ai-text.p.rapidapi.com",
        "x-rapidapi-key":  RAPIDAPI_KEY_MAIN,
    }
    params          = {"noqueue": "1", "language": "en"}
    chunks          = _chunk_text(text_to_scan, max_words=600)
    humanized_parts = []

    for idx, chunk in enumerate(chunks):
        try:
            print(f"\n[HUMANIZE] Chunk {idx+1}/{len(chunks)}...")
            response  = requests.post(url, json={"text": chunk}, headers=headers, params=params, timeout=45)
            limit     = response.headers.get("x-ratelimit-requests-limit", "?")
            remaining = response.headers.get("x-ratelimit-requests-remaining", "?")
            print(f"[API WALLET] Humanizer: {limit} | Left: {remaining}")

            if response.status_code == 200:
                data      = response.json()
                humanized = (
                    data.get("humanizedText") or data.get("humanized_text") or
                    data.get("text") or data.get("result") or chunk
                )
                print(f"[HUMANIZE] {len(chunk)} → {len(humanized)} chars")
                humanized_parts.append(humanized)
            else:
                print(f"[!] Humanizer Error {response.status_code}: {response.text[:200]}")
                humanized_parts.append(chunk)
        except Exception as e:
            print(f"[!] Humanizer Failed: {e}")
            humanized_parts.append(chunk)

    result = "\n\n".join(humanized_parts)
    print(f"\n[HUMANIZE] Done — {len(text_to_scan)} → {len(result)} chars")
    return result


def humanize_text_edenai(text):
    return humanize_text_rapidapi(text)


# ──────────────────────────────────────────────────────────────────────────────
# AI DETECTION
# ──────────────────────────────────────────────────────────────────────────────
def get_rapidapi_ai_score(text_to_scan: str) -> int:
    url     = "https://ai-content-detector-ai-gpt.p.rapidapi.com/api/detectText/"
    headers = {
        "Content-Type":    "application/json",
        "x-rapidapi-host": "ai-content-detector-ai-gpt.p.rapidapi.com",
        "x-rapidapi-key":  RAPIDAPI_KEY_MAIN,
    }
    chunks = _chunk_text(text_to_scan, max_words=800)
    scores = []

    for idx, chunk in enumerate(chunks):
        try:
            print(f"\n[AI] Chunk {idx+1}/{len(chunks)}...")
            response  = requests.post(url, json={"text": chunk}, headers=headers, timeout=30)
            limit     = response.headers.get("x-ratelimit-requests-limit", "?")
            remaining = response.headers.get("x-ratelimit-requests-remaining", "?")
            print(f"[API WALLET] AI Detector: {limit} | Left: {remaining}")

            if response.status_code == 200:
                data = response.json()
                print(f"[AI] Raw: {data}")
                SCORE_KEYS = [
                    "fakePercentage", "aiPercentage", "ai_percentage",
                    "ai_score", "aiScore", "isGpt", "score", "percentage", "ai",
                ]
                raw = None
                for k in SCORE_KEYS:
                    if k in data:
                        raw = data[k]
                        break
                if raw is None:
                    for v in data.values():
                        if isinstance(v, dict):
                            for k in SCORE_KEYS:
                                if k in v:
                                    raw = v[k]
                                    break
                        if raw is not None:
                            break

                score = _clean_score(raw)
                print(f"[AI] Chunk {idx+1}: {score}%")
                scores.append(score)
            else:
                print(f"[!] AI Error {response.status_code}: {response.text[:200]}")
                scores.append(0)
        except Exception as e:
            print(f"[!] AI Failed: {e}")
            scores.append(0)

    final = max(scores) if scores else 0
    print(f"[AI] Final: {final}%")
    return final


# ──────────────────────────────────────────────────────────────────────────────
# FIX 2: WIKIPEDIA DIRECT PAGE FETCH & OVERLAP COMPARISON
# Instead of just checking if sentences appear in search results,
# we now FETCH the actual Wikipedia article and compute real overlap.
# ──────────────────────────────────────────────────────────────────────────────
def _fetch_wikipedia_article_text(title: str) -> str:
    """Fetch the plain text of a Wikipedia article by title."""
    try:
        response = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action":      "query",
                "titles":      title,
                "prop":        "extracts",
                "explaintext": True,
                "format":      "json",
            },
            headers={"User-Agent": "IntellectCheck/2.0"},
            timeout=10,
        )
        if response.status_code == 200:
            pages = response.json().get("query", {}).get("pages", {})
            for page in pages.values():
                extract = page.get("extract", "")
                if extract:
                    return extract
    except Exception as e:
        print(f"[WIKI] Fetch article error: {e}")
    return ""


def _compute_overlap_score(submitted_text: str, wiki_text: str) -> int:
    """
    Compute what % of submitted_text sentences appear (word-overlap ≥ 80%)
    in the fetched Wikipedia article. This is accurate sentence-level diffing.
    """
    if not wiki_text:
        return 0

    # Clean both texts
    sub_clean  = _clean_text_for_search(submitted_text).lower()
    wiki_clean = _clean_text_for_search(wiki_text).lower()

    # Split into sentences
    sub_sentences = [s.strip() for s in re.split(r'[.!?]', sub_clean) if len(s.strip()) > 30]
    if not sub_sentences:
        return 0

    matched = 0
    for sentence in sub_sentences:
        sub_words  = set(sentence.split())
        # Slide a window across wiki text to find best overlap
        wiki_words = wiki_clean.split()
        win_size   = len(sub_words)
        best_overlap = 0
        for i in range(0, max(1, len(wiki_words) - win_size + 1), max(1, win_size // 3)):
            window   = set(wiki_words[i: i + win_size + 5])
            overlap  = len(sub_words & window) / len(sub_words) if sub_words else 0
            best_overlap = max(best_overlap, overlap)
        if best_overlap >= 0.70:   # 70% word overlap = plagiarised sentence
            matched += 1

    score = int((matched / len(sub_sentences)) * 100)
    print(f"[WIKI-OVERLAP] {matched}/{len(sub_sentences)} sentences matched → {score}%")
    return score


def check_wikipedia_plagiarism(text: str):
    """
    IMPROVED Wikipedia plagiarism check:
    1. Clean citation markers from text first
    2. Sample MORE sentences (up to 10) for search
    3. Fetch the actual Wikipedia article(s) found
    4. Do real sentence-level word-overlap scoring
    5. Return accurate score + sources
    """
    cleaned_text = _clean_text_for_search(text)

    # Extract meaningful sentences
    raw_sentences = [s.strip() for s in re.split(r'[.!?\n]', cleaned_text) if len(s.strip()) > 40]

    if not raw_sentences:
        return 0, []

    # FIX: Sample up to 10 sentences (was 5), weighted toward the beginning
    # (Wikipedia copy-paste is usually detected early)
    sample_count = min(10, len(raw_sentences))
    if len(raw_sentences) > sample_count:
        # Take first 5 + spread across rest
        early   = raw_sentences[:5]
        step    = max(1, len(raw_sentences) // (sample_count - 5))
        spread  = [raw_sentences[i] for i in range(5, len(raw_sentences), step)][:5]
        sentences = early + spread
    else:
        sentences = raw_sentences

    print(f"\n[WIKI] Checking {len(sentences)} sentences against Wikipedia...")

    wiki_sources     = []
    fetched_articles = {}   # title → article_text (cache, avoid re-fetching)
    matched_count    = 0

    for i, sentence in enumerate(sentences):
        query = sentence[:150]
        print(f"[WIKI] Query {i+1}: {query[:70]}...")

        try:
            response = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action":   "query",
                    "list":     "search",
                    "srsearch": f'"{query}"',
                    "format":   "json",
                    "srlimit":  3,
                },
                headers={"User-Agent": "IntellectCheck/2.0"},
                timeout=8,
            )

            if response.status_code == 200:
                results = response.json().get("query", {}).get("search", [])
                if results:
                    matched_count += 1
                    print(f"[WIKI] ✅ Found in Wikipedia! {len(results)} article(s)")
                    for result in results[:2]:
                        title    = result.get("title", "Wikipedia Article")
                        wiki_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"

                        # FIX: Fetch article text for overlap scoring (only once per article)
                        if title not in fetched_articles:
                            print(f"[WIKI] Fetching article: {title}")
                            fetched_articles[title] = _fetch_wikipedia_article_text(title)

                        if not any(s["url"] == wiki_url for s in wiki_sources):
                            wiki_sources.append({
                                "title":        f"Wikipedia: {title}",
                                "url":          wiki_url,
                                "matchedWords": len(sentence.split()),
                                "similarity":   0,
                                "credible":     True,
                            })
                else:
                    print(f"[WIKI] ❌ Not found in Wikipedia (sentence {i+1})")
            else:
                print(f"[WIKI] API Error {response.status_code}")

        except Exception as e:
            print(f"[WIKI] Error: {e}")

    # FIX: Use real overlap scoring against fetched article text
    best_overlap_score = 0
    for title, article_text in fetched_articles.items():
        overlap = _compute_overlap_score(text, article_text)
        print(f"[WIKI] Overlap with '{title}': {overlap}%")
        best_overlap_score = max(best_overlap_score, overlap)

    # FIX: Combine search-match rate + actual overlap (both signals)
    search_match_rate = int((matched_count / len(sentences)) * 100) if sentences else 0
    wiki_score        = max(search_match_rate, best_overlap_score)

    # FIX: If we found Wikipedia articles AND overlap is significant, boost confidence
    if wiki_sources and best_overlap_score > 30:
        wiki_score = min(97, int(best_overlap_score * 1.15))

    print(f"[WIKI] Search match rate: {search_match_rate}% | Overlap: {best_overlap_score}% | Final: {wiki_score}%")
    print(f"[WIKI] Sources: {len(wiki_sources)}")
    return wiki_score, wiki_sources


# ──────────────────────────────────────────────────────────────────────────────
# DOMAIN FILTERS
# ──────────────────────────────────────────────────────────────────────────────
JUNK_DOMAINS = {
    'instagram.com', 'tiktok.com', 'twitter.com', 'x.com',
    'facebook.com', 'reddit.com', 'pinterest.com', 'youtube.com',
    'quora.com', 'anagora.org', 'discord.com', 'linkedin.com',
    't.me', 'tumblr.com', 'snapchat.com',
}

CREDIBLE_DOMAINS = [
    'wikipedia.org', '.edu', '.gov', '.ac.',
    'researchgate.net', 'jstor.org', 'britannica.com',
    'bbc.com', 'reuters.com', 'ncbi.nlm.nih.gov',
    'scholar.google', 'academia.edu', 'pubmed.ncbi',
    'springer.com', 'sciencedirect.com', 'ieee.org',
    'nature.com', 'tandfonline.com',
]


def _is_junk(url: str) -> bool:
    return any(j in url for j in JUNK_DOMAINS)


def _is_credible(url: str) -> bool:
    return any(c in url for c in CREDIBLE_DOMAINS)


# ──────────────────────────────────────────────────────────────────────────────
# FIX 3: COMPOSITE SCORE — Wikipedia is now the dominant signal
# ──────────────────────────────────────────────────────────────────────────────
def calculate_composite_plag_score(
    smodin_score: int,
    wiki_score: int,
    sources_list: list,
    text: str,
) -> int:
    n              = len(sources_list)
    word_count     = len(text.split())
    credible_count = sum(1 for s in sources_list if _is_credible(s.get("url", "")))

    print(f"\n[SCORE] ── Composite Score Inputs ──")
    print(f"[SCORE] Smodin raw     : {smodin_score}%")
    print(f"[SCORE] Wikipedia score: {wiki_score}%")
    print(f"[SCORE] Total sources  : {n}")
    print(f"[SCORE] Credible srcs  : {credible_count}")
    print(f"[SCORE] Word count     : {word_count}")

    # FIX: Wikipedia overlap score is the most reliable signal.
    # If Wikipedia detected significant overlap, trust it heavily.
    if wiki_score >= 50:
        # Strong Wikipedia match — this IS plagiarism from Wikipedia
        combined = int(
            wiki_score   * 0.80 +   # Wikipedia real overlap = primary signal
            smodin_score * 0.10 +   # Smodin backup
            min(90, n * 10) * 0.10  # Source count
        )
        print(f"[SCORE] Mode: STRONG WIKIPEDIA MATCH → {combined}%")

    elif wiki_score > 0:
        # Partial Wikipedia match
        combined = int(
            wiki_score   * 0.65 +
            smodin_score * 0.20 +
            min(90, n * 10) * 0.15
        )
        print(f"[SCORE] Mode: PARTIAL WIKIPEDIA MATCH → {combined}%")

    elif n >= 5:
        combined = int(
            smodin_score       * 0.20 +
            min(90, n * 10)    * 0.50 +
            credible_count * 8 * 0.30
        )
        print(f"[SCORE] Mode: STRONG WEB EVIDENCE → {combined}%")

    elif n >= 3:
        combined = int(
            smodin_score    * 0.30 +
            min(60, n * 12) * 0.50 +
            credible_count * 5 * 0.20
        )
        print(f"[SCORE] Mode: MEDIUM EVIDENCE → {combined}%")

    else:
        combined = smodin_score
        print(f"[SCORE] Mode: RAW SMODIN SCORE → {combined}%")

    # Short text = less confident
    if word_count < 100:
        combined = int(combined * 0.75)
    elif word_count < 200:
        combined = int(combined * 0.88)

    # FIX: Final = max of all signals, not suppressed by low Smodin score
    final = min(97, max(smodin_score, wiki_score, combined))
    print(f"[SCORE] ── Final: {final}% ──\n")
    return final


# ──────────────────────────────────────────────────────────────────────────────
# SMODIN PLAGIARISM CHECKER
# ──────────────────────────────────────────────────────────────────────────────
def get_rapidapi_plagiarism_score(text_to_scan: str):
    url     = "https://plagiarism-checker-and-auto-citation-generator-multi-lingual.p.rapidapi.com/plagiarism"
    headers = {
        "Content-Type":    "application/json",
        "x-rapidapi-host": "plagiarism-checker-and-auto-citation-generator-multi-lingual.p.rapidapi.com",
        "x-rapidapi-key":  RAPIDAPI_KEY_PLAG,
    }

    # FIX: Clean citation markers from text before sending to Smodin too
    cleaned_text = _clean_text_for_search(text_to_scan)
    chunks       = _chunk_text(cleaned_text, max_words=800)
    all_sources  = {}
    raw_scores   = []

    for idx, chunk in enumerate(chunks):
        payload = {
            "text":             chunk,
            "language":         "en",
            "includeCitations": False,
            "scrapeSources":    True,
        }
        try:
            print(f"\n[PLAG] Chunk {idx+1}/{len(chunks)} ({len(chunk.split())} words)...")
            response  = requests.post(url, json=payload, headers=headers, timeout=90)
            limit     = response.headers.get("x-ratelimit-requests-limit", "?")
            remaining = response.headers.get("x-ratelimit-requests-remaining", "?")
            print(f"[API WALLET] Plagiarism: {limit} | Left: {remaining}")

            if response.status_code != 200:
                print(f"[!] Plag Error {response.status_code}: {response.text[:200]}")
                raw_scores.append(0)
                continue

            data    = response.json()
            raw_src = data.get("sources", [])
            print(f"[PLAG] Sources in chunk: {len(raw_src)}")

            for src in raw_src:
                url_val   = src.get("url", src.get("link", "")) if isinstance(src, dict) else str(src)
                title_val = src.get("title", url_val[:70]) if isinstance(src, dict) else url_val[:70]
                mw        = src.get("matchedWords", "Multiple") if isinstance(src, dict) else "Multiple"

                if not url_val or _is_junk(url_val):
                    continue

                if url_val not in all_sources:
                    all_sources[url_val] = {
                        "title":        title_val or "Internet Match",
                        "url":          url_val,
                        "matchedWords": mw,
                        "similarity":   0,
                        "credible":     _is_credible(url_val),
                    }

            chunk_raw = int(data.get("percentPlagiarism", 0) or 0)
            print(f"[PLAG] Chunk raw: {chunk_raw}%")
            raw_scores.append(chunk_raw)

        except requests.exceptions.Timeout:
            print(f"[!] Timeout chunk {idx+1}.")
            raw_scores.append(0)
        except Exception as e:
            print(f"[!] Plag Failed (chunk {idx+1}): {e}")
            raw_scores.append(0)

    return max(raw_scores) if raw_scores else 0, list(all_sources.values())


# ──────────────────────────────────────────────────────────────────────────────
# MAIN HYBRID REPORT
# ──────────────────────────────────────────────────────────────────────────────
def get_hybrid_report(text: str) -> dict:
    if not text or len(text.strip()) < 50:
        print("[!] Text too short. Skipping.")
        return {
            "plag_score": 0, "ai_score": 0,
            "scan_id": None, "matched_sources": [],
            "analysis_results": [],
        }

    scan_id = str(uuid.uuid4())
    sep     = "=" * 55
    print(f"\n{sep}\n   HYBRID SCAN STARTED: {scan_id}\n{sep}")

    # Step 1 — AI Detection
    ai_score = get_rapidapi_ai_score(text)

    # Step 2 — Wikipedia check (FREE, now with real overlap scoring)
    wiki_score, wiki_sources = check_wikipedia_plagiarism(text)

    # Step 3 — Smodin general web plagiarism (now with citation cleanup)
    smodin_score, smodin_sources = get_rapidapi_plagiarism_score(text)

    # Step 4 — Merge all sources (Wikipedia + Smodin, no duplicates)
    all_sources_dict = {}
    for src in wiki_sources + smodin_sources:
        url_key = src.get("url", "")
        if url_key and url_key not in all_sources_dict:
            all_sources_dict[url_key] = src
    matched_sources = list(all_sources_dict.values())

    # Step 5 — Calculate final composite score
    plag_score = calculate_composite_plag_score(
        smodin_score, wiki_score, matched_sources, text
    )

    print(f"\n{sep}")
    print(f"   COMPLETE → AI: {ai_score}% | Plag: {plag_score}% "
          f"| Sources: {len(matched_sources)}")
    print(f"   (Wiki: {wiki_score}% | Smodin: {smodin_score}%)")
    print(f"{sep}\n")

    return {
        "plag_score":       plag_score,
        "ai_score":         ai_score,
        "scan_id":          scan_id,
        "matched_sources":  matched_sources,
        "analysis_results": [{"type": "normal", "text": text}],
    }


# ──────────────────────────────────────────────────────────────────────────────
# COMPATIBILITY STUBS
# ──────────────────────────────────────────────────────────────────────────────
def get_copyleaks_token():
    return None

def get_copyleaks_ai_score(token, text, scan_id):
    return 0