from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from .forms import MessageForm, StartConversationForm
from .models import Conversation, Message

User = get_user_model()


@login_required
def conversation_list(request):
    """
    Lists conversations for the authenticated user, ordered by recent activity.
    Displays other participant, latest message snippet, timestamp, and unread counts.
    """
    conversations = (
        Conversation.objects.filter(
            Q(participant1=request.user) | Q(participant2=request.user)
        )
        .select_related('participant1', 'participant2')
        .prefetch_related('messages')
        .order_by('-updated_at')
    )

    conversation_data = []
    for conv in conversations:
        other_user = conv.get_other_participant(request.user)
        latest_msg = conv.latest_message
        unread_count = conv.unread_count_for(request.user)
        conversation_data.append({
            'conversation': conv,
            'other_user': other_user,
            'latest_message': latest_msg,
            'unread_count': unread_count,
        })

    return render(request, 'messaging/conversation_list.html', {
        'conversation_data': conversation_data,
    })


@login_required
def conversation_detail(request, pk):
    """
    Displays the complete chronological message history for a conversation.
    Marks all received unread messages as read upon viewing.
    Enforces server-side authorization: only the 2 participants can access.
    """
    conversation = get_object_or_404(
        Conversation.objects.select_related('participant1', 'participant2'),
        pk=pk
    )

    if not conversation.is_participant(request.user):
        raise PermissionDenied("You do not have permission to view this conversation.")

    # Mark received unread messages as read
    conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    other_user = conversation.get_other_participant(request.user)
    message_history = conversation.messages.select_related('sender').order_by('created_at')
    form = MessageForm()

    return render(request, 'messaging/conversation_detail.html', {
        'conversation': conversation,
        'other_user': other_user,
        'message_history': message_history,
        'form': form,
    })


@login_required
def start_conversation(request):
    """
    Initiates or retrieves an existing conversation between authenticated user and another user.
    GET requests only render the form; conversation creation is POST-only.
    Guarantees no self-conversations and no duplicate conversation pairs.
    """
    if request.method == 'POST':
        form = StartConversationForm(request.POST, current_user=request.user)
        if form.is_valid():
            recipient = form.cleaned_data['recipient']
            if recipient.pk == request.user.pk:
                messages.error(request, "You cannot start a conversation with yourself.")
                return render(request, 'messaging/start_conversation.html', {'form': form})
            conversation, _ = Conversation.get_or_create_between(request.user, recipient)
            return redirect('messaging:conversation_detail', pk=conversation.pk)
    else:
        form = StartConversationForm(current_user=request.user)
        target_id = request.GET.get('user')
        if target_id:
            try:
                target_user = User.objects.get(pk=target_id, is_active=True)
            except (User.DoesNotExist, ValueError):
                target_user = None
            if target_user and target_user.pk != request.user.pk:
                form.initial['recipient'] = target_user.pk

    return render(request, 'messaging/start_conversation.html', {'form': form})


@login_required
def send_message(request, pk):
    """
    Processes sending a message to a conversation.
    Must be POST, must be authenticated, sender must be a participant.
    """
    if request.method != 'POST':
        raise PermissionDenied("Invalid request method. POST required.")

    conversation = get_object_or_404(Conversation, pk=pk)

    if not conversation.is_participant(request.user):
        raise PermissionDenied("You do not have permission to send messages in this conversation.")

    form = MessageForm(request.POST)
    if form.is_valid():
        message = form.save(commit=False)
        message.conversation = conversation
        message.sender = request.user
        message.save()
        conversation.save()  # Triggers updated_at timestamp update
    else:
        for error in form.errors.get('content', []):
            messages.error(request, error)

    return redirect('messaging:conversation_detail', pk=conversation.pk)
