from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from projects.models import Project
from projects.forms import ProjectForm

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

    def test_project_can_be_created_with_skills_required(self):
        project_with_skills = Project.objects.create(
            client=self.client_user,
            title='Embedded Drone Firmware',
            description='Custom drone control loop implementation.',
            category='Robotics',
            skills_required='C++, RTOS, STM32, PID',
            budget=350.00,
            status=Project.Status.OPEN
        )
        self.assertEqual(project_with_skills.skills_required, 'C++, RTOS, STM32, PID')
        self.assertEqual(project_with_skills.skills_list, ['C++', 'RTOS', 'STM32', 'PID'])

    def test_project_can_exist_with_empty_skills_required(self):
        project_without_skills = Project.objects.create(
            client=self.client_user,
            title='General Research Assistant',
            description='Literature review for university lab.',
            category='Research',
            budget=100.00,
            status=Project.Status.OPEN
        )
        self.assertEqual(project_without_skills.skills_required, '')
        self.assertEqual(project_without_skills.skills_list, [])

    def test_project_form_exposes_skills_required(self):
        form = ProjectForm()
        self.assertIn('skills_required', form.fields)
        self.assertFalse(form.fields['skills_required'].required)

        # Form is valid with skills_required provided
        valid_data_with_skills = {
            'title': 'Computer Vision Pipeline',
            'description': 'Real-time object detection using YOLO and OpenCV.',
            'category': 'AI & Python',
            'skills_required': 'Python, PyTorch, OpenCV',
            'budget': '200.00',
            'status': 'open',
        }
        form_with_skills = ProjectForm(data=valid_data_with_skills)
        self.assertTrue(form_with_skills.is_valid())
        self.assertEqual(form_with_skills.cleaned_data['skills_required'], 'Python, PyTorch, OpenCV')

        # Form is also valid with skills_required omitted/blank
        valid_data_without_skills = {
            'title': 'Poster Printing Task',
            'description': 'Print banners for orientation week.',
            'category': 'Design',
            'skills_required': '',
            'budget': '50.00',
            'status': 'open',
        }
        form_without_skills = ProjectForm(data=valid_data_without_skills)
        self.assertTrue(form_without_skills.is_valid())

    def test_client_can_create_project_with_skills_via_view(self):
        self.client.login(username='clientuser', password='Password123!')
        res = self.client.post(reverse('projects:project_create'), {
            'title': 'Campus Mobile App UI',
            'description': 'Figma UI design for RUET event portal.',
            'category': 'UI/UX',
            'skills_required': 'Figma, Wireframing, Prototyping',
            'budget': '150.00',
            'status': 'open',
        })
        self.assertEqual(res.status_code, 302)
        created_project = Project.objects.filter(title='Campus Mobile App UI').first()
        self.assertIsNotNone(created_project)
        self.assertEqual(created_project.skills_required, 'Figma, Wireframing, Prototyping')
        self.assertEqual(created_project.skills_list, ['Figma', 'Wireframing', 'Prototyping'])

