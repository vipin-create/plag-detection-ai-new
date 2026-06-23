import requests
import PyPDF2
import docx
import uuid
import re

# ─── API KEYS (HARDCODED FOR LIVE PRESENTATION RELIABILITY) ────────────────────
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


def _clean_text_for_search(text: str) -> str:
    """
    Remove Wikipedia inline citation markers like [1], [j][19], [citation needed],
    so that phrase searches against Wikipedia's API actually find matches.
    """
    text = re.sub(r'\[[^\]]{0,20}\]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ──────────────────────────────────────────────────────────────────────────────
# ADVANCED TEXT SEGMENTATION & ANALYSIS MAPPER (For UI Highlighting)
# ──────────────────────────────────────────────────────────────────────────────
def segment_and_tag_text(text, ai_score, matched_sources):
    """
    Splits the document text into structural sentences and tags them as
    'plagiarized', 'ai', or 'normal' to power the front-end dynamic UI highlights.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)
    analysis_results = []
    
    match_phrases = []
    for src in matched_sources:
        title_words = src.get('title', '').lower().split()
        if len(title_words) > 3:
            match_phrases.append(" ".join(title_words[:4]))

    for idx, sentence in enumerate(sentences):
        sentence_str = sentence.strip()
        if not sentence_str:
            continue
            
        is_plag = any(phrase in sentence_str.lower() for phrase in match_phrases) if match_phrases else False
        
        if is_plag:
            tag_type = "plagiarized"
        elif ai_score > 40 and (idx % 2 == 0 or len(sentence_str) > 60):
            tag_type = "ai"
        else:
            tag_type = "normal"
            
        analysis_results.append({
            "id": idx + 1,
            "text": sentence + " ",
            "type": tag_type
        })
    return analysis_results


# ──────────────────────────────────────────────────────────────────────────────
# HUMANIZER (Adversarial Text Manipulation Guard)
# ──────────────────────────────────────────────────────────────────────────────
def _extract_humanized_string(data, fallback_chunk):
    """
    Safely extract a plain string from the API response dict.
    Handles cases where the API returns nested dicts, lists, or unexpected types.
    """
    # Try common key names in order of likelihood
    HUMANIZED_KEYS = [
        "humanizedText", "humanized_text", "humanized",
        "text", "result", "output", "content", "data",
    ]
    for key in HUMANIZED_KEYS:
        val = data.get(key)
        if val is not None:
            if isinstance(val, str) and val.strip():
                print(f"[HUMANIZE] Found string in key '{key}': {len(val)} chars")
                return val
            elif isinstance(val, dict):
                # Some APIs wrap text in a nested dict — recurse one level
                inner = _extract_humanized_string(val, None)
                if inner:
                    return inner
            elif isinstance(val, list) and val:
                # Some APIs return a list of strings
                joined = " ".join(str(v) for v in val if v)
                if joined.strip():
                    print(f"[HUMANIZE] Joined list from key '{key}': {len(joined)} chars")
                    return joined

    # Nothing useful found — log the full response for debugging and fall back
    print(f"[HUMANIZE] WARNING: Could not extract string from response. Keys: {list(data.keys())}")
    print(f"[HUMANIZE] Full response (truncated): {str(data)[:300]}")
    return fallback_chunk  # Always a string (original chunk)


def humanize_text_rapidapi(text_to_scan):
    url     = "https://ai-content-detection-ai-detector-humanize-ai-text.p.rapidapi.com/humanizeContent"
    headers = {
        "Content-Type":    "application/json",
        "x-rapidapi-host": "ai-content-detection-ai-detector-humanize-ai-text.p.rapidapi.com",
        "x-rapidapi-key":  RAPIDAPI_KEY_MAIN,
    }
    params          = {"noqueue": "1", "language": "en"}
    chunks          = _chunk_text(text_to_scan, max_words=600)
    humanized_parts = []  # Will always contain plain strings after this fix

    for idx, chunk in enumerate(chunks):
        try:
            print(f"\n[HUMANIZE] Chunk {idx+1}/{len(chunks)}...")
            response  = requests.post(url, json={"text": chunk}, headers=headers, params=params, timeout=45)
            limit     = response.headers.get("x-ratelimit-requests-limit", "?")
            remaining = response.headers.get("x-ratelimit-requests-remaining", "?")
            print(f"[API WALLET] Humanizer: {limit} | Left: {remaining}")

            if response.status_code == 200:
                data = response.json()
                print(f"[HUMANIZE] Raw response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")

                if isinstance(data, str):
                    # Entire response is a plain string
                    humanized = data if data.strip() else chunk
                elif isinstance(data, dict):
                    humanized = _extract_humanized_string(data, chunk)
                else:
                    print(f"[HUMANIZE] Unexpected response type: {type(data)}")
                    humanized = chunk

                # Final safety net — must be a string before appending
                if not isinstance(humanized, str):
                    print(f"[HUMANIZE] Non-string result ({type(humanized)}), using original chunk")
                    humanized = chunk

                print(f"[HUMANIZE] {len(chunk)} → {len(humanized)} chars")
                humanized_parts.append(humanized)

            else:
                print(f"[!] Humanizer Error {response.status_code}: {response.text[:200]}")
                humanized_parts.append(chunk)  # Fall back to original chunk (string)

        except Exception as e:
            print(f"[!] Humanizer Failed: {e}")
            humanized_parts.append(chunk)  # Fall back to original chunk (string)

    # All items in humanized_parts are now guaranteed strings
    result = "\n\n".join(humanized_parts)
    print(f"\n[HUMANIZE] Done — {len(text_to_scan)} → {len(result)} chars")
    return result


def humanize_text_edenai(text):
    return humanize_text_rapidapi(text)


# ──────────────────────────────────────────────────────────────────────────────
# AI DETECTION (Multi-Model Semantic Evaluation Engine)
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
# WIKIPEDIA DIRECT PAGE FETCH & OVERLAP COMPARISON
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
    if not wiki_text:
        return 0

    sub_clean  = _clean_text_for_search(submitted_text).lower()
    wiki_clean = _clean_text_for_search(wiki_text).lower()

    sub_sentences = [s.strip() for s in re.split(r'[.!?]', sub_clean) if len(s.strip()) > 30]
    if not sub_sentences:
        return 0

    matched = 0
    for sentence in sub_sentences:
        sub_words  = set(sentence.split())
        wiki_words = wiki_clean.split()
        win_size   = len(sub_words)
        best_overlap = 0
        for i in range(0, max(1, len(wiki_words) - win_size + 1), max(1, win_size // 3)):
            window   = set(wiki_words[i: i + win_size + 5])
            overlap  = len(sub_words & window) / len(sub_words) if sub_words else 0
            best_overlap = max(best_overlap, overlap)
        if best_overlap >= 0.70:
            matched += 1

    score = int((matched / len(sub_sentences)) * 100)
    print(f"[WIKI-OVERLAP] {matched}/{len(sub_sentences)} sentences matched → {score}%")
    return score


def check_wikipedia_plagiarism(text: str):
    cleaned_text = _clean_text_for_search(text)
    raw_sentences = [s.strip() for s in re.split(r'[.!?\n]', cleaned_text) if len(s.strip()) > 40]

    if not raw_sentences:
        return 0, []

    sample_count = min(10, len(raw_sentences))
    if len(raw_sentences) > sample_count:
        early   = raw_sentences[:5]
        step    = max(1, len(raw_sentences) // (sample_count - 5))
        spread  = [raw_sentences[i] for i in range(5, len(raw_sentences), step)][:5]
        sentences = early + spread
    else:
        sentences = raw_sentences

    print(f"\n[WIKI] Checking {len(sentences)} sentences against Wikipedia...")

    wiki_sources     = []
    fetched_articles = {}
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

    best_overlap_score = 0
    for title, article_text in fetched_articles.items():
        overlap = _compute_overlap_score(text, article_text)
        print(f"[WIKI] Overlap with '{title}': {overlap}%")
        best_overlap_score = max(best_overlap_score, overlap)

    search_match_rate = int((matched_count / len(sentences)) * 100) if sentences else 0
    wiki_score        = max(search_match_rate, best_overlap_score)

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
# COMPOSITE SCORE
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

    if wiki_score >= 50:
        combined = int(
            wiki_score   * 0.80 +
            smodin_score * 0.10 +
            min(90, n * 10) * 0.10
        )
        print(f"[SCORE] Mode: STRONG WIKIPEDIA MATCH → {combined}%")
    elif wiki_score > 0:
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

    if word_count < 100:
        combined = int(combined * 0.75)
    elif word_count < 200:
        combined = int(combined * 0.88)

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
            "unique_score": 100, "human_score": 100,
            "scan_id": None, "matched_sources": [],
            "analysis_results": [],
        }

    scan_id = str(uuid.uuid4())
    sep     = "=" * 55
    print(f"\n{sep}\n   HYBRID SCAN STARTED: {scan_id}\n{sep}")

    # Step 1 — AI Detection
    ai_score = get_rapidapi_ai_score(text)

    # Step 2 — Wikipedia check
    wiki_score, wiki_sources = check_wikipedia_plagiarism(text)

    # Step 3 — Smodin general web plagiarism
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

    # Dynamic Structural Text Highlighter Sequence
    analysis_results = segment_and_tag_text(text, ai_score, matched_sources)

    return {
        "plag_score":       plag_score,
        "ai_score":         ai_score,
        "unique_score":     100 - plag_score,
        "human_score":      100 - ai_score,
        "scan_id":          scan_id,
        "matched_sources":  matched_sources,
        "analysis_results": analysis_results,
    }


# ──────────────────────────────────────────────────────────────────────────────
# COMPATIBILITY STUBS
# ──────────────────────────────────────────────────────────────────────────────
def get_copyleaks_token():
    return None

def get_copyleaks_ai_score(token, text, scan_id):
    return 0