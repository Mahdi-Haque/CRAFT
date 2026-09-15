from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from projects.models import Project, ProjectTeam, ProjectMembership
from applications.models import Application

User = get_user_model()


class ApplicationsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.client_user = User.objects.create_user(
            username='clientuser',
            email='client@ruet.ac.bd',
            password='Password123!',
            role=User.Role.CLIENT,
            company_name='Embedded Systems Lab'
        )
        self.student = User.objects.create_user(
            username='studentuser',
            email='student@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT,
            skills='C, RTOS, PCB Design'
        )
        self.other_student = User.objects.create_user(
            username='otherstudent',
            email='otherstud@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT
        )
        self.admin_user = User.objects.create_superuser(
            username='adminuser',
            email='admin@ruet.ac.bd',
            password='Password123!',
            role=User.Role.ADMIN
        )
        self.project = Project.objects.create(
            client=self.client_user,
            title='STM32 Drone Flight Controller',
            description='Design firmware for quadcopter stabilization.',
            budget=200.00,
            status=Project.Status.OPEN
        )

    def test_student_can_apply_to_open_project(self):
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.post(reverse('applications:project_apply', kwargs={'pk': self.project.pk}), {
            'cover_letter': 'I have completed CSE 3100 microcontrollers lab and built an inverted pendulum.'
        })
        self.assertEqual(res.status_code, 302)
        self.assertTrue(Application.objects.filter(project=self.project, student=self.student).exists())

    def test_cannot_apply_twice(self):
        Application.objects.create(
            project=self.project,
            student=self.student,
            cover_letter='First application'
        )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('applications:project_apply', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 302) # Redirects to project detail with info message

    def test_cannot_apply_to_closed_project(self):
        self.project.status = Project.Status.CLOSED
        self.project.save()

        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('applications:project_apply', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 302) # Redirects with error message

    def test_client_manage_applicants_and_status(self):
        app = Application.objects.create(
            project=self.project,
            student=self.student,
            cover_letter='Strong candidate proposal'
        )
        self.client.login(username='clientuser', password='Password123!')
        
        # View applicants list
        list_res = self.client.get(reverse('applications:applicants_list', kwargs={'pk': self.project.pk}))
        self.assertEqual(list_res.status_code, 200)
        self.assertContains(list_res, 'studentuser')
        self.assertContains(list_res, 'Strong candidate proposal')

        # Accept applicant
        accept_res = self.client.post(reverse('applications:application_status', kwargs={'pk': app.pk, 'new_status': 'accepted'}))
        self.assertEqual(accept_res.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.status, Application.Status.ACCEPTED)

    def test_student_dashboard_and_withdraw(self):
        app = Application.objects.create(
            project=self.project,
            student=self.student,
            cover_letter='Need to withdraw later',
            status=Application.Status.PENDING
        )
        self.client.login(username='studentuser', password='Password123!')
        dash_res = self.client.get(reverse('applications:student_dashboard'))
        self.assertEqual(dash_res.status_code, 200)
        self.assertContains(dash_res, 'STM32 Drone Flight Controller')

        # Withdraw
        withdraw_res = self.client.post(reverse('applications:application_withdraw', kwargs={'pk': app.pk}))
        self.assertEqual(withdraw_res.status_code, 302)
        self.assertFalse(Application.objects.filter(pk=app.pk).exists())

    def test_unauthenticated_user_cannot_submit_application(self):
        res = self.client.get(reverse('applications:project_apply', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login/', res.url)

    def test_project_owner_cannot_apply_to_own_project(self):
        # Even if owner is student/admin, owner cannot apply to own project
        self.project.client = self.student
        self.project.save()
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('applications:project_apply', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 403)

    def test_non_owner_cannot_view_another_project_applications(self):
        self.client.login(username='otherstudent', password='Password123!')
        res = self.client.get(reverse('applications:applicants_list', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 403)

    def test_project_owner_can_reject_pending_application(self):
        app = Application.objects.create(
            project=self.project,
            student=self.student,
            cover_letter='Proposal text'
        )
        self.client.login(username='clientuser', password='Password123!')
        res = self.client.post(reverse('applications:application_reject', kwargs={'pk': app.pk}))
        self.assertEqual(res.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.status, Application.Status.REJECTED)

    def test_non_owner_cannot_accept_or_reject_application(self):
        app = Application.objects.create(
            project=self.project,
            student=self.student,
            cover_letter='Proposal text'
        )
        self.client.login(username='otherstudent', password='Password123!')
        res_accept = self.client.post(reverse('applications:application_accept', kwargs={'pk': app.pk}))
        self.assertEqual(res_accept.status_code, 403)

        res_reject = self.client.post(reverse('applications:application_reject', kwargs={'pk': app.pk}))
        self.assertEqual(res_reject.status_code, 403)

    def test_applicant_sees_submitted_status_on_project_detail(self):
        app = Application.objects.create(
            project=self.project,
            student=self.student,
            cover_letter='My proposal'
        )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('projects:project_detail', kwargs={'pk': self.project.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Application Submitted')
        self.assertContains(res, 'Pending')

    def test_empty_application_form_is_rejected(self):
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.post(reverse('applications:project_apply', kwargs={'pk': self.project.pk}), {
            'cover_letter': ''
        })
        self.assertEqual(res.status_code, 200)
        self.assertFormError(res.context['form'], 'cover_letter', 'This field is required.')

    def test_cannot_transition_already_finalized_application(self):
        app = Application.objects.create(
            project=self.project,
            student=self.student,
            cover_letter='Proposal',
            status=Application.Status.ACCEPTED
        )
        self.client.login(username='clientuser', password='Password123!')
        res = self.client.post(reverse('applications:application_reject', kwargs={'pk': app.pk}))
        self.assertEqual(res.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.status, Application.Status.ACCEPTED)

    def test_get_request_on_accept_or_reject_is_denied(self):
        app = Application.objects.create(
            project=self.project,
            student=self.student,
            cover_letter='Proposal'
        )
        self.client.login(username='clientuser', password='Password123!')
        res = self.client.get(reverse('applications:application_accept', kwargs={'pk': app.pk}))
        self.assertEqual(res.status_code, 403)

    def test_in_progress_project_cannot_receive_new_applications(self):
        self.project.status = Project.Status.IN_PROGRESS
        self.project.save()

        self.client.login(username='studentuser', password='Password123!')
        res = self.client.post(reverse('applications:project_apply', kwargs={'pk': self.project.pk}), {
            'cover_letter': 'Trying to apply late'
        })
        self.assertEqual(res.status_code, 302)
        self.assertFalse(Application.objects.filter(project=self.project, student=self.student).exists())

    def test_completed_project_cannot_receive_new_applications(self):
        self.project.status = Project.Status.COMPLETED
        self.project.save()

        self.client.login(username='studentuser', password='Password123!')
        res = self.client.post(reverse('applications:project_apply', kwargs={'pk': self.project.pk}), {
            'cover_letter': 'Trying to apply to completed project'
        })
        self.assertEqual(res.status_code, 302)
        self.assertFalse(Application.objects.filter(project=self.project, student=self.student).exists())

    def test_cancelled_closed_project_cannot_receive_new_applications(self):
        self.project.status = Project.Status.CLOSED
        self.project.save()

        self.client.login(username='studentuser', password='Password123!')
        res = self.client.post(reverse('applications:project_apply', kwargs={'pk': self.project.pk}), {
            'cover_letter': 'Trying to apply to closed project'
        })
        self.assertEqual(res.status_code, 302)
        self.assertFalse(Application.objects.filter(project=self.project, student=self.student).exists())

    def test_accepting_application_transitions_open_project_to_in_progress(self):
        app = Application.objects.create(
            project=self.project,
            student=self.student,
            cover_letter='Proposal'
        )
        self.client.login(username='clientuser', password='Password123!')
        res = self.client.post(reverse('applications:application_accept', kwargs={'pk': app.pk}))
        self.assertEqual(res.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.status, Application.Status.ACCEPTED)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.IN_PROGRESS)

    def test_cannot_accept_application_on_completed_or_closed_project(self):
        app = Application.objects.create(
            project=self.project,
            student=self.student,
            cover_letter='Proposal'
        )
        self.project.status = Project.Status.COMPLETED
        self.project.save()

        self.client.login(username='clientuser', password='Password123!')
        res = self.client.post(reverse('applications:application_accept', kwargs={'pk': app.pk}))
        self.assertEqual(res.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.status, Application.Status.PENDING)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.COMPLETED)

    def test_accepting_application_creates_team_membership(self):
        app = Application.objects.create(
            project=self.project,
            student=self.student,
            cover_letter='Proposal for team work'
        )
        self.client.login(username='clientuser', password='Password123!')
        res = self.client.post(reverse('applications:application_accept', kwargs={'pk': app.pk}))
        self.assertEqual(res.status_code, 302)
        
        # Verify student is now a team member
        team = self.project.get_team()
        self.assertTrue(team.members.filter(id=self.student.id).exists())
        self.assertTrue(ProjectMembership.objects.filter(team=team, user=self.student).exists())

    def test_duplicate_team_membership_prevented(self):
        app = Application.objects.create(
            project=self.project,
            student=self.student,
            cover_letter='Proposal'
        )
        self.client.login(username='clientuser', password='Password123!')
        # Accept first time
        res1 = self.client.post(reverse('applications:application_accept', kwargs={'pk': app.pk}))
        self.assertEqual(res1.status_code, 302)

        # Attempt to accept again (already decided)
        res2 = self.client.post(reverse('applications:application_accept', kwargs={'pk': app.pk}))
        self.assertEqual(res2.status_code, 302)

        team = self.project.get_team()
        self.assertEqual(ProjectMembership.objects.filter(team=team, user=self.student).count(), 1)
        self.assertEqual(team.members.filter(id=self.student.id).count(), 1)


class StudentDashboardIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.client_user = User.objects.create_user(
            username='clientuser',
            email='client@ruet.ac.bd',
            password='Password123!',
            role=User.Role.CLIENT,
            company_name='Embedded Systems Lab'
        )
        self.student = User.objects.create_user(
            username='studentuser',
            email='student@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT,
            skills='C, RTOS, PCB Design'
        )
        self.other_student = User.objects.create_user(
            username='otherstudent',
            email='otherstudent@ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT,
            skills='Python, Django'
        )
        self.project1 = Project.objects.create(
            client=self.client_user,
            title='Drone Flight Controller',
            description='Firmware for quadcopter.',
            category='Robotics',
            budget=200.00,
            status=Project.Status.IN_PROGRESS
        )
        self.project2 = Project.objects.create(
            client=self.client_user,
            title='Autonomous Ground Vehicle',
            description='Path planning algorithm.',
            category='Robotics',
            budget=350.00,
            status=Project.Status.OPEN
        )
        self.project3 = Project.objects.create(
            client=self.client_user,
            title='Smart Campus Sensor Node',
            description='IoT telemetry.',
            category='IoT',
            budget=150.00,
            status=Project.Status.COMPLETED
        )

    def test_student_dashboard_authenticated_student_access(self):
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('applications:student_dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'applications/student_dashboard.html')

    def test_student_dashboard_non_student_forbidden(self):
        self.client.login(username='clientuser', password='Password123!')
        res = self.client.get(reverse('applications:student_dashboard'))
        self.assertEqual(res.status_code, 403)

    def test_student_dashboard_unauthenticated_redirect(self):
        res = self.client.get(reverse('applications:student_dashboard'))
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse('accounts:login'), res.url)

    def test_student_dashboard_metrics_breakdown(self):
        Application.objects.create(
            project=self.project1,
            student=self.student,
            status=Application.Status.ACCEPTED,
            cover_letter='Accepted application'
        )
        Application.objects.create(
            project=self.project2,
            student=self.student,
            status=Application.Status.PENDING,
            cover_letter='Pending application'
        )
        Application.objects.create(
            project=self.project3,
            student=self.student,
            status=Application.Status.REJECTED,
            cover_letter='Rejected application'
        )

        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('applications:student_dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['pending_count'], 1)
        self.assertEqual(res.context['accepted_count'], 1)
        self.assertEqual(res.context['rejected_count'], 1)
        self.assertEqual(res.context['applications'].count(), 3)

    def test_student_dashboard_shows_only_own_applications(self):
        app_mine = Application.objects.create(
            project=self.project1,
            student=self.student,
            status=Application.Status.PENDING,
            cover_letter='My proposal'
        )
        app_other = Application.objects.create(
            project=self.project2,
            student=self.other_student,
            status=Application.Status.PENDING,
            cover_letter='Other secret proposal'
        )

        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('applications:student_dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertIn(app_mine, res.context['applications'])
        self.assertNotIn(app_other, res.context['applications'])
        self.assertContains(res, 'Drone Flight Controller')
        self.assertNotContains(res, 'Other secret proposal')

    def test_student_dashboard_shows_project_lifecycle_status(self):
        Application.objects.create(
            project=self.project1,
            student=self.student,
            status=Application.Status.ACCEPTED,
            cover_letter='Accepted proposal'
        )
        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('applications:student_dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'In Progress')

    def test_student_dashboard_workspace_button_strictly_for_accepted(self):
        Application.objects.create(
            project=self.project1,
            student=self.student,
            status=Application.Status.ACCEPTED,
            cover_letter='Accepted proposal'
        )
        Application.objects.create(
            project=self.project2,
            student=self.student,
            status=Application.Status.PENDING,
            cover_letter='Pending proposal'
        )
        Application.objects.create(
            project=self.project3,
            student=self.student,
            status=Application.Status.REJECTED,
            cover_letter='Rejected proposal'
        )

        workspace_url_accepted = reverse('projects:project_workspace', kwargs={'pk': self.project1.pk})
        workspace_url_pending = reverse('projects:project_workspace', kwargs={'pk': self.project2.pk})
        workspace_url_rejected = reverse('projects:project_workspace', kwargs={'pk': self.project3.pk})

        self.client.login(username='studentuser', password='Password123!')
        res = self.client.get(reverse('applications:student_dashboard'))
        self.assertEqual(res.status_code, 200)

        self.assertContains(res, workspace_url_accepted)
        self.assertNotContains(res, workspace_url_pending)
        self.assertNotContains(res, workspace_url_rejected)




