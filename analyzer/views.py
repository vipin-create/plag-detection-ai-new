from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .utils import extract_text_from_file, get_hybrid_report, humanize_text_gemini
from .models import ScanReport

# =========================================
# 1. DASHBOARD & PLAGIARISM SCANNER
# =========================================
@login_required
def dashboard(request):
    # HANDLE SCANNING (POST REQUEST)
    if request.method == 'POST':
        text = ""
        filename = "Manual Entry"

        # Check for file upload
        if 'document' in request.FILES:
            uploaded_file = request.FILES['document']
            text = extract_text_from_file(uploaded_file)
            filename = uploaded_file.name
        # Check for text input
        elif 'text_input' in request.POST:
            text = request.POST['text_input']

        # Run Analysis
        report = get_hybrid_report(text)
        
        # SAVE TO DATABASE (History)
        ScanReport.objects.create(
            user=request.user,
            filename=filename,
            text_content=text,
            plag_score=report['plag_score'],
            ai_score=report['ai_score']
        )

        # Show Report Page
        return render(request, 'analyzer/report.html', {
            'text': text,
            'plag_score': report['plag_score'],
            'ai_score': report['ai_score']
        })

    # SHOW DASHBOARD + HISTORY (GET REQUEST)
    # Get last 5 scans for this user
    recent_scans = ScanReport.objects.filter(user=request.user).order_by('-scan_date')[:5]

    return render(request, 'analyzer/dashboard.html', {'recent_scans': recent_scans})

# =========================================
# 2. AI DETECTOR VIEW (Restored)
# =========================================
@login_required
def ai_detector(request):
    return render(request, 'analyzer/ai_detector.html')

# =========================================
# 3. HUMANIZER VIEW (Restored)
# =========================================
@login_required
def humanizer(request):
    if request.method == 'POST':
        text = request.POST.get('text_input', '')
        humanized_text = humanize_text_gemini(text)
        return render(request, 'analyzer/humanizer.html', {
            'original': text, 
            'humanized': humanized_text
        })
    return render(request, 'analyzer/humanizer.html')