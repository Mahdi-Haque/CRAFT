from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class Conversation(models.Model):
    """
    A conversation represents a private communication thread between two users.
    Enforces exactly two participants, prevents self-conversations, and prevents duplicate pairs.
    """
    participant1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_p1'
    )
    participant2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_p2'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'messaging'
        ordering = ['-updated_at']
        constraints = [
            models.CheckConstraint(
                condition=~Q(participant1=F('participant2')),
                name='prevent_self_conversation'
            ),
            models.UniqueConstraint(
                fields=['participant1', 'participant2'],
                name='unique_conversation_pair'
            ),
        ]

    def __str__(self):
        return f"Conversation: {self.participant1.username} & {self.participant2.username}"

    def clean(self):
        super().clean()
        if self.participant1_id and self.participant2_id and self.participant1_id == self.participant2_id:
            raise ValidationError("A user cannot have a conversation with themselves.")

    @classmethod
    def get_or_create_between(cls, user1, user2):
        """
        Retrieves or creates a conversation between user1 and user2.
        Canonicalizes participant ordering by primary key to guarantee uniqueness.
        """
        if not user1 or not user2 or user1.pk == user2.pk:
            raise ValidationError("Cannot create a conversation with yourself or an invalid user.")
        p1, p2 = (user1, user2) if user1.pk < user2.pk else (user2, user1)
        return cls.objects.get_or_create(participant1=p1, participant2=p2)

    def is_participant(self, user):
        """Checks if a user is one of the two participants."""
        if not user or not user.is_authenticated:
            return False
        return user.id in (self.participant1_id, self.participant2_id)

    def get_other_participant(self, user):
        """Returns the other participant given one participant."""
        if not user or not user.is_authenticated:
            return None
        if user.id == self.participant1_id:
            return self.participant2
        if user.id == self.participant2_id:
            return self.participant1
        return None

    @property
    def latest_message(self):
        """Returns the most recent message in this conversation."""
        return self.messages.order_by('-created_at').first()

    def unread_count_for(self, user):
        """Returns the number of unread messages sent to this user."""
        if not user or not user.is_authenticated:
            return 0
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class Message(models.Model):
    """
    A single message belonging to a Conversation.
    """
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'messaging'
        ordering = ['created_at']

    def __str__(self):
        return f"Message {self.id} by {self.sender.username} in #{self.conversation_id}"

    def clean(self):
        super().clean()
        if self.conversation_id and self.sender_id:
            if not self.conversation.is_participant(self.sender):
                raise ValidationError("Message sender must be a participant in the conversation.")
