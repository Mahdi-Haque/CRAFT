from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class AccountsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(
            username='teststudent',
            email='student@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT,
            skills='Python, Django, React'
        )
        self.client_user = User.objects.create_user(
            username='testclient',
            email='client@ruet.ac.bd',
            password='Password123!',
            role=User.Role.CLIENT,
            company_name='Robotics Club'
        )
        self.admin_user = User.objects.create_superuser(
            username='testadmin',
            email='admin@ruet.ac.bd',
            password='Password123!',
            role=User.Role.ADMIN
        )

    def test_login_page_renders(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign In')
        self.assertContains(response, 'CRAFT')
        self.assertContains(response, 'static/css/base.css')
        self.assertContains(response, 'static/css/components.css')

    def test_register_page_renders(self):
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Join CRAFT')
        self.assertContains(response, 'student-skills-group')
        self.assertContains(response, 'client-company-group')

    def test_student_registration_flow(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'newstudent',
            'email': 'newstudent@ruet.ac.bd',
            'role': 'student',
            'skills': 'C++, Embedded Systems',
            'company_name': '',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(username='newstudent')
        self.assertTrue(new_user.is_student)
        self.assertEqual(new_user.skills, 'C++, Embedded Systems')

    def test_client_registration_requires_company(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'newclient',
            'email': 'newclient@ruet.ac.bd',
            'role': 'client',
            'skills': '',
            'company_name': '',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'company_name', 'Company name is required for client accounts.')

    def test_dashboard_redirects_by_role(self):
        # Student -> student dashboard
        self.client.login(username='teststudent', password='Password123!')
        res = self.client.get(reverse('accounts:dashboard'))
        self.assertRedirects(res, reverse('applications:student_dashboard'))
        self.client.logout()

        # Client -> client dashboard
        self.client.login(username='testclient', password='Password123!')
        res = self.client.get(reverse('accounts:dashboard'))
        self.assertRedirects(res, reverse('projects:client_dashboard'))
        self.client.logout()

        # Admin -> admin dashboard
        self.client.login(username='testadmin', password='Password123!')
        res = self.client.get(reverse('accounts:dashboard'))
        self.assertRedirects(res, reverse('applications:admin_dashboard'))

    def test_profile_view_and_update(self):
        self.client.login(username='teststudent', password='Password123!')
        res = self.client.get(reverse('accounts:profile'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'My Profile')
        self.assertContains(res, 'teststudent')

        # Update profile
        update_res = self.client.post(reverse('accounts:profile'), {
            'first_name': 'A.Q.M.',
            'last_name': 'Mahdi',
            'email': 'student@ruet.ac.bd',
            'bio': 'CSE student at RUET interested in AI and Full-Stack.',
            'skills': 'Python, Django, PyTorch',
            'company_name': '',
        })
        self.assertEqual(update_res.status_code, 302)
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, 'A.Q.M.')
        self.assertEqual(self.student.skills, 'Python, Django, PyTorch')

    def test_home_page_guest_and_authenticated(self):
        # Guest sees landing page
        guest_res = self.client.get(reverse('home'))
        self.assertEqual(guest_res.status_code, 200)
        self.assertContains(guest_res, 'Turn your campus skills into')
        self.assertContains(guest_res, 'Exclusively for RUET Students')

        # Authenticated user is redirected to dashboard router
        self.client.login(username='teststudent', password='Password123!')
        auth_res = self.client.get(reverse('home'))
        self.assertEqual(auth_res.status_code, 302)
        self.assertEqual(auth_res['Location'], reverse('accounts:dashboard'))

