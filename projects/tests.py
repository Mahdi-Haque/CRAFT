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

    def test_category_filter_returns_matching_projects(self):
        Project.objects.create(
            client=self.client_user,
            title='Campus Society Web Portal',
            description='Django backend and React frontend for university club.',
            category='Web Development',
            budget=200.00,
            status=Project.Status.OPEN
        )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'), {'category': 'Robotics'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Autonomous Rover Firmware')
        self.assertEqual(res.context['selected_category'], 'Robotics')
        self.assertIn('Robotics', res.context['categories'])
        self.assertIn('Web Development', res.context['categories'])

    def test_category_filter_excludes_projects_from_other_categories(self):
        Project.objects.create(
            client=self.client_user,
            title='Campus Society Web Portal',
            description='Django backend and React frontend for university club.',
            category='Web Development',
            budget=200.00,
            status=Project.Status.OPEN
        )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'), {'category': 'Robotics'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Autonomous Rover Firmware')
        self.assertNotContains(res, 'Campus Society Web Portal')

    def test_keyword_search_still_works(self):
        Project.objects.create(
            client=self.client_user,
            title='Campus Society Web Portal',
            description='Django backend and React frontend for university club.',
            category='Web Development',
            budget=200.00,
            status=Project.Status.OPEN
        )
        self.client.login(username='studentuser', password='Password123!')

        # Search matching Rover
        res_rover = self.client.get(reverse('projects:project_list'), {'q': 'Rover'})
        self.assertEqual(res_rover.status_code, 200)
        self.assertContains(res_rover, 'Autonomous Rover Firmware')
        self.assertNotContains(res_rover, 'Campus Society Web Portal')

        # Search matching Web
        res_web = self.client.get(reverse('projects:project_list'), {'q': 'Web'})
        self.assertEqual(res_web.status_code, 200)
        self.assertContains(res_web, 'Campus Society Web Portal')
        self.assertNotContains(res_web, 'Autonomous Rover Firmware')

        # Search matching nothing
        res_none = self.client.get(reverse('projects:project_list'), {'q': 'NonExistentXYZ'})
        self.assertEqual(res_none.status_code, 200)
        self.assertContains(res_none, 'No Open Projects Found')

    def test_keyword_search_and_category_filter_work_together(self):
        # Project 1: Rover in Robotics (self.project)
        # Project 2: Rover in CAD
        Project.objects.create(
            client=self.client_user,
            title='Rover Chassis CAD Design',
            description='SolidWorks CAD model for rover chassis.',
            category='CAD Modeling',
            budget=150.00,
            status=Project.Status.OPEN
        )
        # Project 3: Drone in Robotics
        Project.objects.create(
            client=self.client_user,
            title='Drone Flight Stabilization',
            description='Quadcopter stabilization code.',
            category='Robotics',
            budget=180.00,
            status=Project.Status.OPEN
        )
        self.client.login(username='studentuser', password='Password123!')

        # Query for 'Rover' in category 'Robotics'
        res = self.client.get(reverse('projects:project_list'), {'q': 'Rover', 'category': 'Robotics'})
        self.assertEqual(res.status_code, 200)
        # Should include Project 1 (Rover + Robotics)
        self.assertContains(res, 'Autonomous Rover Firmware')
        # Should NOT include Project 2 (Rover + CAD Modeling)
        self.assertNotContains(res, 'Rover Chassis CAD Design')
        # Should NOT include Project 3 (Drone + Robotics)
        self.assertNotContains(res, 'Drone Flight Stabilization')
        # Check UI preserves both query and selected_category
        self.assertEqual(res.context['query'], 'Rover')
        self.assertEqual(res.context['selected_category'], 'Robotics')

    def test_empty_or_invalid_category_does_not_break_page(self):
        self.client.login(username='studentuser', password='Password123!')

        # Empty category should return all open projects gracefully
        res_empty = self.client.get(reverse('projects:project_list'), {'category': ''})
        self.assertEqual(res_empty.status_code, 200)
        self.assertContains(res_empty, 'Autonomous Rover Firmware')
        self.assertEqual(res_empty.context['selected_category'], '')

        # Whitespace-only category should return all open projects gracefully
        res_whitespace = self.client.get(reverse('projects:project_list'), {'category': '   '})
        self.assertEqual(res_whitespace.status_code, 200)
        self.assertContains(res_whitespace, 'Autonomous Rover Firmware')

        # Invalid/non-existent category should return empty list gracefully without error
        res_invalid = self.client.get(reverse('projects:project_list'), {'category': 'NonExistentCategoryXYZ'})
        self.assertEqual(res_invalid.status_code, 200)
        self.assertEqual(len(res_invalid.context['projects']), 0)
        self.assertContains(res_invalid, 'No Open Projects Found')
        self.assertContains(res_invalid, 'NonExistentCategoryXYZ')

    def test_project_list_is_paginated(self):
        # Create 7 additional projects (total 8 with self.project)
        for i in range(7):
            Project.objects.create(
                client=self.client_user,
                title=f'Test Pagination Project {i}',
                description=f'Description for project {i}',
                category='Robotics',
                budget=100.00 + i,
                status=Project.Status.OPEN
            )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'))
        self.assertEqual(res.status_code, 200)
        page_obj = res.context['page_obj']
        self.assertEqual(page_obj.paginator.num_pages, 2)
        self.assertEqual(page_obj.paginator.count, 8)

    def test_first_page_contains_expected_number_of_projects(self):
        for i in range(7):
            Project.objects.create(
                client=self.client_user,
                title=f'Test Pagination Project {i}',
                description=f'Description for project {i}',
                category='Robotics',
                budget=100.00 + i,
                status=Project.Status.OPEN
            )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context['projects']), 6)
        self.assertEqual(res.context['page_obj'].number, 1)

    def test_second_page_contains_remaining_projects(self):
        for i in range(7):
            Project.objects.create(
                client=self.client_user,
                title=f'Test Pagination Project {i}',
                description=f'Description for project {i}',
                category='Robotics',
                budget=100.00 + i,
                status=Project.Status.OPEN
            )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'), {'page': 2})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context['projects']), 2)
        self.assertEqual(res.context['page_obj'].number, 2)

    def test_pagination_preserves_keyword_search(self):
        for i in range(7):
            Project.objects.create(
                client=self.client_user,
                title=f'Robotics Subsystem {i}',
                description='Robotics build',
                category='Robotics',
                budget=100.00,
                status=Project.Status.OPEN
            )
        Project.objects.create(
            client=self.client_user,
            title='Web Portal App',
            description='Web build',
            category='Web',
            budget=100.00,
            status=Project.Status.OPEN
        )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'), {'q': 'Robotics', 'page': 2})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['query'], 'Robotics')
        self.assertContains(res, 'q=Robotics')
        self.assertContains(res, 'page=1')

    def test_pagination_preserves_category_filtering(self):
        for i in range(7):
            Project.objects.create(
                client=self.client_user,
                title=f'Robotics Project {i}',
                description='Robotics build',
                category='Robotics',
                budget=100.00,
                status=Project.Status.OPEN
            )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'), {'category': 'Robotics', 'page': 2})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['selected_category'], 'Robotics')
        self.assertContains(res, 'category=Robotics')
        self.assertContains(res, 'page=1')

    def test_invalid_page_parameters_handled_gracefully(self):
        for i in range(7):
            Project.objects.create(
                client=self.client_user,
                title=f'Test Project {i}',
                description='Description',
                category='Robotics',
                budget=100.00,
                status=Project.Status.OPEN
            )
        self.client.login(username='studentuser', password='Password123!')
        res_invalid = self.client.get(reverse('projects:project_list'), {'page': 'not_an_int'})
        self.assertEqual(res_invalid.status_code, 200)
        self.assertEqual(res_invalid.context['page_obj'].number, 1)

        res_empty = self.client.get(reverse('projects:project_list'), {'page': ''})
        self.assertEqual(res_empty.status_code, 200)
        self.assertEqual(res_empty.context['page_obj'].number, 1)

    def test_out_of_range_page_parameters_handled_gracefully(self):
        for i in range(7):
            Project.objects.create(
                client=self.client_user,
                title=f'Test Project {i}',
                description='Description',
                category='Robotics',
                budget=100.00,
                status=Project.Status.OPEN
            )
        self.client.login(username='studentuser', password='Password123!')
        res_overflow = self.client.get(reverse('projects:project_list'), {'page': 9999})
        self.assertEqual(res_overflow.status_code, 200)
        self.assertEqual(res_overflow.context['page_obj'].number, 2)

    def test_pagination_controls_appear_correctly(self):
        self.client.login(username='studentuser', password='Password123!')
        # Single page: controls should NOT appear
        res_single = self.client.get(reverse('projects:project_list'))
        self.assertNotContains(res_single, '<nav aria-label="Projects pagination">')

        # Create enough projects to trigger pagination
        for i in range(7):
            Project.objects.create(
                client=self.client_user,
                title=f'Pagination Control Project {i}',
                description='Description',
                category='Robotics',
                budget=100.00,
                status=Project.Status.OPEN
            )
        # Page 1: controls appear, Previous is disabled, Next is active
        res_p1 = self.client.get(reverse('projects:project_list'))
        self.assertContains(res_p1, '<nav aria-label="Projects pagination">')
        self.assertContains(res_p1, 'Previous')
        self.assertContains(res_p1, 'Next')
        self.assertContains(res_p1, 'active')

        # Page 2: controls appear, Next is disabled
        res_p2 = self.client.get(reverse('projects:project_list'), {'page': 2})
        self.assertContains(res_p2, '<nav aria-label="Projects pagination">')



