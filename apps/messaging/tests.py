from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import IntegrityError
from django.test import TestCase, Client
from django.urls import reverse, resolve
from django.utils import timezone

from .models import Conversation, Message
from .forms import MessageForm, StartConversationForm
from apps.notifications.models import Notification

User = get_user_model()


class MessagingModelTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT,
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@ruet.ac.bd',
            password='Password123!',
            role=User.Role.CLIENT,
        )
        self.user3 = User.objects.create_user(
            username='user3',
            email='user3@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT,
        )

    def test_conversation_has_two_participants(self):
        conv, created = Conversation.get_or_create_between(self.user1, self.user2)
        self.assertTrue(created)
        self.assertIn(conv.participant1, [self.user1, self.user2])
        self.assertIn(conv.participant2, [self.user1, self.user2])
        self.assertNotEqual(conv.participant1, conv.participant2)
        self.assertIn(self.user1.username, str(conv))
        self.assertIn(self.user2.username, str(conv))

    def test_cannot_create_self_conversation_via_helper(self):
        with self.assertRaises(ValidationError):
            Conversation.get_or_create_between(self.user1, self.user1)

    def test_cannot_create_self_conversation_model_clean(self):
        conv = Conversation(participant1=self.user1, participant2=self.user1)
        with self.assertRaises(ValidationError):
            conv.clean()

    def test_database_check_constraint_rejects_self_conversation(self):
        # Even bypassing clean(), SQLite/Postgres CheckConstraint enforces p1 != p2
        with self.assertRaises(IntegrityError):
            Conversation.objects.create(participant1=self.user1, participant2=self.user1)

    def test_duplicate_conversation_between_same_users_prevented_and_reused(self):
        conv1, created1 = Conversation.get_or_create_between(self.user1, self.user2)
        self.assertTrue(created1)

        # Inverting the arguments must return the exact same conversation
        conv2, created2 = Conversation.get_or_create_between(self.user2, self.user1)
        self.assertFalse(created2)
        self.assertEqual(conv1.pk, conv2.pk)
        self.assertEqual(Conversation.objects.count(), 1)

    def test_database_unique_constraint_rejects_duplicate_pairs(self):
        p1, p2 = (self.user1, self.user2) if self.user1.pk < self.user2.pk else (self.user2, self.user1)
        Conversation.objects.create(participant1=p1, participant2=p2)
        with self.assertRaises(IntegrityError):
            Conversation.objects.create(participant1=p1, participant2=p2)

    def test_message_belongs_to_conversation(self):
        conv, _ = Conversation.get_or_create_between(self.user1, self.user2)
        msg = Message.objects.create(
            conversation=conv,
            sender=self.user1,
            content="Hello from user1!"
        )
        self.assertEqual(msg.conversation, conv)
        self.assertEqual(msg.sender, self.user1)
        self.assertFalse(msg.is_read)
        self.assertIn("Hello from user1!", msg.content)
        self.assertTrue(timezone.is_aware(msg.created_at))

    def test_message_chronological_ordering(self):
        conv, _ = Conversation.get_or_create_between(self.user1, self.user2)
        msg1 = Message.objects.create(conversation=conv, sender=self.user1, content="First message")
        msg2 = Message.objects.create(conversation=conv, sender=self.user2, content="Second message")
        msg3 = Message.objects.create(conversation=conv, sender=self.user1, content="Third message")

        messages = list(conv.messages.all())
        self.assertEqual(messages, [msg1, msg2, msg3])

    def test_message_sender_must_belong_to_conversation(self):
        conv, _ = Conversation.get_or_create_between(self.user1, self.user2)
        msg = Message(conversation=conv, sender=self.user3, content="Intruder message")
        with self.assertRaises(ValidationError):
            msg.clean()

    def test_conversation_helper_methods(self):
        conv, _ = Conversation.get_or_create_between(self.user1, self.user2)
        self.assertTrue(conv.is_participant(self.user1))
        self.assertTrue(conv.is_participant(self.user2))
        self.assertFalse(conv.is_participant(self.user3))

        self.assertEqual(conv.get_other_participant(self.user1), self.user2)
        self.assertEqual(conv.get_other_participant(self.user2), self.user1)
        self.assertIsNone(conv.get_other_participant(self.user3))

        # Unread count
        self.assertEqual(conv.unread_count_for(self.user2), 0)
        msg = Message.objects.create(conversation=conv, sender=self.user1, content="Unread message")
        self.assertEqual(conv.unread_count_for(self.user2), 1)
        self.assertEqual(conv.unread_count_for(self.user1), 0)  # Sent by user1, so 0 unread for user1
        self.assertEqual(conv.latest_message, msg)


class MessagingViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='alice',
            email='alice@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT,
        )
        self.user2 = User.objects.create_user(
            username='bob',
            email='bob@ruet.ac.bd',
            password='Password123!',
            role=User.Role.CLIENT,
        )
        self.user3 = User.objects.create_user(
            username='charlie',
            email='charlie@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT,
        )

    def test_anonymous_user_redirected_to_login(self):
        urls = [
            reverse('messaging:conversation_list'),
            reverse('messaging:start_conversation'),
            reverse('messaging:conversation_detail', kwargs={'pk': 1}),
            reverse('messaging:send_message', kwargs={'pk': 1}),
        ]
        for url in urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 302)
            self.assertIn('/login/', res.url)

    def test_authenticated_user_can_access_conversation_list(self):
        self.client.login(username='alice', password='Password123!')
        res = self.client.get(reverse('messaging:conversation_list'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Messages")
        self.assertContains(res, "No Conversations Yet")
        self.assertNotContains(res, 'aria-label="1 unread messages"')

    def test_navbar_shows_only_received_unread_message_count(self):
        conversation, _ = Conversation.get_or_create_between(self.user1, self.user2)
        Message.objects.create(conversation=conversation, sender=self.user2, content='Unread for Alice')
        Message.objects.create(conversation=conversation, sender=self.user1, content='Sent by Alice')

        self.client.login(username='alice', password='Password123!')
        response = self.client.get(reverse('messaging:conversation_list'))
        self.assertEqual(response.context['unread_message_count'], 1)
        self.assertContains(response, 'aria-label="1 unread messages"')

    def test_unread_count_excludes_unrelated_conversations(self):
        related, _ = Conversation.get_or_create_between(self.user1, self.user2)
        unrelated, _ = Conversation.get_or_create_between(self.user2, self.user3)
        Message.objects.create(conversation=related, sender=self.user2, content='Related')
        Message.objects.create(conversation=unrelated, sender=self.user3, content='Unrelated')

        self.client.login(username='alice', password='Password123!')
        response = self.client.get(reverse('messaging:conversation_list'))
        self.assertEqual(response.context['unread_message_count'], 1)

    def test_unauthenticated_requests_have_no_unread_count(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.context['unread_message_count'], 0)

    def test_user_only_sees_their_own_conversations(self):
        # Alice & Bob have a conversation
        conv_ab, _ = Conversation.get_or_create_between(self.user1, self.user2)
        Message.objects.create(conversation=conv_ab, sender=self.user1, content="Secret between Alice and Bob")

        # Bob & Charlie have a conversation
        conv_bc, _ = Conversation.get_or_create_between(self.user2, self.user3)
        Message.objects.create(conversation=conv_bc, sender=self.user3, content="Secret between Bob and Charlie")

        # Alice logs in
        self.client.login(username='alice', password='Password123!')
        res = self.client.get(reverse('messaging:conversation_list'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "bob")
        self.assertNotContains(res, "charlie")
        self.assertContains(res, "Secret between Alice and Bob")
        self.assertNotContains(res, "Secret between Bob and Charlie")

    def test_user_can_start_conversation_via_post(self):
        self.client.login(username='alice', password='Password123!')
        res = self.client.post(reverse('messaging:start_conversation'), {
            'recipient': self.user2.pk
        })
        self.assertEqual(res.status_code, 302)
        conv = Conversation.objects.first()
        self.assertIsNotNone(conv)
        self.assertRedirects(res, reverse('messaging:conversation_detail', kwargs={'pk': conv.pk}))

    def test_get_user_param_only_preselects_recipient(self):
        self.client.login(username='alice', password='Password123!')
        res = self.client.get(reverse('messaging:start_conversation') + f"?user={self.user2.pk}")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, f'<option value="{self.user2.pk}" selected', html=False)
        self.assertEqual(Conversation.objects.count(), 0)

    def test_user_cannot_start_conversation_with_self_via_post(self):
        self.client.login(username='alice', password='Password123!')
        res = self.client.post(reverse('messaging:start_conversation'), {
            'recipient': self.user1.pk
        })
        # Form excludes current user so this causes form error or view check
        self.assertEqual(Conversation.objects.count(), 0)

    def test_user_cannot_start_conversation_with_self_via_get(self):
        self.client.login(username='alice', password='Password123!')
        res = self.client.get(reverse('messaging:start_conversation') + f"?user={self.user1.pk}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Conversation.objects.count(), 0)

    def test_existing_conversation_is_reused_on_start(self):
        conv, _ = Conversation.get_or_create_between(self.user1, self.user2)
        self.client.login(username='alice', password='Password123!')
        res = self.client.post(reverse('messaging:start_conversation'), {
            'recipient': self.user2.pk
        })
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, reverse('messaging:conversation_detail', kwargs={'pk': conv.pk}))
        self.assertEqual(Conversation.objects.count(), 1)

    def test_participant_can_open_conversation(self):
        conv, _ = Conversation.get_or_create_between(self.user1, self.user2)
        Message.objects.create(conversation=conv, sender=self.user2, content="Hi Alice!")

        self.client.login(username='alice', password='Password123!')
        res = self.client.get(reverse('messaging:conversation_detail', kwargs={'pk': conv.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Hi Alice!")
        self.assertContains(res, "bob")

    def test_non_participant_cannot_open_conversation(self):
        conv, _ = Conversation.get_or_create_between(self.user1, self.user2)
        self.client.login(username='charlie', password='Password123!')
        res = self.client.get(reverse('messaging:conversation_detail', kwargs={'pk': conv.pk}))
        self.assertEqual(res.status_code, 403)

    def test_opening_conversation_marks_received_messages_as_read(self):
        conv, _ = Conversation.get_or_create_between(self.user1, self.user2)
        msg_from_bob = Message.objects.create(conversation=conv, sender=self.user2, content="Bob message", is_read=False)
        msg_from_alice = Message.objects.create(conversation=conv, sender=self.user1, content="Alice message", is_read=False)

        # Alice opens conversation
        self.client.login(username='alice', password='Password123!')
        res = self.client.get(reverse('messaging:conversation_detail', kwargs={'pk': conv.pk}))
        self.assertEqual(res.status_code, 200)

        msg_from_bob.refresh_from_db()
        msg_from_alice.refresh_from_db()

        self.assertTrue(msg_from_bob.is_read)       # Received by Alice -> marked as read
        self.assertFalse(msg_from_alice.is_read)    # Sent by Alice -> remains False until Bob reads it

    def test_participant_can_send_message_via_post(self):
        conv, _ = Conversation.get_or_create_between(self.user1, self.user2)
        self.client.login(username='alice', password='Password123!')

        res = self.client.post(reverse('messaging:send_message', kwargs={'pk': conv.pk}), {
            'content': 'Hello Bob, looking forward to working with you.'
        })
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, reverse('messaging:conversation_detail', kwargs={'pk': conv.pk}))

        self.assertEqual(conv.messages.count(), 1)
        msg = conv.messages.first()
        self.assertEqual(msg.sender, self.user1)
        self.assertEqual(msg.content, 'Hello Bob, looking forward to working with you.')

    def test_sending_message_notifies_other_participant(self):
        conv, _ = Conversation.get_or_create_between(self.user1, self.user2)
        self.client.login(username='alice', password='Password123!')

        response = self.client.post(
            reverse('messaging:send_message', kwargs={'pk': conv.pk}),
            {'content': 'Hello Bob'},
        )

        self.assertEqual(response.status_code, 302)
        notifications = Notification.objects.filter(
            notification_type=Notification.NotificationType.NEW_MESSAGE
        )
        self.assertEqual(notifications.count(), 1)
        notification = notifications.get()
        self.assertEqual(notification.recipient, self.user2)
        self.assertEqual(notification.title, 'New message')
        self.assertEqual(notification.message, 'alice sent you a new message.')
        self.assertEqual(
            notification.link,
            reverse('messaging:conversation_detail', kwargs={'pk': conv.pk}),
        )
        self.assertFalse(
            Notification.objects.filter(recipient=self.user1).exists()
        )

    def test_multiple_messages_create_separate_notifications_newest_first(self):
        conv, _ = Conversation.get_or_create_between(self.user1, self.user2)
        self.client.login(username='alice', password='Password123!')

        self.client.post(
            reverse('messaging:send_message', kwargs={'pk': conv.pk}),
            {'content': 'First message'},
        )
        self.client.post(
            reverse('messaging:send_message', kwargs={'pk': conv.pk}),
            {'content': 'Second message'},
        )

        notifications = Notification.objects.filter(recipient=self.user2)
        self.assertEqual(notifications.count(), 2)
        self.assertEqual(
            list(notifications.values_list('message', flat=True)),
            [
                'alice sent you a new message.',
                'alice sent you a new message.',
            ],
        )
        self.assertGreaterEqual(
            notifications.first().created_at,
            notifications.last().created_at,
        )

    def test_non_participant_cannot_send_message(self):
        conv, _ = Conversation.get_or_create_between(self.user1, self.user2)
        self.client.login(username='charlie', password='Password123!')

        res = self.client.post(reverse('messaging:send_message', kwargs={'pk': conv.pk}), {
            'content': 'Spam message from Charlie'
        })
        self.assertEqual(res.status_code, 403)
        self.assertEqual(conv.messages.count(), 0)

    def test_send_message_requires_post_method(self):
        conv, _ = Conversation.get_or_create_between(self.user1, self.user2)
        self.client.login(username='alice', password='Password123!')

        res = self.client.get(reverse('messaging:send_message', kwargs={'pk': conv.pk}))
        self.assertEqual(res.status_code, 403)

    def test_empty_or_whitespace_message_rejected(self):
        conv, _ = Conversation.get_or_create_between(self.user1, self.user2)
        self.client.login(username='alice', password='Password123!')

        res = self.client.post(reverse('messaging:send_message', kwargs={'pk': conv.pk}), {
            'content': '   \n\t   '
        })
        self.assertEqual(res.status_code, 302)
        self.assertEqual(conv.messages.count(), 0)


class MessagingURLTests(TestCase):
    def test_urls_reverse_and_resolve(self):
        self.assertEqual(reverse('messaging:conversation_list'), '/messages/')
        self.assertEqual(reverse('messaging:start_conversation'), '/messages/start/')
        self.assertEqual(reverse('messaging:conversation_detail', kwargs={'pk': 42}), '/messages/42/')
        self.assertEqual(reverse('messaging:send_message', kwargs={'pk': 42}), '/messages/42/send/')

        self.assertEqual(resolve('/messages/').view_name, 'messaging:conversation_list')
        self.assertEqual(resolve('/messages/start/').view_name, 'messaging:start_conversation')
        self.assertEqual(resolve('/messages/42/').view_name, 'messaging:conversation_detail')
        self.assertEqual(resolve('/messages/42/send/').view_name, 'messaging:send_message')
