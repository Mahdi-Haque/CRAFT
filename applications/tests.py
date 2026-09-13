from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from projects.models import Project
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

