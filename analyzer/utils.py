import os
import requests
import PyPDF2
import docx
import uuid
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
env_path    = os.path.join(current_dir, '.env')
load_dotenv(env_path)

# ─── Environment Variables ────────────────────────────────────────────────────
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
NGROK_URL = os.getenv("NGROK_URL", "https://colony-march-imitation.ngrok-free.dev")

print("\n--- ENVIRONMENT INITIALIZATION ---")
print(f"RapidAPI Key Loaded : {'YES' if RAPIDAPI_KEY else 'NO (Check .env file)'}")
print(f"Ngrok URL           : {NGROK_URL}")
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
    url = "https://ai-humanizer-api.p.rapidapi.com/"
    
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": "ai-humanizer-api.p.rapidapi.com",
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    
    payload = {
        "text": text_to_scan,
        "level": "standard"
    }
    
    try:
        print("\n[HUMANIZE] Routing text to RapidAPI Humanizer...")
        response = requests.post(url, json=payload, headers=headers)
        
        limit = response.headers.get("x-ratelimit-requests-limit", "Unknown")
        remaining = response.headers.get("x-ratelimit-requests-remaining", "Unknown")
        print(f"[API WALLET] Humanizer Quota: {limit} | Left: {remaining}")
        
        if response.status_code == 200:
            data = response.json()
            humanized = data.get("humanized_text", data.get("text", text_to_scan))
            print("[HUMANIZE] Success! Text converted to human style.")
            return humanized
        else:
            print(f"[!] Humanizer API Error {response.status_code}: {response.text}")
            return text_to_scan
    except Exception as e:
        print(f"[!] Humanizer Connection Failed: {e}")
        return text_to_scan


# ──────────────────────────────────────────────────────────────────────────────
# RAPIDAPI — AI DETECTION (ZeroGPT2)
# ──────────────────────────────────────────────────────────────────────────────
def get_rapidapi_ai_score(text_to_scan):
    url = "https://zerogpt2.p.rapidapi.com/Gptcheck"
    
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": "zerogpt2.p.rapidapi.com",
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    
    payload = {"text": text_to_scan}
    
    try:
        print("\n[AI] Routing document to RapidAPI ZeroGPT Engine...")
        response = requests.post(url, json=payload, headers=headers)
        
        limit = response.headers.get("x-ratelimit-requests-limit", "Unknown")
        remaining = response.headers.get("x-ratelimit-requests-remaining", "Unknown")
        print(f"[API WALLET] ZeroGPT Quota: {limit} | Left: {remaining}")
        
        if response.status_code == 200:
            data = response.json()
            ai_score = data.get("isGpt", data.get("data", {}).get("is_gpt_generated", 0))
            print(f"[AI] Success! AI Score: {ai_score}%")
            return int(ai_score)
        else:
            print(f"[!] AI API Error {response.status_code}: {response.text}")
            return 0
    except Exception as e:
        print(f"[!] AI Connection Failed: {e}")
        return 0


# ──────────────────────────────────────────────────────────────────────────────
# RAPIDAPI — PLAGIARISM CHECKER (Smodin with scrapeSources & timeout fixes)
# ──────────────────────────────────────────────────────────────────────────────
def get_rapidapi_plagiarism_score(text_to_scan):
    url = "https://plagiarism-checker-and-auto-citation-generator-multi-lingual.p.rapidapi.com/plagiarism"
    
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": "plagiarism-checker-and-auto-citation-generator-multi-lingual.p.rapidapi.com",
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    
    payload = {
        "text": text_to_scan,
        "language": "en",
        "includeCitations": False,
        "scrapeSources": True  # MUST be true to check the internet
    }
    
    try:
        print("\n[PLAG] Routing document to RapidAPI Plagiarism Engine...")
        # Added timeout=50 to prevent endless loading loops
        response = requests.post(url, json=payload, headers=headers, timeout=50)
        
        limit = response.headers.get("x-ratelimit-requests-limit", "Unknown")
        remaining = response.headers.get("x-ratelimit-requests-remaining", "Unknown")
        print(f"[API WALLET] Plagiarism Quota: {limit} | Left: {remaining}")
        
        if response.status_code == 200:
            data = response.json()
            
            plag_score = int(data.get("percentPlagiarism", 0))
            raw_sources = data.get("sources", [])
            sources_list = []
            
            for src in raw_sources:
                sources_list.append({
                    "title": src.get("title", "Internet Database Match"),
                    "url": src.get("url", ""),
                    "matchedWords": "Multiple"
                })
                
            print(f"[PLAG] Success! Score: {plag_score}% | Found {len(sources_list)} sources.")
            return plag_score, sources_list
        else:
            print(f"[!] Plagiarism API Error {response.status_code}: {response.text}")
            return 0, []
            
    except requests.exceptions.Timeout:
        print("[!] Plagiarism API Error: Request Timed Out (Took too long to search the web).")
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
    print(f"  HYBRID SCAN STARTED: {scan_id}")
    print(f"{'='*55}")

    ai_score = get_rapidapi_ai_score(text)
    plag_score, matched_sources = get_rapidapi_plagiarism_score(text)

    print(f"\n{'='*55}")
    print(f"  COMPLETE → AI: {ai_score}% | Plag: {plag_score}% | Sources: {len(matched_sources)}")
    print(f"{'='*55}\n")

    analysis_results = [{"type": "normal", "text": text}]

    return {
        "plag_score":      plag_score,
        "ai_score":        ai_score,
        "scan_id":         scan_id,
        "matched_sources": matched_sources,
        "analysis_results": analysis_results
    }