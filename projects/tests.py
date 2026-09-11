from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from projects.models import Project

User = get_user_model()


class ProjectsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.client_user = User.objects.create_user(
            username='clientuser',
            email='client@ruet.ac.bd',
            password='Password123!',
            role=User.Role.CLIENT,
            company_name='RUET Dev Society'
        )
        self.other_client = User.objects.create_user(
            username='otherclient',
            email='other@ruet.ac.bd',
            password='Password123!',
            role=User.Role.CLIENT,
            company_name='Autonomous Labs'
        )
        self.student = User.objects.create_user(
            username='studentuser',
            email='student@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT
        )
        self.project = Project.objects.create(
            client=self.client_user,
            title='Autonomous Rover Firmware',
            description='Build ROS 2 nodes for navigation and obstacle avoidance.',
            category='Robotics',
            budget=250.00,
            status=Project.Status.OPEN
        )

    def test_project_list_view(self):
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Autonomous Rover Firmware')
        self.assertContains(res, 'Robotics')
        self.assertContains(res, '$250.00')

    def test_project_detail_view(self):
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_detail', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Autonomous Rover Firmware')
        self.assertContains(res, 'Apply for this Project')

    def test_client_can_create_project(self):
        self.client.login(username='clientuser', password='Password123!')
        res = self.client.post(reverse('projects:project_create'), {
            'title': 'Campus Mobile App UI',
            'description': 'Figma UI design for RUET event portal.',
            'category': 'UI/UX',
            'budget': '150.00',
            'status': 'open',
        })
        self.assertEqual(res.status_code, 302)
        self.assertTrue(Project.objects.filter(title='Campus Mobile App UI').exists())

    def test_student_cannot_create_project(self):
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_create'))
        self.assertEqual(res.status_code, 403)

    def test_project_ownership_protection_on_edit(self):
        self.client.login(username='otherclient', password='Password123!')
        res = self.client.get(reverse('projects:project_update', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 403)

    def test_project_owner_can_edit_and_delete(self):
        self.client.login(username='clientuser', password='Password123!')
        # Edit
        edit_res = self.client.post(reverse('projects:project_update', kwargs={'pk': self.project.pk}), {
            'title': 'Autonomous Rover Firmware v2',
            'description': 'Updated specs.',
            'category': 'Robotics',
            'budget': '300.00',
            'status': 'open',
        })
        self.assertEqual(edit_res.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, 'Autonomous Rover Firmware v2')
        self.assertEqual(float(self.project.budget), 300.00)

        # Delete
        del_res = self.client.post(reverse('projects:project_delete', kwargs={'pk': self.project.pk}))
        self.assertEqual(del_res.status_code, 302)
        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())
