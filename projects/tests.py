from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from projects.models import Project, ProjectTeam, ProjectMembership
from projects.forms import ProjectForm
from applications.models import Application

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

    def test_default_sorting_is_newest_first(self):
        p2 = Project.objects.create(
            client=self.client_user,
            title='Second Project',
            description='Second project description',
            category='Robotics',
            budget=500.00,
            status=Project.Status.OPEN
        )
        p3 = Project.objects.create(
            client=self.client_user,
            title='Third Project',
            description='Third project description',
            category='Robotics',
            budget=100.00,
            status=Project.Status.OPEN
        )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['selected_sort'], 'newest')
        projects = list(res.context['projects'])
        self.assertEqual(projects[0], p3)
        self.assertEqual(projects[1], p2)
        self.assertEqual(projects[2], self.project)

    def test_sort_newest_explicit(self):
        p2 = Project.objects.create(
            client=self.client_user,
            title='Second Project',
            description='Second project description',
            category='Robotics',
            budget=500.00,
            status=Project.Status.OPEN
        )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'), {'sort': 'newest'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['selected_sort'], 'newest')
        projects = list(res.context['projects'])
        self.assertEqual(projects[0], p2)
        self.assertEqual(projects[1], self.project)

    def test_sort_oldest_first(self):
        p2 = Project.objects.create(
            client=self.client_user,
            title='Second Project',
            description='Second project description',
            category='Robotics',
            budget=500.00,
            status=Project.Status.OPEN
        )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'), {'sort': 'oldest'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['selected_sort'], 'oldest')
        projects = list(res.context['projects'])
        self.assertEqual(projects[0], self.project)
        self.assertEqual(projects[1], p2)

    def test_sort_budget_high_to_low(self):
        p_low = Project.objects.create(
            client=self.client_user,
            title='Low Budget Project',
            description='Low budget project',
            category='Robotics',
            budget=50.00,
            status=Project.Status.OPEN
        )
        p_high = Project.objects.create(
            client=self.client_user,
            title='High Budget Project',
            description='High budget project',
            category='Robotics',
            budget=1000.00,
            status=Project.Status.OPEN
        )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'), {'sort': 'budget_high'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['selected_sort'], 'budget_high')
        projects = list(res.context['projects'])
        self.assertEqual(projects[0], p_high)
        self.assertEqual(projects[1], self.project)
        self.assertEqual(projects[2], p_low)

    def test_sort_budget_low_to_high(self):
        p_low = Project.objects.create(
            client=self.client_user,
            title='Low Budget Project',
            description='Low budget project',
            category='Robotics',
            budget=50.00,
            status=Project.Status.OPEN
        )
        p_high = Project.objects.create(
            client=self.client_user,
            title='High Budget Project',
            description='High budget project',
            category='Robotics',
            budget=1000.00,
            status=Project.Status.OPEN
        )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'), {'sort': 'budget_low'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['selected_sort'], 'budget_low')
        projects = list(res.context['projects'])
        self.assertEqual(projects[0], p_low)
        self.assertEqual(projects[1], self.project)
        self.assertEqual(projects[2], p_high)

    def test_sort_deadline_nearest_first_with_nulls_last(self):
        today = date.today()
        p_soon = Project.objects.create(
            client=self.client_user,
            title='Deadline Soon Project',
            description='Finishes soon',
            category='Robotics',
            budget=100.00,
            deadline=today + timedelta(days=2),
            status=Project.Status.OPEN
        )
        p_later = Project.objects.create(
            client=self.client_user,
            title='Deadline Later Project',
            description='Finishes later',
            category='Robotics',
            budget=100.00,
            deadline=today + timedelta(days=10),
            status=Project.Status.OPEN
        )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'), {'sort': 'deadline'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['selected_sort'], 'deadline')
        projects = list(res.context['projects'])
        self.assertEqual(projects[0], p_soon)
        self.assertEqual(projects[1], p_later)
        self.assertEqual(projects[2], self.project)

    def test_sort_with_category_filter(self):
        Project.objects.create(
            client=self.client_user,
            title='High Budget Robotics',
            description='Description',
            category='Robotics',
            budget=900.00,
            status=Project.Status.OPEN
        )
        Project.objects.create(
            client=self.client_user,
            title='High Budget Web',
            description='Description',
            category='Web Development',
            budget=1000.00,
            status=Project.Status.OPEN
        )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'), {'category': 'Robotics', 'sort': 'budget_high'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['selected_category'], 'Robotics')
        self.assertEqual(res.context['selected_sort'], 'budget_high')
        projects = list(res.context['projects'])
        self.assertEqual(len(projects), 2)
        self.assertEqual(projects[0].title, 'High Budget Robotics')
        self.assertEqual(projects[1].title, 'Autonomous Rover Firmware')

    def test_sort_with_keyword_search(self):
        Project.objects.create(
            client=self.client_user,
            title='Autonomous Drone Navigation',
            description='Description',
            category='Robotics',
            budget=800.00,
            status=Project.Status.OPEN
        )
        Project.objects.create(
            client=self.client_user,
            title='Autonomous Submarine',
            description='Description',
            category='Robotics',
            budget=100.00,
            status=Project.Status.OPEN
        )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'), {'q': 'Autonomous', 'sort': 'budget_low'})
        self.assertEqual(res.status_code, 200)
        projects = list(res.context['projects'])
        self.assertEqual(len(projects), 3)
        self.assertEqual(projects[0].title, 'Autonomous Submarine')
        self.assertEqual(projects[1].title, 'Autonomous Rover Firmware')
        self.assertEqual(projects[2].title, 'Autonomous Drone Navigation')

    def test_sort_preserved_in_pagination_links(self):
        for i in range(7):
            Project.objects.create(
                client=self.client_user,
                title=f'Project {i}',
                description='Description',
                category='Robotics',
                budget=100.00 + i,
                status=Project.Status.OPEN
            )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'), {'sort': 'budget_high', 'page': 1})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'sort=budget_high')
        self.assertContains(res, 'page=2')

    def test_filtering_sorting_and_pagination_work_together(self):
        for i in range(7):
            Project.objects.create(
                client=self.client_user,
                title=f'Robotics Project {i}',
                description='Description',
                category='Robotics',
                budget=100.00 + i,
                status=Project.Status.OPEN
            )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'), {'category': 'Robotics', 'sort': 'budget_high', 'page': 1})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'category=Robotics')
        self.assertContains(res, 'sort=budget_high')
        self.assertContains(res, 'page=2')

    def test_invalid_sort_parameter_falls_back_to_newest(self):
        p2 = Project.objects.create(
            client=self.client_user,
            title='Second Project',
            description='Description',
            category='Robotics',
            budget=500.00,
            status=Project.Status.OPEN
        )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'), {'sort': 'invalid_xyz'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['selected_sort'], 'newest')
        projects = list(res.context['projects'])
        self.assertEqual(projects[0], p2)
        self.assertEqual(projects[1], self.project)

    def test_sort_dropdown_rendered_with_selected_option(self):
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_list'), {'sort': 'budget_high'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, '<select name="sort"')
        self.assertContains(res, 'value="newest"')
        self.assertContains(res, 'value="oldest"')
        self.assertContains(res, 'value="budget_high" selected')
        self.assertContains(res, 'value="budget_low"')
        self.assertContains(res, 'value="deadline"')


class ProjectLifecycleTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(
            username='clientowner',
            email='clientowner@ruet.ac.bd',
            password='Password123!',
            role=User.Role.CLIENT,
            company_name='RUET Robotics Club'
        )
        self.other_client = User.objects.create_user(
            username='otherclient',
            email='otherclient@ruet.ac.bd',
            password='Password123!',
            role=User.Role.CLIENT,
            company_name='Autonomous Systems'
        )
        self.student = User.objects.create_user(
            username='studentdev',
            email='studentdev@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT
        )
        self.project = Project.objects.create(
            client=self.owner,
            title='Autonomous Delivery Drone',
            description='Firmware and path planning in ROS2.',
            category='Robotics',
            budget=400.00,
            status=Project.Status.OPEN
        )

    def test_owner_can_start_open_project(self):
        self.client.login(username='clientowner', password='Password123!')
        res = self.client.post(reverse('projects:project_start', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.IN_PROGRESS)

    def test_non_owner_cannot_start_or_change_lifecycle(self):
        self.client.login(username='otherclient', password='Password123!')
        res = self.client.post(reverse('projects:project_start', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 403)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.OPEN)

    def test_unauthenticated_cannot_change_lifecycle(self):
        res = self.client.post(reverse('projects:project_start', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login/', res.url)

    def test_owner_can_mark_in_progress_project_completed(self):
        self.project.status = Project.Status.IN_PROGRESS
        self.project.save()

        self.client.login(username='clientowner', password='Password123!')
        res = self.client.post(reverse('projects:project_complete', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.COMPLETED)

    def test_non_owner_cannot_complete_project(self):
        self.project.status = Project.Status.IN_PROGRESS
        self.project.save()

        self.client.login(username='studentdev', password='Password123!')
        res = self.client.post(reverse('projects:project_complete', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 403)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.IN_PROGRESS)

    def test_owner_can_cancel_open_or_in_progress_project(self):
        self.client.login(username='clientowner', password='Password123!')
        # Cancel open project
        res = self.client.post(reverse('projects:project_cancel', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.CLOSED)

        # Cancel in-progress project using close alias
        proj2 = Project.objects.create(
            client=self.owner,
            title='In Progress Project',
            description='Test description',
            budget=200.00,
            status=Project.Status.IN_PROGRESS
        )
        res2 = self.client.post(reverse('projects:project_close', kwargs={'pk': proj2.pk}))
        self.assertEqual(res2.status_code, 302)
        proj2.refresh_from_db()
        self.assertEqual(proj2.status, Project.Status.CLOSED)

    def test_invalid_lifecycle_transitions_rejected(self):
        self.client.login(username='clientowner', password='Password123!')
        
        # Cannot complete an OPEN project directly
        res = self.client.post(reverse('projects:project_complete', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.OPEN)

        # Cannot start a COMPLETED project
        self.project.status = Project.Status.COMPLETED
        self.project.save()
        res_start = self.client.post(reverse('projects:project_start', kwargs={'pk': self.project.pk}))
        self.assertEqual(res_start.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.COMPLETED)

        # Cannot cancel an already COMPLETED project
        res_cancel = self.client.post(reverse('projects:project_cancel', kwargs={'pk': self.project.pk}))
        self.assertEqual(res_cancel.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.COMPLETED)

    def test_completed_project_cannot_be_reopened(self):
        self.project.status = Project.Status.COMPLETED
        self.project.save()

        self.client.login(username='clientowner', password='Password123!')
        # Via start action
        res = self.client.post(reverse('projects:project_start', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.COMPLETED)

        # Via edit form
        res_edit = self.client.post(reverse('projects:project_update', kwargs={'pk': self.project.pk}), {
            'title': self.project.title,
            'description': self.project.description,
            'budget': self.project.budget,
            'status': 'open',
        })
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.COMPLETED)

    def test_closed_project_cannot_be_reopened(self):
        self.project.status = Project.Status.CLOSED
        self.project.save()

        self.client.login(username='clientowner', password='Password123!')
        # Via start action
        res = self.client.post(reverse('projects:project_start', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.CLOSED)

        # Via complete action
        res_complete = self.client.post(reverse('projects:project_complete', kwargs={'pk': self.project.pk}))
        self.assertEqual(res_complete.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.CLOSED)

        # Via edit form
        res_edit = self.client.post(reverse('projects:project_update', kwargs={'pk': self.project.pk}), {
            'title': self.project.title,
            'description': self.project.description,
            'budget': self.project.budget,
            'status': 'open',
        })
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.CLOSED)

    def test_lifecycle_get_requests_are_denied(self):
        self.client.login(username='clientowner', password='Password123!')
        res1 = self.client.get(reverse('projects:project_start', kwargs={'pk': self.project.pk}))
        self.assertEqual(res1.status_code, 403)
        res2 = self.client.get(reverse('projects:project_complete', kwargs={'pk': self.project.pk}))
        self.assertEqual(res2.status_code, 403)
        res3 = self.client.get(reverse('projects:project_cancel', kwargs={'pk': self.project.pk}))
        self.assertEqual(res3.status_code, 403)

    def test_project_detail_reflects_lifecycle_controls_and_badges(self):
        # Open project
        self.client.login(username='clientowner', password='Password123!')
        res_open = self.client.get(reverse('projects:project_detail', kwargs={'pk': self.project.pk}))
        self.assertContains(res_open, 'Open for Applications')
        self.assertContains(res_open, 'Start Project')
        self.assertContains(res_open, 'Close Project')

        # In-Progress project
        self.project.status = Project.Status.IN_PROGRESS
        self.project.save()
        res_prog = self.client.get(reverse('projects:project_detail', kwargs={'pk': self.project.pk}))
        self.assertContains(res_prog, 'In Progress')
        self.assertContains(res_prog, 'Mark Completed')
        self.assertContains(res_prog, 'Cancel Project')

        # Completed project
        self.project.status = Project.Status.COMPLETED
        self.project.save()
        res_done = self.client.get(reverse('projects:project_detail', kwargs={'pk': self.project.pk}))
        self.assertContains(res_done, 'Completed')
        self.assertNotContains(res_done, 'Start Project')
        self.assertNotContains(res_done, 'Mark Completed')
        self.assertNotContains(res_done, 'Cancel Project')


class ProjectWorkspaceTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(
            username='labclient',
            email='labclient@ruet.ac.bd',
            password='Password123!',
            role=User.Role.CLIENT,
            company_name='RUET VLSI Research'
        )
        self.other_client = User.objects.create_user(
            username='otherclient',
            email='otherclient@ruet.ac.bd',
            password='Password123!',
            role=User.Role.CLIENT,
            company_name='Autonomous Labs'
        )
        self.accepted_student = User.objects.create_user(
            username='acceptedstudent',
            email='accepted@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT,
            skills='Verilog, FPGA, MATLAB'
        )
        self.second_accepted_student = User.objects.create_user(
            username='studenttwo',
            email='studenttwo@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT,
            skills='Python, PyTorch'
        )
        self.pending_student = User.objects.create_user(
            username='pendingstudent',
            email='pending@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT
        )
        self.rejected_student = User.objects.create_user(
            username='rejectedstudent',
            email='rejected@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT
        )
        self.unrelated_student = User.objects.create_user(
            username='unrelatedstudent',
            email='unrelated@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT
        )
        self.project = Project.objects.create(
            client=self.owner,
            title='RISC-V Core Implementation',
            description='Design a 5-stage pipelined RV32I processor core in Verilog.',
            category='Hardware',
            budget=500.00,
            status=Project.Status.IN_PROGRESS
        )
        self.team = self.project.get_team()
        self.team.add_member(self.accepted_student)

        # Applications
        Application.objects.create(
            project=self.project,
            student=self.accepted_student,
            cover_letter='Strong Verilog candidate',
            status=Application.Status.ACCEPTED
        )
        Application.objects.create(
            project=self.project,
            student=self.pending_student,
            cover_letter='Pending candidate',
            status=Application.Status.PENDING
        )
        Application.objects.create(
            project=self.project,
            student=self.rejected_student,
            cover_letter='Declined candidate',
            status=Application.Status.REJECTED
        )

    def test_project_owner_can_access_workspace(self):
        self.client.login(username='labclient', password='Password123!')
        res = self.client.get(reverse('projects:project_workspace', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Team Workspace')
        self.assertContains(res, 'RISC-V Core Implementation')
        self.assertContains(res, 'labclient')
        self.assertContains(res, 'acceptedstudent')

    def test_accepted_student_can_access_workspace(self):
        self.client.login(username='acceptedstudent', password='Password123!')
        res = self.client.get(reverse('projects:project_workspace', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Team Workspace')
        self.assertContains(res, 'acceptedstudent')
        self.assertContains(res, 'Verilog')

    def test_unauthenticated_user_cannot_access_workspace(self):
        res = self.client.get(reverse('projects:project_workspace', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login/', res.url)

    def test_unrelated_authenticated_user_cannot_access_workspace(self):
        self.client.login(username='unrelatedstudent', password='Password123!')
        res = self.client.get(reverse('projects:project_workspace', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 403)

    def test_pending_applicant_cannot_access_workspace(self):
        self.client.login(username='pendingstudent', password='Password123!')
        res = self.client.get(reverse('projects:project_workspace', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 403)

    def test_rejected_applicant_cannot_access_workspace(self):
        self.client.login(username='rejectedstudent', password='Password123!')
        res = self.client.get(reverse('projects:project_workspace', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 403)

    def test_unrelated_client_cannot_access_workspace(self):
        self.client.login(username='otherclient', password='Password123!')
        res = self.client.get(reverse('projects:project_workspace', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 403)

    def test_accepted_student_cannot_perform_owner_only_lifecycle_actions(self):
        self.client.login(username='acceptedstudent', password='Password123!')
        res_complete = self.client.post(reverse('projects:project_complete', kwargs={'pk': self.project.pk}))
        self.assertEqual(res_complete.status_code, 403)

        res_cancel = self.client.post(reverse('projects:project_cancel', kwargs={'pk': self.project.pk}))
        self.assertEqual(res_cancel.status_code, 403)

    def test_multiple_accepted_students_can_belong_to_same_project_and_display(self):
        self.team.add_member(self.second_accepted_student)
        self.client.login(username='labclient', password='Password123!')
        res = self.client.get(reverse('projects:project_workspace', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'acceptedstudent')
        self.assertContains(res, 'studenttwo')
        self.assertEqual(self.team.members.count(), 2)

    def test_pending_and_rejected_applicants_not_displayed_as_active_team_members(self):
        self.client.login(username='labclient', password='Password123!')
        res = self.client.get(reverse('projects:project_workspace', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 200)
        # Pending and rejected applicants are not in team_members
        self.assertNotIn(self.pending_student, res.context['team_members'])
        self.assertNotIn(self.rejected_student, res.context['team_members'])
        self.assertIn(self.accepted_student, res.context['team_members'])

    def test_workspace_accessible_in_in_progress_and_completed_states(self):
        self.client.login(username='acceptedstudent', password='Password123!')
        # IN_PROGRESS
        res_in_prog = self.client.get(reverse('projects:project_workspace', kwargs={'pk': self.project.pk}))
        self.assertEqual(res_in_prog.status_code, 200)

        # COMPLETED
        self.project.status = Project.Status.COMPLETED
        self.project.save()
        res_comp = self.client.get(reverse('projects:project_workspace', kwargs={'pk': self.project.pk}))
        self.assertEqual(res_comp.status_code, 200)

    def test_project_detail_displays_workspace_link_for_owner_and_accepted_student(self):
        # Owner sees link
        self.client.login(username='labclient', password='Password123!')
        res_owner = self.client.get(reverse('projects:project_detail', kwargs={'pk': self.project.pk}))
        self.assertContains(res_owner, 'Team Workspace')

        # Accepted student sees link
        self.client.login(username='acceptedstudent', password='Password123!')
        res_accepted = self.client.get(reverse('projects:project_detail', kwargs={'pk': self.project.pk}))
        self.assertContains(res_accepted, 'Enter Team Workspace')

        # Unrelated student does NOT see link
        self.client.login(username='unrelatedstudent', password='Password123!')
        res_unrelated = self.client.get(reverse('projects:project_detail', kwargs={'pk': self.project.pk}))
        self.assertNotContains(res_unrelated, 'Enter Team Workspace')


class ClientDashboardIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.client_user = User.objects.create_user(
            username='mainclient',
            email='mainclient@ruet.ac.bd',
            password='Password123!',
            role=User.Role.CLIENT,
            company_name='Robotics & AI Society'
        )
        self.other_client = User.objects.create_user(
            username='otherclient',
            email='otherclient@ruet.ac.bd',
            password='Password123!',
            role=User.Role.CLIENT,
            company_name='Circuit Lab'
        )
        self.student1 = User.objects.create_user(
            username='studentone',
            email='s1@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT
        )
        self.student2 = User.objects.create_user(
            username='studenttwo',
            email='s2@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT
        )

        self.open_proj = Project.objects.create(
            client=self.client_user,
            title='Open Vision Project',
            description='OpenCV object tracker.',
            category='Robotics',
            budget=300.00,
            status=Project.Status.OPEN
        )
        self.in_progress_proj = Project.objects.create(
            client=self.client_user,
            title='In Progress Rover Control',
            description='Motor drivers and telemetry.',
            category='Robotics',
            budget=450.00,
            status=Project.Status.IN_PROGRESS
        )
        self.completed_proj = Project.objects.create(
            client=self.client_user,
            title='Completed Web Dashboard',
            description='Django monitoring portal.',
            category='Web',
            budget=200.00,
            status=Project.Status.COMPLETED
        )
        self.closed_proj = Project.objects.create(
            client=self.client_user,
            title='Closed Design Challenge',
            description='Old UI mockups.',
            category='UI/UX',
            budget=100.00,
            status=Project.Status.CLOSED
        )

        self.other_proj = Project.objects.create(
            client=self.other_client,
            title='Confidential Hardware Design',
            description='Secret schematic.',
            category='Embedded',
            budget=500.00,
            status=Project.Status.OPEN
        )

    def test_client_dashboard_authenticated_client_access(self):
        self.client.login(username='mainclient', password='Password123!')
        res = self.client.get(reverse('projects:client_dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'projects/client_dashboard.html')

    def test_client_dashboard_non_client_forbidden(self):
        self.client.login(username='studentone', password='Password123!')
        res = self.client.get(reverse('projects:client_dashboard'))
        self.assertEqual(res.status_code, 403)

    def test_client_dashboard_unauthenticated_redirect(self):
        res = self.client.get(reverse('projects:client_dashboard'))
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse('accounts:login'), res.url)

    def test_client_dashboard_lifecycle_metrics(self):
        Application.objects.create(
            project=self.open_proj,
            student=self.student1,
            status=Application.Status.PENDING,
            cover_letter='Applying to open project'
        )
        Application.objects.create(
            project=self.in_progress_proj,
            student=self.student2,
            status=Application.Status.ACCEPTED,
            cover_letter='Applying to in-progress project'
        )

        self.client.login(username='mainclient', password='Password123!')
        res = self.client.get(reverse('projects:client_dashboard'))
        self.assertEqual(res.status_code, 200)

        self.assertEqual(res.context['open_count'], 1)
        self.assertEqual(res.context['in_progress_count'], 1)
        self.assertEqual(res.context['completed_count'], 1)
        self.assertEqual(res.context['closed_count'], 1)
        self.assertEqual(res.context['total_applicants'], 2)
        self.assertEqual(len(res.context['projects']), 4)

        self.assertContains(res, 'Open Projects')
        self.assertContains(res, 'In Progress')
        self.assertContains(res, 'Completed')
        self.assertContains(res, 'Closed')
        self.assertContains(res, 'Total Applicants')

    def test_client_dashboard_shows_only_own_projects(self):
        self.client.login(username='mainclient', password='Password123!')
        res = self.client.get(reverse('projects:client_dashboard'))
        self.assertEqual(res.status_code, 200)

        project_ids = [p.id for p in res.context['projects']]
        self.assertIn(self.open_proj.id, project_ids)
        self.assertNotIn(self.other_proj.id, project_ids)
        self.assertContains(res, 'Open Vision Project')
        self.assertNotContains(res, 'Confidential Hardware Design')

    def test_client_dashboard_applicant_review_link(self):
        Application.objects.create(
            project=self.open_proj,
            student=self.student1,
            status=Application.Status.PENDING,
            cover_letter='Proposal'
        )
        self.client.login(username='mainclient', password='Password123!')
        res = self.client.get(reverse('projects:client_dashboard'))
        self.assertEqual(res.status_code, 200)

        applicants_url = reverse('applications:applicants_list', kwargs={'pk': self.open_proj.pk})
        self.assertContains(res, applicants_url)
        self.assertContains(res, '1 applicant')

    def test_client_dashboard_workspace_link_for_active_projects(self):
        self.client.login(username='mainclient', password='Password123!')
        res = self.client.get(reverse('projects:client_dashboard'))
        self.assertEqual(res.status_code, 200)

        in_prog_workspace_url = reverse('projects:project_workspace', kwargs={'pk': self.in_progress_proj.pk})
        completed_workspace_url = reverse('projects:project_workspace', kwargs={'pk': self.completed_proj.pk})
        open_workspace_url = reverse('projects:project_workspace', kwargs={'pk': self.open_proj.pk})

        self.assertContains(res, in_prog_workspace_url)
        self.assertContains(res, completed_workspace_url)
        self.assertNotContains(res, open_workspace_url)



