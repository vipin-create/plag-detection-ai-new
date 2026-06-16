import requests
import PyPDF2
import docx
import uuid

# ─── API KEYS — Hardcoded for reliability ─────────────────────────────────────
RAPIDAPI_KEY = "bfabdccc8fmshd775d7eed9eb952p1f6e47jsn073423e40f52"
NGROK_URL    = "https://colony-march-imitation.ngrok-free.dev"

print("\n--- ENVIRONMENT INITIALIZATION ---")
print(f"RapidAPI Key : {RAPIDAPI_KEY[:15]}...")
print(f"Ngrok URL    : {NGROK_URL}")
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
            return "Error: Unsupported file type"
    except Exception as e:
        return f"Error: {str(e)}"
    return text.strip()


# ──────────────────────────────────────────────────────────────────────────────
# RAPIDAPI — HUMANIZER
# ──────────────────────────────────────────────────────────────────────────────
def humanize_text_rapidapi(text_to_scan):
    url     = "https://ai-humanizer-api.p.rapidapi.com/"
    headers = {
        "Content-Type":   "application/json",
        "x-rapidapi-host": "ai-humanizer-api.p.rapidapi.com",
        "x-rapidapi-key":  RAPIDAPI_KEY
    }
    payload = {"text": text_to_scan, "level": "standard"}

    try:
        print("\n[HUMANIZE] Routing text to RapidAPI Humanizer...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)

        limit     = response.headers.get("x-ratelimit-requests-limit", "Unknown")
        remaining = response.headers.get("x-ratelimit-requests-remaining", "Unknown")
        print(f"[API WALLET] Humanizer Quota: {limit} | Left: {remaining}")

        if response.status_code == 200:
            data      = response.json()
            humanized = data.get("humanized_text", data.get("text", text_to_scan))
            print("[HUMANIZE] Success!")
            return humanized
        else:
            print(f"[!] Humanizer Error {response.status_code}: {response.text}")
            return text_to_scan
    except Exception as e:
        print(f"[!] Humanizer Connection Failed: {e}")
        return text_to_scan


# Keep old function name for compatibility with views.py
def humanize_text_edenai(text):
    return humanize_text_rapidapi(text)


# ──────────────────────────────────────────────────────────────────────────────
# RAPIDAPI — AI DETECTION
# ──────────────────────────────────────────────────────────────────────────────
def get_rapidapi_ai_score(text_to_scan):
    url     = "https://ai-content-detector-ai-gpt.p.rapidapi.com/api/detectText/"
    headers = {
        "Content-Type":    "application/json",
        "x-rapidapi-host": "ai-content-detector-ai-gpt.p.rapidapi.com",
        "x-rapidapi-key":  RAPIDAPI_KEY
    }
    payload = {"text": text_to_scan}

    try:
        print("\n[AI] Routing document to AI Content Detector...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)

        limit     = response.headers.get("x-ratelimit-requests-limit", "Unknown")
        remaining = response.headers.get("x-ratelimit-requests-remaining", "Unknown")
        print(f"[API WALLET] AI Detector Quota: {limit} | Left: {remaining}")

        if response.status_code == 200:
            data = response.json()
            print(f"[AI] Raw Response: {data}")

            ai_val       = 0
            possible_keys = [
                'ai_percentage', 'ai_score', 'aiScore', 'aiPercentage',
                'fakePercentage', 'isGpt', 'score', 'percentage', 'ai'
            ]

            for k in possible_keys:
                if k in data:
                    ai_val = data[k]
                    break
            else:
                for k, v in data.items():
                    if isinstance(v, dict):
                        for sub_k in possible_keys:
                            if sub_k in v:
                                ai_val = v[sub_k]
                                break
                    if ai_val:
                        break

            def clean_score(val):
                if val is None:
                    return 0
                if isinstance(val, (int, float)):
                    return int(val * 100) if 0 < val <= 1.0 else int(val)
                if isinstance(val, str):
                    cleaned = val.replace('%', '').strip()
                    try:
                        f = float(cleaned)
                        return int(f * 100) if 0 < f <= 1.0 else int(f)
                    except ValueError:
                        return 0
                return 0

            ai_score = clean_score(ai_val)
            print(f"[AI] Score: {ai_score}%")
            return ai_score
        else:
            print(f"[!] AI API Error {response.status_code}: {response.text}")
            return 0
    except Exception as e:
        print(f"[!] AI Connection Failed: {e}")
        return 0


# ──────────────────────────────────────────────────────────────────────────────
# RAPIDAPI — PLAGIARISM CHECKER
# ──────────────────────────────────────────────────────────────────────────────
def get_rapidapi_plagiarism_score(text_to_scan):
    url     = "https://plagiarism-checker-and-auto-citation-generator-multi-lingual.p.rapidapi.com/plagiarism"
    headers = {
        "Content-Type":    "application/json",
        "x-rapidapi-host": "plagiarism-checker-and-auto-citation-generator-multi-lingual.p.rapidapi.com",
        "x-rapidapi-key":  RAPIDAPI_KEY
    }
    payload = {
        "text":             text_to_scan,
        "language":         "en",
        "includeCitations": False,
        "scrapeSources":    True
    }

    try:
        print("\n[PLAG] Routing document to RapidAPI Plagiarism Engine...")
        response = requests.post(url, json=payload, headers=headers, timeout=50)

        limit     = response.headers.get("x-ratelimit-requests-limit", "Unknown")
        remaining = response.headers.get("x-ratelimit-requests-remaining", "Unknown")
        print(f"[API WALLET] Plagiarism Quota: {limit} | Left: {remaining}")

        if response.status_code == 200:
            data         = response.json()
            plag_score   = int(data.get("percentPlagiarism", 0))
            raw_sources  = data.get("sources", [])
            sources_list = []

            for src in raw_sources:
                sources_list.append({
                    "title":        src.get("title", "Internet Database Match"),
                    "url":          src.get("url", ""),
                    "matchedWords": src.get("matchedWords", "Multiple"),
                    "similarity":   src.get("similarity", 0),
                })

            print(f"[PLAG] Score: {plag_score}% | Sources: {len(sources_list)}")
            return plag_score, sources_list
        else:
            print(f"[!] Plagiarism API Error {response.status_code}: {response.text}")
            return 0, []

    except requests.exceptions.Timeout:
        print("[!] Plagiarism API Timed Out.")
        return 0, []
    except Exception as e:
        print(f"[!] Plagiarism Connection Failed: {e}")
        return 0, []


# ──────────────────────────────────────────────────────────────────────────────
# MAIN HYBRID REPORT
# ──────────────────────────────────────────────────────────────────────────────
def get_hybrid_report(text):
    if not text or len(text) < 50:
        print("[!] Text too short. Skipping.")
        return {"plag_score": 0, "ai_score": 0, "scan_id": None, "matched_sources": []}

    scan_id = str(uuid.uuid4())
    print(f"\n{'='*55}")
    print(f"   HYBRID SCAN STARTED: {scan_id}")
    print(f"{'='*55}")

    # Step 1 — AI Detection
    ai_score = get_rapidapi_ai_score(text)

    # Step 2 — Plagiarism Check
    plag_score, matched_sources = get_rapidapi_plagiarism_score(text)

    print(f"\n{'='*55}")
    print(f"   COMPLETE → AI: {ai_score}% | Plag: {plag_score}% | Sources: {len(matched_sources)}")
    print(f"{'='*55}\n")

    return {
        "plag_score":       plag_score,
        "ai_score":         ai_score,
        "scan_id":          scan_id,
        "matched_sources":  matched_sources,
        "analysis_results": [{"type": "normal", "text": text}]
    }


# ──────────────────────────────────────────────────────────────────────────────
# KEPT FOR COMPATIBILITY — Copyleaks functions (stubbed out)
# ──────────────────────────────────────────────────────────────────────────────
def get_copyleaks_token():
    return None

def get_copyleaks_ai_score(token, text, scan_id):
    return 0