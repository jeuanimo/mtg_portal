from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.decorators import staff_required

from .imap_client import (
    IMAPError,
    delete_message,
    fetch_folders,
    fetch_inbox,
    fetch_message,
    fetch_sent,
    fetch_sent_message,
    mark_unread,
    save_to_sent,
    toggle_important,
)
from .models import EmailDraft


# ── Inbox ─────────────────────────────────────────────────────────────────────

@staff_required
def email_inbox(request):
    try:
        emails = fetch_inbox(limit=50)
        error = None
    except IMAPError as e:
        emails = []
        error = str(e)
    return render(request, 'inbox/email/inbox.html', {'emails': emails, 'error': error})


@staff_required
def email_detail(request, uid):
    try:
        message = fetch_message(uid)
        error = None
    except IMAPError as e:
        message = None
        error = str(e)
    return render(request, 'inbox/email/detail.html', {'message': message, 'error': error})


# ── Actions ───────────────────────────────────────────────────────────────────

@staff_required
@require_POST
def email_mark_important(request, uid):
    flagged = request.POST.get('flagged') == '1'
    try:
        toggle_important(uid, flagged)
        label = 'marked as important' if flagged else 'unmarked'
        messages.success(request, f'Message {label}.')
    except IMAPError as e:
        messages.error(request, f'Could not update flag: {e}')
    return redirect('inbox:email_detail', uid=uid)


@staff_required
@require_POST
def email_mark_unread(request, uid):
    try:
        mark_unread(uid)
        messages.success(request, 'Message marked as unread.')
    except IMAPError as e:
        messages.error(request, f'Could not mark as unread: {e}')
    return redirect('inbox:email_inbox')


@staff_required
@require_POST
def email_delete(request, uid):
    try:
        delete_message(uid)
        messages.success(request, 'Message deleted.')
    except IMAPError as e:
        messages.error(request, f'Could not delete message: {e}')
    return redirect('inbox:email_inbox')


# ── Sent ──────────────────────────────────────────────────────────────────────

@staff_required
def email_sent(request):
    try:
        emails, folder = fetch_sent(limit=50)
        error = None
        available_folders = None
    except IMAPError as e:
        emails, folder, error = [], '', str(e)
        try:
            available_folders = fetch_folders()
        except IMAPError:
            available_folders = None
    return render(request, 'inbox/email/sent.html', {
        'emails': emails,
        'folder': folder,
        'error': error,
        'available_folders': available_folders,
    })


@staff_required
def email_sent_detail(request, uid):
    try:
        message = fetch_sent_message(uid)
        error = None
    except IMAPError as e:
        message, error = None, str(e)
    return render(request, 'inbox/email/sent_detail.html', {'message': message, 'error': error})


# ── Compose & Drafts ──────────────────────────────────────────────────────────

@staff_required
def email_compose(request, draft_pk=None):
    draft = get_object_or_404(EmailDraft, pk=draft_pk, created_by=request.user) if draft_pk else None

    if request.method == 'POST':
        data = _parse_compose_form(request.POST)
        if request.POST.get('action') == 'send' and data['to']:
            return _send_compose(request, data, draft)
        return _save_draft(request, data, draft)

    # Pre-fill from query string (e.g. forward/reply links)
    prefill = None
    if not draft and (request.GET.get('to') or request.GET.get('subject')):
        prefill = {
            'to': request.GET.get('to', ''),
            'subject': request.GET.get('subject', ''),
        }

    return render(request, 'inbox/email/compose.html', {'draft': draft, 'prefill': prefill})


def _parse_compose_form(post):
    return {
        'to': post.get('to', '').strip(),
        'cc': post.get('cc', '').strip(),
        'subject': post.get('subject', '').strip(),
        'body': post.get('body', ''),
    }


def _send_compose(request, data, draft):
    from django.core.mail import EmailMessage as DjangoEmail
    try:
        msg = DjangoEmail(
            subject=data['subject'],
            body=data['body'],
            from_email=None,
            to=[t.strip() for t in data['to'].split(',') if t.strip()],
            cc=[c.strip() for c in data['cc'].split(',') if c.strip()] if data['cc'] else [],
        )
        msg.send()
        save_to_sent(msg.message().as_bytes())
    except Exception as e:
        messages.error(request, f'Failed to send email: {e}')
        return redirect('inbox:email_compose')
    if draft:
        draft.delete()
    messages.success(request, f"Email sent to {data['to']}.")
    return redirect('inbox:email_inbox')


def _save_draft(request, data, draft):
    if draft:
        for field, value in data.items():
            setattr(draft, field, value)
        draft.save()
    else:
        draft = EmailDraft.objects.create(**data, created_by=request.user)
    messages.success(request, 'Draft saved.')
    return redirect('inbox:email_draft_edit', draft_pk=draft.pk)


@staff_required
def email_draft_list(request):
    drafts = EmailDraft.objects.filter(created_by=request.user)
    return render(request, 'inbox/email/drafts.html', {'drafts': drafts})


@staff_required
@require_POST
def email_draft_delete(request, pk):
    draft = get_object_or_404(EmailDraft, pk=pk, created_by=request.user)
    draft.delete()
    messages.success(request, 'Draft deleted.')
    return redirect('inbox:email_draft_list')
