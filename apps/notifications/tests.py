from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from .models import Notification
from .services import create_notification


User = get_user_model()


class NotificationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='notification-user',
            email='notification@example.com',
            password='Password123!',
        )

    def test_notification_can_be_created_for_user(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.NEW_MESSAGE,
            title='New message',
            message='You have received a new message.',
            link='/messages/1/',
        )

        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.title, 'New message')

    def test_new_notification_is_unread_by_default(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.TEAM_ADDED,
            title='Team update',
            message='You were added to a team.',
        )

        self.assertFalse(notification.is_read)

    def test_all_required_notification_types_exist(self):
        self.assertEqual(
            set(Notification.NotificationType.values),
            {
                'new_message',
                'new_application',
                'application_accepted',
                'application_rejected',
                'team_added',
                'project_started',
                'project_completed',
                'project_closed',
            },
        )

    def test_user_notifications_related_manager_returns_notifications(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.NEW_APPLICATION,
            title='New application',
            message='A student applied to your project.',
        )

        self.assertIn(notification, self.user.notifications.all())

    def test_notifications_are_ordered_newest_first(self):
        older = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.NEW_MESSAGE,
            title='Older',
            message='Older notification',
        )
        newer = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.APPLICATION_ACCEPTED,
            title='Newer',
            message='Newer notification',
        )
        Notification.objects.filter(pk=older.pk).update(
            created_at=timezone.now() - timedelta(days=1)
        )

        self.assertEqual(list(self.user.notifications.all()), [newer, older])

    def test_string_representation_identifies_recipient_and_title(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.APPLICATION_REJECTED,
            title='Application update',
            message='Your application was rejected.',
        )

        self.assertEqual(str(notification), 'notification-user: Application update')

    def test_link_is_optional(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.NEW_MESSAGE,
            title='New message',
            message='You have received a new message.',
            link='',
        )

        self.assertEqual(notification.link, '')


class NotificationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='service-test-user',
            email='service@example.com',
            password='Password123!',
        )

    def test_create_notification_creates_notification(self):
        notification = create_notification(
            recipient=self.user,
            notification_type=Notification.NotificationType.NEW_MESSAGE,
            title='Test notification',
            message='Test message content',
            link='/test/',
        )

        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.title, 'Test notification')
        self.assertEqual(notification.link, '/test/')
        self.assertFalse(notification.is_read)

    def test_create_notification_works_without_link(self):
        notification = create_notification(
            recipient=self.user,
            notification_type=Notification.NotificationType.TEAM_ADDED,
            title='Team added',
            message='You were added to a team',
        )

        self.assertEqual(notification.link, '')
        self.assertTrue(Notification.objects.filter(pk=notification.pk).exists())


class NotificationListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='Password123!',
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='Password123!',
        )

    def test_notification_list_requires_authentication(self):
        response = self.client.get(reverse('notifications:notification_list'))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login'))

    def test_authenticated_user_can_access_notification_list(self):
        self.client.login(username='user1', password='Password123!')
        response = self.client.get(reverse('notifications:notification_list'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'notifications/notification_list.html'
        )

    def test_user_sees_only_own_notifications(self):
        notification1 = Notification.objects.create(
            recipient=self.user1,
            notification_type=Notification.NotificationType.NEW_MESSAGE,
            title='User 1 notification',
            message='This is for user 1',
        )
        notification2 = Notification.objects.create(
            recipient=self.user2,
            notification_type=Notification.NotificationType.NEW_MESSAGE,
            title='User 2 notification',
            message='This is for user 2',
        )

        self.client.login(username='user1', password='Password123!')
        response = self.client.get(reverse('notifications:notification_list'))

        self.assertContains(response, 'User 1 notification')
        self.assertNotContains(response, 'User 2 notification')

    def test_notifications_appear_newest_first(self):
        older = Notification.objects.create(
            recipient=self.user1,
            notification_type=Notification.NotificationType.NEW_MESSAGE,
            title='Older',
            message='Older notification',
        )
        newer = Notification.objects.create(
            recipient=self.user1,
            notification_type=Notification.NotificationType.APPLICATION_ACCEPTED,
            title='Newer',
            message='Newer notification',
        )
        Notification.objects.filter(pk=older.pk).update(
            created_at=timezone.now() - timedelta(days=1)
        )

        self.client.login(username='user1', password='Password123!')
        response = self.client.get(reverse('notifications:notification_list'))
        notifications = response.context['notifications']

        self.assertEqual(list(notifications), [newer, older])

    def test_empty_state_when_no_notifications(self):
        self.client.login(username='user1', password='Password123!')
        response = self.client.get(reverse('notifications:notification_list'))

        self.assertContains(response, 'No Notifications')


class MarkNotificationAsReadTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='Password123!',
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='Password123!',
        )
        self.notification = Notification.objects.create(
            recipient=self.user1,
            notification_type=Notification.NotificationType.NEW_MESSAGE,
            title='Test',
            message='Test message',
            link='/messages/',
        )

    def test_own_unread_notification_becomes_read(self):
        self.client.login(username='user1', password='Password123!')
        response = self.client.post(
            reverse('notifications:mark_as_read', args=[self.notification.pk])
        )

        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    def test_another_users_notification_cannot_be_modified(self):
        self.client.login(username='user2', password='Password123!')
        response = self.client.post(
            reverse('notifications:mark_as_read', args=[self.notification.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.notification.refresh_from_db()
        self.assertFalse(self.notification.is_read)

    def test_notification_with_link_redirects_to_link(self):
        self.client.login(username='user1', password='Password123!')
        response = self.client.post(
            reverse('notifications:mark_as_read', args=[self.notification.pk]),
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/messages/')

    def test_notification_without_link_returns_to_notification_list(self):
        notification_no_link = Notification.objects.create(
            recipient=self.user1,
            notification_type=Notification.NotificationType.TEAM_ADDED,
            title='Team added',
            message='You were added to a team',
        )

        self.client.login(username='user1', password='Password123!')
        response = self.client.post(
            reverse('notifications:mark_as_read', args=[notification_no_link.pk]),
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, reverse('notifications:notification_list')
        )


class MarkAllNotificationsAsReadTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='Password123!',
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='Password123!',
        )

        self.notification1 = Notification.objects.create(
            recipient=self.user1,
            notification_type=Notification.NotificationType.NEW_MESSAGE,
            title='Notification 1',
            message='Message 1',
        )
        self.notification2 = Notification.objects.create(
            recipient=self.user1,
            notification_type=Notification.NotificationType.APPLICATION_ACCEPTED,
            title='Notification 2',
            message='Message 2',
        )
        self.notification3 = Notification.objects.create(
            recipient=self.user2,
            notification_type=Notification.NotificationType.NEW_APPLICATION,
            title='User 2 notification',
            message='Message for user 2',
        )

    def test_all_current_users_unread_notifications_become_read(self):
        self.client.login(username='user1', password='Password123!')
        self.client.post(reverse('notifications:mark_all_as_read'))

        self.notification1.refresh_from_db()
        self.notification2.refresh_from_db()
        self.assertTrue(self.notification1.is_read)
        self.assertTrue(self.notification2.is_read)

    def test_another_users_unread_notifications_remain_unread(self):
        self.client.login(username='user1', password='Password123!')
        self.client.post(reverse('notifications:mark_all_as_read'))

        self.notification3.refresh_from_db()
        self.assertFalse(self.notification3.is_read)

    def test_redirects_to_notification_list(self):
        self.client.login(username='user1', password='Password123!')
        response = self.client.post(
            reverse('notifications:mark_all_as_read'), follow=False
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, reverse('notifications:notification_list')
        )


class NotificationContextProcessorTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='context-user',
            email='context@example.com',
            password='Password123!',
        )

    def test_unread_notification_count_for_authenticated_user(self):
        Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.NEW_MESSAGE,
            title='Notification 1',
            message='Message 1',
        )
        Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.APPLICATION_ACCEPTED,
            title='Notification 2',
            message='Message 2',
        )

        self.client.login(username='context-user', password='Password123!')
        response = self.client.get(reverse('notifications:notification_list'))

        self.assertEqual(response.context['unread_notification_count'], 2)

    def test_read_notifications_not_counted(self):
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.NEW_MESSAGE,
            title='Notification 1',
            message='Message 1',
        )
        notification.is_read = True
        notification.save()

        self.client.login(username='context-user', password='Password123!')
        response = self.client.get(reverse('notifications:notification_list'))

        self.assertEqual(response.context['unread_notification_count'], 0)

    def test_zero_for_anonymous_user(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.context['unread_notification_count'], 0)

    def test_another_users_unread_notifications_excluded(self):
        other_user = User.objects.create_user(
            username='other-user',
            email='other@example.com',
            password='Password123!',
        )
        Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.NEW_MESSAGE,
            title='For self',
            message='Message for self',
        )
        Notification.objects.create(
            recipient=other_user,
            notification_type=Notification.NotificationType.NEW_MESSAGE,
            title='For other',
            message='Message for other',
        )

        self.client.login(username='context-user', password='Password123!')
        response = self.client.get(reverse('notifications:notification_list'))

        self.assertEqual(response.context['unread_notification_count'], 1)
