import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .utils import extract_text_from_file, get_hybrid_report, humanize_text_rapidapi, get_rapidapi_ai_score, segment_and_tag_text
from .models import ScanReport

MAX_WORDS_LIMIT = 1000


def enforce_word_limit(text):
    if not text:
        return ""
    words = text.split()
    if len(words) > MAX_WORDS_LIMIT:
        return " ".join(words[:MAX_WORDS_LIMIT])
    return text


@login_required
def dashboard(request):
    recent_scans = ScanReport.objects.filter(user=request.user).order_by('-scan_date')[:5]
    if request.method == 'POST':
        text = ""
        filename = "Manual Entry Matrix"
        if 'document' in request.FILES:
            uploaded_file = request.FILES['document']
            text = extract_text_from_file(uploaded_file)
            filename = uploaded_file.name
        elif 'text_input' in request.POST:
            text = request.POST['text_input']

        text = enforce_word_limit(text)
        report_data = None

        if text.strip():
            report_data = get_hybrid_report(text)
            ScanReport.objects.create(
                user=request.user,
                filename=filename,
                text_content=text,
                plag_score=report_data['plag_score'],
                ai_score=report_data['ai_score'],
                scan_id=report_data.get('scan_id'),
                status="completed"
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
    result = None

    if request.method == 'POST':
        # Server-side file extraction — no JS PDF parsing needed
        if 'document' in request.FILES and request.FILES['document']:
            text = extract_text_from_file(request.FILES['document'])
        else:
            text = request.POST.get('text_input', '')

        # Enforce 1000 word limit
        text = enforce_word_limit(text)

        if text.strip():
            ai_score = get_rapidapi_ai_score(text)
            human_score = 100 - ai_score
            analysis_results = segment_and_tag_text(text, ai_score, [])
            result = {
                'ai_score':         ai_score,
                'human_score':      human_score,
                'mixed_score':      0,
                'analysis_results': analysis_results,
            }

    return render(request, 'analyzer/ai_detector.html', {'text': text, 'result': result})


@login_required
def humanizer(request):
    text = ""
    result = None

    if request.method == 'POST':
        # Server-side file extraction
        if 'document' in request.FILES and request.FILES['document']:
            text = extract_text_from_file(request.FILES['document'])
        else:
            text = request.POST.get('text_input', '')

        # Enforce 1000 word limit — saves API credits
        text = enforce_word_limit(text)

        if text.strip():
            humanized_text = humanize_text_rapidapi(text)

            # Word change count
            original_words  = text.split()
            humanized_words = humanized_text.split() if humanized_text else []
            words_changed   = sum(1 for a, b in zip(original_words, humanized_words) if a != b)

            # Sentence rewrite count
            orig_sents   = [s.strip() for s in text.split('.') if s.strip()]
            human_sents  = [s.strip() for s in humanized_text.split('.') if s.strip()] if humanized_text else []
            sents_changed = sum(1 for a, b in zip(orig_sents, human_sents) if a != b)

            # Tag sentences for highlighting
            analysis_results = []
            for i, sent in enumerate(human_sents):
                orig = orig_sents[i] if i < len(orig_sents) else ""
                tag  = "rewritten" if sent.strip() != orig.strip() else "unchanged"
                analysis_results.append({"text": sent + ". ", "type": tag})

            result = {
                'humanized_text':      humanized_text,
                # No original_ai_score or new_ai_score — removed to save API credits
                'words_changed':       words_changed,
                'sentences_rewritten': sents_changed,
                'analysis_results':    analysis_results,
            }

    return render(request, 'analyzer/humanizer.html', {'result': result, 'text': text})


@login_required
def writing_assistant(request):
    return render(request, 'analyzer/writing_assistant.html')