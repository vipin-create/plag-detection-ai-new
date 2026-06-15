import json
import uuid
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .utils import extract_text_from_file, get_hybrid_report, humanize_text_rapidapi, get_rapidapi_ai_score
from .models import ScanReport

# ================= SERVER-SIDE SECURITY LOCK =================
MAX_WORDS_LIMIT = 1000

def enforce_word_limit(text):
    """
    Helper function to intercept massive documents. 
    It splits the text into words, checks the length, and cleanly 
    slices it at the 1,000-word mark to protect API credits.
    """
    if not text:
        return ""
    
    words = text.split()
    if len(words) > MAX_WORDS_LIMIT:
        return " ".join(words[:MAX_WORDS_LIMIT])
    return text
# =============================================================

@login_required
def dashboard(request):
    recent_scans = ScanReport.objects.filter(user=request.user).order_by('-scan_date')[:5]

    if request.method == 'POST':
        text = ""
        filename = "Manual Entry"

        if 'document' in request.FILES:
            uploaded_file = request.FILES['document']
            text = extract_text_from_file(uploaded_file)
            filename = uploaded_file.name
        elif 'text_input' in request.POST:
            text = request.POST['text_input']

        # --- SECURITY LOCK APPLIED HERE ---
        text = enforce_word_limit(text)
        
        report_data = None

        if text.strip():
            # Run the fully synchronous RapidAPI dual-engine
            report_data = get_hybrid_report(text)
            
            # BULLETPROOF NUMBER GUARD
            if report_data.get('plag_score') is None:
                report_data['plag_score'] = 0
            if report_data.get('ai_score') is None:
                report_data['ai_score'] = 0

            # Create the database record (Now marked "completed" instantly!)
            ScanReport.objects.create(
                user=request.user,
                filename=filename,
                text_content=text,
                plag_score=report_data['plag_score'],
                ai_score=report_data['ai_score'],
                scan_id=report_data.get('scan_id'),
                status="completed",
                matched_sources=report_data.get('matched_sources', [])
            )

        return render(request, 'analyzer/dashboard.html', {
            'report_data': report_data,
            'recent_scans': recent_scans,
            'text': text
        })

    return render(request, 'analyzer/dashboard.html', {'recent_scans': recent_scans})


@login_required
def ai_detector(request):
    text = ""
    ai_score = 0

    if request.method == 'POST':
        if 'document' in request.FILES:
            text = extract_text_from_file(request.FILES['document'])
        else:
            text = request.POST.get('text_input', '')

        # --- SECURITY LOCK APPLIED HERE ---
        text = enforce_word_limit(text)

        if text.strip():
            if len(text) < 50:
                print("\n[!] Text is too short for AI Detection")
                ai_score = 0
            else:
                print("\n--- INITIATING STANDALONE AI SCAN ---")
                ai_score = get_rapidapi_ai_score(text)

    return render(request, 'analyzer/ai_detector.html', {'text': text, 'ai_score': ai_score})


@login_required
def humanizer(request):
    text = ""
    humanized_text = ""

    if request.method == 'POST':
        text = request.POST.get('text_input', '')
        
        # --- SECURITY LOCK APPLIED HERE ---
        text = enforce_word_limit(text)
        
        if text.strip():
            humanized_text = humanize_text_rapidapi(text)
        
    return render(request, 'analyzer/humanizer.html', {
        'original': text, 
        'humanized': humanized_text
    })


@login_required
def writing_assistant(request):
    """View to display the future writing assistant roadmap."""
    return render(request, 'analyzer/writing_assistant.html')