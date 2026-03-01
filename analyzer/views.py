from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .utils import extract_text_from_file, get_hybrid_report, get_ai_score, humanize_text_gemini
from .models import ScanReport

@login_required
def dashboard(request):
    if request.method == 'POST':
        text = ""
        filename = "Manual Entry"

        if 'document' in request.FILES:
            uploaded_file = request.FILES['document']
            text = extract_text_from_file(uploaded_file)
            filename = uploaded_file.name
        elif 'text_input' in request.POST:
            text = request.POST['text_input']

        report = get_hybrid_report(text)
        
        ScanReport.objects.create(
            user=request.user,
            filename=filename,
            text_content=text,
            plag_score=report['plag_score'],
            ai_score=report['ai_score']
        )

        return render(request, 'analyzer/report.html', {
            'text': text,
            'plag_score': report['plag_score'],
            'ai_score': report['ai_score']
        })

    recent_scans = ScanReport.objects.filter(user=request.user).order_by('-scan_date')[:5]
    return render(request, 'analyzer/dashboard.html', {'recent_scans': recent_scans})

@login_required
def ai_detector(request):
    text = ""
    ai_score = None

    if request.method == 'POST':
        if 'document' in request.FILES:
            text = extract_text_from_file(request.FILES['document'])
        else:
            text = request.POST.get('text_input', '')

        if text.strip():
            ai_score = get_ai_score(text) 

    return render(request, 'analyzer/ai_detector.html', {'text': text, 'ai_score': ai_score})

@login_required
def humanizer(request):
    text = ""
    humanized_text = ""

    if request.method == 'POST':
        text = request.POST.get('text_input', '')
        humanized_text = humanize_text_gemini(text)
        
    return render(request, 'analyzer/humanizer.html', {
        'original': text, 
        'humanized': humanized_text
    })

@login_required
def writing_assistant(request):
    """View to display the future writing assistant roadmap."""
    return render(request, 'analyzer/writing_assistant.html')