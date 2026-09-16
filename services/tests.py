from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from services.models import Service

User = get_user_model()


class ServicesDomainTests(TestCase):
    def setUp(self):
        self.client = Client()

        # User 1: Student Creator
        self.creator = User.objects.create_user(
            username='servicecreator',
            email='creator@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT,
            bio='4th year CSE student passionate about embedded systems and web apps.'
        )

        # User 2: Another Student
        self.other_user = User.objects.create_user(
            username='otherstudent',
            email='other@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT
        )

        # User 3: Admin user
        self.admin_user = User.objects.create_user(
            username='adminuser',
            email='admin@ruet.ac.bd',
            password='Password123!',
            role=User.Role.ADMIN,
            is_staff=True
        )

        # Baseline Service (Active)
        self.active_service = Service.objects.create(
            creator=self.creator,
            title='Professional Event Poster Design for RUET Clubs',
            description='I will design modern high-impact promotional posters in Figma and Illustrator.',
            category=Service.Category.GRAPHIC_DESIGN,
            skills='Figma, Illustrator, Photoshop, Print Design',
            delivery_time_days=2,
            price_estimate=20.00,
            is_active=True
        )

        # Baseline Service (Inactive / Paused)
        self.inactive_service = Service.objects.create(
            creator=self.creator,
            title='ESP32 & Arduino Hardware Prototyping',
            description='Custom circuit design and firmware programming for course projects.',
            category=Service.Category.EMBEDDED,
            skills='C++, ESP32, Arduino, KiCAD',
            delivery_time_days=5,
            price_estimate=50.00,
            is_active=False
        )

    def test_service_model_helpers(self):
        """Verify __str__, get_absolute_url, and skills_list property."""
        self.assertIn('Professional Event Poster Design', str(self.active_service))
        self.assertIn(self.creator.username, str(self.active_service))
        self.assertEqual(
            self.active_service.get_absolute_url(),
            reverse('services:service_detail', kwargs={'pk': self.active_service.pk})
        )
        self.assertEqual(
            self.active_service.skills_list,
            ['Figma', 'Illustrator', 'Photoshop', 'Print Design']
        )

    def test_service_list_public_and_active_filtering(self):
        """Public marketplace shows active services and excludes paused ones by default."""
        res = self.client.get(reverse('services:service_list'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Professional Event Poster Design')
        # Paused service shouldn't appear for anonymous guests
        self.assertNotContains(res, 'ESP32 & Arduino Hardware Prototyping')

    def test_service_detail_public(self):
        """Active service detail is publicly readable with full specs."""
        res = self.client.get(reverse('services:service_detail', kwargs={'pk': self.active_service.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Professional Event Poster Design')
        self.assertContains(res, 'Graphic Design')
        self.assertContains(res, '৳ 20.00')
        self.assertContains(res, '~2 Days')
        self.assertContains(res, 'servicecreator')

    def test_inactive_service_detail_hidden_from_strangers(self):
        """Non-owners and unauthenticated users are redirected when accessing inactive services."""
        # Anonymous
        res = self.client.get(reverse('services:service_detail', kwargs={'pk': self.inactive_service.pk}))
        self.assertEqual(res.status_code, 302)

        # Other authenticated student
        self.client.login(username='otherstudent', password='Password123!')
        res2 = self.client.get(reverse('services:service_detail', kwargs={'pk': self.inactive_service.pk}))
        self.assertEqual(res2.status_code, 302)

    def test_inactive_service_detail_visible_to_owner_and_admin(self):
        """The creator can view their own paused service detail with owner controls."""
        self.client.login(username='servicecreator', password='Password123!')
        res = self.client.get(reverse('services:service_detail', kwargs={'pk': self.inactive_service.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Currently Paused')
        self.assertContains(res, 'Resume Availability')

        # Admin also has view privileges
        self.client.login(username='adminuser', password='Password123!')
        res_admin = self.client.get(reverse('services:service_detail', kwargs={'pk': self.inactive_service.pk}))
        self.assertEqual(res_admin.status_code, 200)

    def test_service_create_requires_login(self):
        """Unauthenticated requests to service creation redirect to login."""
        res = self.client.get(reverse('services:service_create'))
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login/', res.url)

    def test_service_create_success(self):
        """Authenticated campus users can publish a valid service offering."""
        self.client.login(username='servicecreator', password='Password123!')
        res = self.client.post(reverse('services:service_create'), {
            'title': 'Full-Stack Django & REST API Development',
            'description': 'End-to-end web apps with clean architecture, database design, and responsive frontend.',
            'category': Service.Category.WEB_DEV,
            'skills': 'Python, Django, PostgreSQL, JavaScript',
            'delivery_time_days': 7,
            'price_estimate': '75.00',
            'is_active': True,
        })
        self.assertEqual(res.status_code, 302)
        new_service = Service.objects.filter(title='Full-Stack Django & REST API Development').first()
        self.assertIsNotNone(new_service)
        self.assertEqual(new_service.creator, self.creator)
        self.assertEqual(float(new_service.price_estimate), 75.00)

    def test_service_form_validation(self):
        """Submitting empty or invalid data rejects form and displays errors."""
        self.client.login(username='servicecreator', password='Password123!')
        res = self.client.post(reverse('services:service_create'), {
            'title': '',  # Required field missing
            'description': '',
            'category': Service.Category.WEB_DEV,
            'delivery_time_days': -5,  # Invalid
        })
        self.assertEqual(res.status_code, 200)
        form = res.context['form']
        self.assertTrue(form.errors)
        self.assertIn('title', form.errors)
        self.assertIn('description', form.errors)
        self.assertContains(res, 'This field is required.')

    def test_service_owner_can_update(self):
        """Owner can update their service details."""
        self.client.login(username='servicecreator', password='Password123!')
        res = self.client.post(reverse('services:service_update', kwargs={'pk': self.active_service.pk}), {
            'title': 'High-Impact Poster & Flyer Design for RUET Clubs',
            'description': 'Updated scope with 3 revisions included.',
            'category': Service.Category.GRAPHIC_DESIGN,
            'skills': 'Figma, Canva, Illustrator',
            'delivery_time_days': 1,
            'price_estimate': '25.00',
            'is_active': True,
        })
        self.assertEqual(res.status_code, 302)
        self.active_service.refresh_from_db()
        self.assertEqual(self.active_service.title, 'High-Impact Poster & Flyer Design for RUET Clubs')
        self.assertEqual(self.active_service.delivery_time_days, 1)

    def test_unauthorized_user_cannot_update(self):
        """Another user receives a 403 Forbidden when trying to edit someone else's service."""
        self.client.login(username='otherstudent', password='Password123!')
        res = self.client.get(reverse('services:service_update', kwargs={'pk': self.active_service.pk}))
        self.assertEqual(res.status_code, 403)

        res_post = self.client.post(reverse('services:service_update', kwargs={'pk': self.active_service.pk}), {
            'title': 'Hacked Title',
            'description': 'Hacked description',
            'category': Service.Category.GRAPHIC_DESIGN,
            'delivery_time_days': 1,
        })
        self.assertEqual(res_post.status_code, 403)
        self.active_service.refresh_from_db()
        self.assertNotEqual(self.active_service.title, 'Hacked Title')

    def test_service_owner_can_delete(self):
        """Service owner can delete their own service."""
        self.client.login(username='servicecreator', password='Password123!')
        res = self.client.post(reverse('services:service_delete', kwargs={'pk': self.active_service.pk}))
        self.assertEqual(res.status_code, 302)
        self.assertFalse(Service.objects.filter(pk=self.active_service.pk).exists())

    def test_unauthorized_user_cannot_delete(self):
        """Another user cannot delete a service they do not own (403 Forbidden)."""
        self.client.login(username='otherstudent', password='Password123!')
        res = self.client.post(reverse('services:service_delete', kwargs={'pk': self.active_service.pk}))
        self.assertEqual(res.status_code, 403)
        self.assertTrue(Service.objects.filter(pk=self.active_service.pk).exists())

    def test_toggle_active_status(self):
        """Owner can toggle service availability via POST."""
        self.client.login(username='servicecreator', password='Password123!')
        # Deactivate active service
        res = self.client.post(reverse('services:service_toggle_active', kwargs={'pk': self.active_service.pk}))
        self.assertEqual(res.status_code, 302)
        self.active_service.refresh_from_db()
        self.assertFalse(self.active_service.is_active)

        # Reactivate service
        res = self.client.post(reverse('services:service_toggle_active', kwargs={'pk': self.active_service.pk}))
        self.assertEqual(res.status_code, 302)
        self.active_service.refresh_from_db()
        self.assertTrue(self.active_service.is_active)

    def test_unauthorized_user_cannot_toggle_active_status(self):
        """Non-owner cannot toggle active status of another user's service."""
        self.client.login(username='otherstudent', password='Password123!')
        res = self.client.post(reverse('services:service_toggle_active', kwargs={'pk': self.active_service.pk}))
        self.assertEqual(res.status_code, 403)

    def test_search_and_category_filtering(self):
        """Verify search query and category filtering on service_list."""
        # Keyword search matching title/skills
        res = self.client.get(reverse('services:service_list') + '?q=Poster')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Professional Event Poster Design')

        # Keyword search matching nothing
        res_none = self.client.get(reverse('services:service_list') + '?q=NonExistentKeywordXYZ')
        self.assertEqual(res_none.status_code, 200)
        self.assertContains(res_none, 'No Services Found')

        # Category filter matching Graphic Design
        res_cat = self.client.get(reverse('services:service_list') + f'?category={Service.Category.GRAPHIC_DESIGN}')
        self.assertEqual(res_cat.status_code, 200)
        self.assertContains(res_cat, 'Professional Event Poster Design')

        # Category filter matching Tutoring (empty)
        res_empty_cat = self.client.get(reverse('services:service_list') + f'?category={Service.Category.TUTORING}')
        self.assertEqual(res_empty_cat.status_code, 200)
        self.assertContains(res_empty_cat, 'No Services Found')

    def test_mine_filter_for_authenticated_user(self):
        """Querying ?mine=1 shows only services belonging to the logged in user."""
        self.client.login(username='servicecreator', password='Password123!')
        res = self.client.get(reverse('services:service_list') + '?mine=1')
        self.assertEqual(res.status_code, 200)
        # Both active and inactive of the creator appear under mine=1
        self.assertContains(res, 'Professional Event Poster Design')
        self.assertContains(res, 'ESP32 &amp; Arduino Hardware Prototyping')

        # Now login as other user who has no services
        self.client.login(username='otherstudent', password='Password123!')
        res_other = self.client.get(reverse('services:service_list') + '?mine=1')
        self.assertEqual(res_other.status_code, 200)
        self.assertContains(res_other, 'No Services Found')
