import io
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from accounts.models import Review
from projects.models import Project, ProjectTeam, ProjectMembership
from applications.models import Application
from services.models import Service
from apps.messaging.models import Conversation

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
            'email': '1903123@student.ruet.ac.bd',
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

    def test_student_registration_requires_exact_ruet_student_email(self):
        invalid_emails = (
            'student@gmail.com',
            '123456@student.ruet.ac.bd',
            '12345678@student.ruet.ac.bd',
            'abcdefg@student.ruet.ac.bd',
            '1234567@ruet.ac.bd',
            '1234567@cse.ruet.ac.bd',
            '1234567@student.ruet.com',
        )
        for index, email in enumerate(invalid_emails):
            response = self.client.post(reverse('accounts:register'), {
                'username': f'invalidstudent{index}',
                'email': email,
                'role': 'student',
                'skills': '',
                'company_name': '',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn('Student accounts require a valid RUET student email', response.context['form'].errors['email'][0])

    def test_student_email_is_normalized_case_insensitively(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'mixedstudent',
            'email': '1903123@STUDENT.RUET.AC.BD',
            'role': 'student',
            'skills': '',
            'company_name': '',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            User.objects.get(username='mixedstudent').email,
            '1903123@student.ruet.ac.bd',
        )

    def test_client_accepts_general_and_ruet_student_emails(self):
        for index, email in enumerate((
            'someone@gmail.com',
            'someone@yahoo.com',
            'someone@outlook.com',
            'someone@example.com',
            '1234567@student.ruet.ac.bd',
        )):
            response = self.client.post(reverse('accounts:register'), {
                'username': f'validclient{index}',
                'email': email,
                'role': 'client',
                'skills': '',
                'company_name': 'CRAFT Client',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            })
            self.assertEqual(response.status_code, 302)

    def test_client_rejects_invalid_email_syntax(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'invalidclient',
            'email': 'not-an-email',
            'role': 'client',
            'skills': '',
            'company_name': 'CRAFT Client',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors['email'])

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

    def test_profile_edit_page_renders_for_authenticated_owner(self):
        self.client.login(username='teststudent', password='Password123!')
        res = self.client.get(reverse('accounts:profile_edit'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Edit Profile')
        self.assertContains(res, 'Profile Picture')
        self.assertContains(res, 'Academic Department')

    def test_profile_edit_requires_authentication(self):
        res = self.client.get(reverse('accounts:profile_edit'))
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse('accounts:login'), res['Location'])

    def test_profile_update_academic_and_portfolio_fields(self):
        self.client.login(username='teststudent', password='Password123!')
        res = self.client.post(reverse('accounts:profile_edit'), {
            'first_name': 'Sumaiya',
            'last_name': 'Kulsum',
            'email': 'student@ruet.ac.bd',
            'department': 'Computer Science & Engineering',
            'student_id': '1903001',
            'bio': 'Passionate about robotics and full-stack systems.',
            'skills': 'Django, Python, Embedded C',
            'portfolio_url': 'https://kulsum.dev',
            'github_url': 'https://github.com/kulsum',
            'linkedin_url': 'https://linkedin.com/in/kulsum',
        })
        self.assertEqual(res.status_code, 302)
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, 'Sumaiya')
        self.assertEqual(self.student.department, 'Computer Science & Engineering')
        self.assertEqual(self.student.student_id, '1903001')
        self.assertEqual(self.student.portfolio_url, 'https://kulsum.dev')
        self.assertEqual(self.student.github_url, 'https://github.com/kulsum')
        self.assertEqual(self.student.linkedin_url, 'https://linkedin.com/in/kulsum')

    def test_profile_update_client_company_and_website(self):
        self.client.login(username='testclient', password='Password123!')
        res = self.client.post(reverse('accounts:profile_edit'), {
            'first_name': 'Farhan',
            'last_name': 'Ahmed',
            'email': 'client@ruet.ac.bd',
            'company_name': 'RUET Innovation Club',
            'website_url': 'https://innovation.ruet.ac.bd',
            'bio': 'Organizing campus hackathons and tech initiatives.',
        })
        self.assertEqual(res.status_code, 302)
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.first_name, 'Farhan')
        self.assertEqual(self.client_user.company_name, 'RUET Innovation Club')
        self.assertEqual(self.client_user.website_url, 'https://innovation.ruet.ac.bd')

    def test_profile_picture_upload_and_display(self):
        self.client.login(username='teststudent', password='Password123!')
        # Generate valid test image
        img = Image.new('RGB', (10, 10), color='blue')
        img_io = io.BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        uploaded = SimpleUploadedFile('avatar.png', img_io.getvalue(), content_type='image/png')

        res = self.client.post(reverse('accounts:profile_edit'), {
            'first_name': 'Test',
            'last_name': 'Student',
            'email': 'student@ruet.ac.bd',
            'bio': 'Bio with picture',
            'profile_picture': uploaded,
        })
        self.assertEqual(res.status_code, 302)
        self.student.refresh_from_db()
        self.assertTrue(bool(self.student.profile_picture))
        self.assertIn('profile_pics/', self.student.profile_picture.name)

        # Check that avatar displays on profile page and navbar
        profile_res = self.client.get(reverse('accounts:profile'))
        self.assertEqual(profile_res.status_code, 200)
        self.assertContains(profile_res, self.student.profile_picture.url)

    def test_profile_picture_rejects_unsupported_extension(self):
        self.client.login(username='teststudent', password='Password123!')
        fake_file = SimpleUploadedFile('script.sh', b'echo Hello', content_type='text/plain')
        res = self.client.post(reverse('accounts:profile_edit'), {
            'first_name': 'Test',
            'last_name': 'Student',
            'email': 'student@ruet.ac.bd',
            'profile_picture': fake_file,
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('profile_picture', res.context['form'].errors)

    def test_public_profile_view_student(self):
        self.client.login(username='testclient', password='Password123!')
        res = self.client.get(reverse('accounts:public_profile', kwargs={'pk': self.student.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'teststudent')
        self.assertContains(res, 'Student')
        self.assertContains(res, 'Send Message')
        self.assertNotContains(res, 'Edit Profile Information')

    def test_public_profile_view_client(self):
        self.client.login(username='teststudent', password='Password123!')
        res = self.client.get(reverse('accounts:public_profile', kwargs={'pk': self.client_user.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Robotics Club')
        self.assertContains(res, 'Send Message')

    def test_public_profile_view_own_profile_shows_edit_button(self):
        self.client.login(username='teststudent', password='Password123!')
        res = self.client.get(reverse('accounts:public_profile', kwargs={'pk': self.student.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Edit My Profile')
        self.assertNotContains(res, 'Send Message')

    def test_public_profile_requires_login(self):
        res = self.client.get(reverse('accounts:public_profile', kwargs={'pk': self.student.pk}))
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse('accounts:login'), res['Location'])

    def test_student_cannot_update_email_to_invalid_domain(self):
        self.client.login(username='teststudent', password='Password123!')
        res = self.client.post(reverse('accounts:profile_edit'), {
            'first_name': 'Test',
            'last_name': 'Student',
            'email': 'fake@gmail.com',
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('email', res.context['form'].errors)
        self.assertIn('Student accounts require a valid RUET student email', res.context['form'].errors['email'][0])

    def test_user_cannot_claim_another_users_email(self):
        User.objects.create_user(
            username='otherstudent',
            email='1903999@student.ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT,
        )
        self.client.login(username='teststudent', password='Password123!')
        res = self.client.post(reverse('accounts:profile_edit'), {
            'first_name': 'Test',
            'last_name': 'Student',
            'email': '1903999@student.ruet.ac.bd',
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('email', res.context['form'].errors)
        self.assertIn('already exists', res.context['form'].errors['email'][0])



class ReviewModelTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='labclient',
            email='client@ruet.ac.bd',
            password='Password123!',
            role=User.Role.CLIENT,
            company_name='Robotics & IoT Lab'
        )
        self.student_user = User.objects.create_user(
            username='devstudent',
            email='1903001@student.ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT,
            skills='Embedded C, ROS, Python'
        )
        self.student_user_2 = User.objects.create_user(
            username='designstudent',
            email='1903002@student.ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT,
            skills='CAD, SolidWorks'
        )
        self.project_1 = Project.objects.create(
            client=self.client_user,
            title='Quadcopter Firmware & Flight Control',
            description='Design stabilization and telemetry firmware.',
            budget=250.00,
            status=Project.Status.COMPLETED
        )
        self.project_2 = Project.objects.create(
            client=self.client_user,
            title='Autonomous Rover Chassis CAD',
            description='Design structural CAD models for chassis.',
            budget=180.00,
            status=Project.Status.COMPLETED
        )

    def test_valid_review_creation(self):
        review = Review.objects.create(
            project=self.project_1,
            reviewer=self.client_user,
            reviewed_user=self.student_user,
            rating=5,
            comment='Outstanding firmware design and great documentation.'
        )
        self.assertIsNotNone(review.pk)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, 'Outstanding firmware design and great documentation.')
        self.assertEqual(review.project, self.project_1)
        self.assertEqual(review.reviewer, self.client_user)
        self.assertEqual(review.reviewed_user, self.student_user)
        self.assertIn('labclient', str(review))
        self.assertIn('devstudent', str(review))
        self.assertIn('5★', str(review))

    def test_rating_1_and_5_are_valid(self):
        r1 = Review(
            project=self.project_1,
            reviewer=self.client_user,
            reviewed_user=self.student_user,
            rating=1,
            comment='Minimum valid rating.'
        )
        r1.full_clean()
        r1.save()
        self.assertEqual(r1.rating, 1)

        r5 = Review(
            project=self.project_2,
            reviewer=self.client_user,
            reviewed_user=self.student_user,
            rating=5,
            comment='Maximum valid rating.'
        )
        r5.full_clean()
        r5.save()
        self.assertEqual(r5.rating, 5)

    def test_rating_0_rejected_by_validation(self):
        review = Review(
            project=self.project_1,
            reviewer=self.client_user,
            reviewed_user=self.student_user,
            rating=0,
            comment='Below minimum rating.'
        )
        with self.assertRaises(ValidationError) as ctx:
            review.full_clean()
        self.assertIn('rating', ctx.exception.message_dict)

    def test_rating_6_rejected_by_validation(self):
        review = Review(
            project=self.project_1,
            reviewer=self.client_user,
            reviewed_user=self.student_user,
            rating=6,
            comment='Above maximum rating.'
        )
        with self.assertRaises(ValidationError) as ctx:
            review.full_clean()
        self.assertIn('rating', ctx.exception.message_dict)

    def test_self_review_rejected_by_validation_and_database(self):
        review = Review(
            project=self.project_1,
            reviewer=self.student_user,
            reviewed_user=self.student_user,
            rating=5,
            comment='Self review attempt.'
        )
        # Validation level
        with self.assertRaises(ValidationError) as ctx:
            review.full_clean()
        self.assertIn('reviewed_user', ctx.exception.message_dict)

        # Database constraint level
        with self.assertRaises(IntegrityError):
            Review.objects.create(
                project=self.project_1,
                reviewer=self.student_user,
                reviewed_user=self.student_user,
                rating=5,
                comment='Self review attempt.'
            )

    def test_duplicate_review_for_same_project_pair_rejected_by_db_constraint(self):
        Review.objects.create(
            project=self.project_1,
            reviewer=self.client_user,
            reviewed_user=self.student_user,
            rating=4,
            comment='Initial review.'
        )
        with self.assertRaises(IntegrityError):
            Review.objects.create(
                project=self.project_1,
                reviewer=self.client_user,
                reviewed_user=self.student_user,
                rating=5,
                comment='Duplicate review attempt.'
            )

    def test_same_reviewer_can_review_same_user_on_different_project(self):
        r1 = Review.objects.create(
            project=self.project_1,
            reviewer=self.client_user,
            reviewed_user=self.student_user,
            rating=4,
            comment='Review on project 1.'
        )
        r2 = Review.objects.create(
            project=self.project_2,
            reviewer=self.client_user,
            reviewed_user=self.student_user,
            rating=5,
            comment='Review on project 2.'
        )
        self.assertEqual(Review.objects.filter(reviewer=self.client_user, reviewed_user=self.student_user).count(), 2)
        self.assertEqual(r1.project, self.project_1)
        self.assertEqual(r2.project, self.project_2)

    def test_same_project_allows_reviews_between_different_pairs(self):
        # Client reviews student 1
        r1 = Review.objects.create(
            project=self.project_1,
            reviewer=self.client_user,
            reviewed_user=self.student_user,
            rating=5,
            comment='Client evaluating student 1.'
        )
        # Student 1 reviews client
        r2 = Review.objects.create(
            project=self.project_1,
            reviewer=self.student_user,
            reviewed_user=self.client_user,
            rating=4,
            comment='Student 1 evaluating client.'
        )
        # Client reviews student 2
        r3 = Review.objects.create(
            project=self.project_1,
            reviewer=self.client_user,
            reviewed_user=self.student_user_2,
            rating=3,
            comment='Client evaluating student 2.'
        )
        self.assertEqual(self.project_1.reviews.count(), 3)
        self.assertIn(r1, self.project_1.reviews.all())
        self.assertIn(r2, self.project_1.reviews.all())
        self.assertIn(r3, self.project_1.reviews.all())

    def test_user_with_no_received_reviews_returns_none_and_zero(self):
        self.assertIsNone(self.student_user.average_rating)
        self.assertEqual(self.student_user.review_count, 0)
        self.assertIsNone(self.client_user.average_rating)
        self.assertEqual(self.client_user.review_count, 0)

    def test_user_review_count_and_average_rating_calculation(self):
        Review.objects.create(
            project=self.project_1,
            reviewer=self.client_user,
            reviewed_user=self.student_user,
            rating=4,
            comment='Good performance.'
        )
        Review.objects.create(
            project=self.project_2,
            reviewer=self.client_user,
            reviewed_user=self.student_user,
            rating=5,
            comment='Exceptional work.'
        )
        self.assertEqual(self.student_user.review_count, 2)
        # Average: (4 + 5) / 2 = 4.5
        self.assertEqual(self.student_user.average_rating, 4.5)

        # Add a third review from another client: rating 4 -> (4 + 5 + 4) / 3 = 4.333... -> rounded to 4.3
        other_client = User.objects.create_user(
            username='otherlab',
            email='otherlab@ruet.ac.bd',
            password='Password123!',
            role=User.Role.CLIENT
        )
        project_3 = Project.objects.create(
            client=other_client,
            title='Telemetry Station',
            budget=120.00,
            status=Project.Status.COMPLETED
        )
        Review.objects.create(
            project=project_3,
            reviewer=other_client,
            reviewed_user=self.student_user,
            rating=4,
            comment='Solid telemetry implementation.'
        )
        self.student_user.refresh_from_db()
        self.assertEqual(self.student_user.review_count, 3)
        self.assertEqual(self.student_user.average_rating, 4.3)

    def test_blank_comment_rejected_by_clean(self):
        review = Review(
            project=self.project_1,
            reviewer=self.client_user,
            reviewed_user=self.student_user,
            rating=5,
            comment='   '
        )
        with self.assertRaises(ValidationError) as ctx:
            review.full_clean()
        self.assertIn('comment', ctx.exception.message_dict)

    def test_review_ordering_newest_first(self):
        r1 = Review.objects.create(
            project=self.project_1,
            reviewer=self.client_user,
            reviewed_user=self.student_user,
            rating=3,
            comment='Earlier review.'
        )
        r2 = Review.objects.create(
            project=self.project_2,
            reviewer=self.client_user,
            reviewed_user=self.student_user,
            rating=5,
            comment='Later review.'
        )
        reviews = list(self.student_user.reviews_received.all())
        self.assertEqual(reviews[0].pk, r2.pk)
        self.assertEqual(reviews[1].pk, r1.pk)


class ReviewUIAndSubmissionIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.client_user = User.objects.create_user(
            username='labclient',
            email='labclient@example.com',
            password='Password123!',
            role=User.Role.CLIENT,
            company_name='Robotics Innovation Lab'
        )
        self.student_user = User.objects.create_user(
            username='devstudent',
            email='1903001@student.ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT,
            skills='Embedded C, ROS, Circuit Design'
        )
        self.other_student = User.objects.create_user(
            username='otherstudent',
            email='1903002@student.ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT,
            skills='Figma, UI/UX'
        )
        self.completed_project = Project.objects.create(
            client=self.client_user,
            title='Autonomous Obstacle Avoidance Rover',
            description='Firmware and hardware testing for rover.',
            budget=350.00,
            status=Project.Status.COMPLETED
        )
        self.in_progress_project = Project.objects.create(
            client=self.client_user,
            title='Ongoing Sensor Calibration',
            description='Calibrate LiDAR sensors.',
            budget=200.00,
            status=Project.Status.IN_PROGRESS
        )
        # Accepted application for completed project
        self.accepted_app = Application.objects.create(
            project=self.completed_project,
            student=self.student_user,
            cover_letter='Experienced in robotics.',
            status=Application.Status.ACCEPTED
        )
        # Pending application for in-progress project
        self.pending_app = Application.objects.create(
            project=self.in_progress_project,
            student=self.student_user,
            cover_letter='Want to help.',
            status=Application.Status.PENDING
        )

    def test_public_profile_displays_reviews_and_ratings(self):
        Review.objects.create(
            project=self.completed_project,
            reviewer=self.client_user,
            reviewed_user=self.student_user,
            rating=5,
            comment='Superb firmware engineering and prompt delivery.'
        )
        self.client.login(username='otherstudent', password='Password123!')
        response = self.client.get(reverse('accounts:public_profile', kwargs={'pk': self.student_user.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reviews & Ratings')
        self.assertContains(response, '5.0')
        self.assertContains(response, 'Superb firmware engineering')
        self.assertContains(response, 'Robotics Innovation Lab')
        self.assertContains(response, self.completed_project.title)

    def test_public_profile_shows_empty_state_when_no_reviews(self):
        self.client.login(username='devstudent', password='Password123!')
        response = self.client.get(reverse('accounts:public_profile', kwargs={'pk': self.student_user.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No reviews received yet')

    def test_submit_review_view_requires_login(self):
        response = self.client.get(reverse('accounts:submit_review', kwargs={
            'project_pk': self.completed_project.pk,
            'user_pk': self.student_user.pk
        }))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_client_can_submit_review_for_accepted_student_on_completed_project(self):
        self.client.login(username='labclient', password='Password123!')
        url = reverse('accounts:submit_review', kwargs={
            'project_pk': self.completed_project.pk,
            'user_pk': self.student_user.pk
        })
        # GET form
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Submit Collaboration Review')
        self.assertContains(response, self.completed_project.title)

        # POST review
        post_response = self.client.post(url, {
            'rating': '5',
            'comment': 'Outstanding contribution to the robotics project.'
        }, follow=True)
        self.assertEqual(post_response.status_code, 200)
        self.assertTrue(Review.objects.filter(
            project=self.completed_project,
            reviewer=self.client_user,
            reviewed_user=self.student_user,
            rating=5
        ).exists())

    def test_student_can_submit_review_for_client_on_completed_project(self):
        self.client.login(username='devstudent', password='Password123!')
        url = reverse('accounts:submit_review', kwargs={
            'project_pk': self.completed_project.pk,
            'user_pk': self.client_user.pk
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        post_response = self.client.post(url, {
            'rating': '4',
            'comment': 'Great communication, clear requirements and timely milestone payments.'
        }, follow=True)
        self.assertEqual(post_response.status_code, 200)
        self.assertTrue(Review.objects.filter(
            project=self.completed_project,
            reviewer=self.student_user,
            reviewed_user=self.client_user,
            rating=4
        ).exists())

    def test_review_submission_rejected_for_incomplete_project(self):
        self.client.login(username='labclient', password='Password123!')
        url = reverse('accounts:submit_review', kwargs={
            'project_pk': self.in_progress_project.pk,
            'user_pk': self.student_user.pk
        })
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reviews can only be submitted for completed projects')
        self.assertEqual(Review.objects.filter(project=self.in_progress_project).count(), 0)

    def test_review_submission_rejected_for_unrelated_student(self):
        self.client.login(username='otherstudent', password='Password123!')
        url = reverse('accounts:submit_review', kwargs={
            'project_pk': self.completed_project.pk,
            'user_pk': self.client_user.pk
        })
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You must be an accepted participant on this project')
        self.assertEqual(Review.objects.filter(reviewer=self.other_student).count(), 0)

    def test_student_cannot_review_another_student(self):
        second_accepted_student = User.objects.create_user(
            username='studenttwo',
            email='1903003@student.ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT
        )
        Application.objects.create(
            project=self.completed_project,
            student=second_accepted_student,
            status=Application.Status.ACCEPTED
        )
        self.client.login(username='devstudent', password='Password123!')
        url = reverse('accounts:submit_review', kwargs={
            'project_pk': self.completed_project.pk,
            'user_pk': second_accepted_student.pk
        })
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Student participants can only review the project client')
        self.assertEqual(Review.objects.filter(reviewed_user=second_accepted_student).count(), 0)

    def test_self_review_rejected_in_view(self):
        self.client.login(username='labclient', password='Password123!')
        url = reverse('accounts:submit_review', kwargs={
            'project_pk': self.completed_project.pk,
            'user_pk': self.client_user.pk
        })
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You cannot review yourself')
        self.assertEqual(Review.objects.filter(reviewer=self.client_user, reviewed_user=self.client_user).count(), 0)

    def test_duplicate_review_rejected_in_view(self):
        Review.objects.create(
            project=self.completed_project,
            reviewer=self.client_user,
            reviewed_user=self.student_user,
            rating=5,
            comment='First review.'
        )
        self.client.login(username='labclient', password='Password123!')
        url = reverse('accounts:submit_review', kwargs={
            'project_pk': self.completed_project.pk,
            'user_pk': self.student_user.pk
        })
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You have already reviewed')
        self.assertEqual(Review.objects.filter(project=self.completed_project, reviewer=self.client_user).count(), 1)

    def test_review_form_validation_rejects_blank_comment(self):
        self.client.login(username='labclient', password='Password123!')
        url = reverse('accounts:submit_review', kwargs={
            'project_pk': self.completed_project.pk,
            'user_pk': self.student_user.pk
        })
        response = self.client.post(url, {
            'rating': '5',
            'comment': '   '
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Review comment cannot be blank.')
        self.assertEqual(Review.objects.filter(project=self.completed_project).count(), 0)

    def test_submit_review_project_url_defaults_to_single_accepted_student(self):
        self.client.login(username='labclient', password='Password123!')
        url = reverse('accounts:submit_review_project', kwargs={
            'project_pk': self.completed_project.pk
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student_user.display_name)


class CrossAppPublicProfileIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.client_user = User.objects.create_user(
            username='labclient',
            email='labclient@ruet.ac.bd',
            password='Password123!',
            role=User.Role.CLIENT,
            first_name='Robotics',
            last_name='Organizer',
            company_name='Robotics Innovation Lab',
            bio='Building campus robots.'
        )
        self.student_user = User.objects.create_user(
            username='devstudent',
            email='1903001@student.ruet.ac.bd',
            password='Password123!',
            role=User.Role.STUDENT,
            first_name='Rahim',
            last_name='Uddin',
            skills='Python, ROS, Computer Vision'
        )
        self.project = Project.objects.create(
            client=self.client_user,
            title='Autonomous Obstacle Avoidance Rover',
            description='Firmware and hardware testing for rover.',
            budget=350.00,
            status=Project.Status.OPEN
        )
        self.application = Application.objects.create(
            project=self.project,
            student=self.student_user,
            cover_letter='Experienced in robotics.',
            status=Application.Status.PENDING
        )
        self.service = Service.objects.create(
            creator=self.student_user,
            title='Autonomous ROS Node Development',
            description='I will write and debug custom ROS2 nodes for your robot.',
            category=Service.Category.EMBEDDED,
            skills='ROS2, Python, C++',
            price_estimate=150.00
        )
        self.conversation, _ = Conversation.get_or_create_between(self.student_user, self.client_user)

    def test_project_detail_links_to_client_public_profile(self):
        self.client.login(username='devstudent', password='Password123!')
        response = self.client.get(reverse('projects:project_detail', kwargs={'pk': self.project.pk}))
        self.assertEqual(response.status_code, 200)
        profile_url = reverse('accounts:public_profile', kwargs={'pk': self.client_user.pk})
        self.assertContains(response, profile_url)
        self.assertContains(response, 'View Client Profile')

    def test_project_list_links_to_client_public_profile(self):
        self.client.login(username='devstudent', password='Password123!')
        response = self.client.get(reverse('projects:project_list'))
        self.assertEqual(response.status_code, 200)
        profile_url = reverse('accounts:public_profile', kwargs={'pk': self.client_user.pk})
        self.assertContains(response, profile_url)

    def test_applicants_list_links_to_student_public_profile(self):
        self.client.login(username='labclient', password='Password123!')
        response = self.client.get(reverse('applications:applicants_list', kwargs={'pk': self.project.pk}))
        self.assertEqual(response.status_code, 200)
        profile_url = reverse('accounts:public_profile', kwargs={'pk': self.student_user.pk})
        self.assertContains(response, profile_url)

    def test_service_detail_links_to_student_public_profile(self):
        response = self.client.get(reverse('services:service_detail', kwargs={'pk': self.service.pk}))
        self.assertEqual(response.status_code, 200)
        profile_url = reverse('accounts:public_profile', kwargs={'pk': self.student_user.pk})
        self.assertContains(response, profile_url)
        self.assertContains(response, 'View Student Profile')

    def test_service_list_links_to_student_public_profile(self):
        response = self.client.get(reverse('services:service_list'))
        self.assertEqual(response.status_code, 200)
        profile_url = reverse('accounts:public_profile', kwargs={'pk': self.student_user.pk})
        self.assertContains(response, profile_url)

    def test_conversation_detail_links_to_other_user_public_profile(self):
        # As student viewing conversation with client
        self.client.login(username='devstudent', password='Password123!')
        response = self.client.get(reverse('messaging:conversation_detail', kwargs={'pk': self.conversation.pk}))
        self.assertEqual(response.status_code, 200)
        client_profile_url = reverse('accounts:public_profile', kwargs={'pk': self.client_user.pk})
        self.assertContains(response, client_profile_url)
        self.assertContains(response, 'View Profile')

        # As client viewing conversation with student
        self.client.login(username='labclient', password='Password123!')
        response = self.client.get(reverse('messaging:conversation_detail', kwargs={'pk': self.conversation.pk}))
        self.assertEqual(response.status_code, 200)
        student_profile_url = reverse('accounts:public_profile', kwargs={'pk': self.student_user.pk})
        self.assertContains(response, student_profile_url)

    def test_workspace_links_to_team_and_client_public_profiles(self):
        # Accept student to grant workspace access
        self.application.status = Application.Status.ACCEPTED
        self.application.save()
        self.project.status = Project.Status.IN_PROGRESS
        self.project.save()
        team, _ = ProjectTeam.objects.get_or_create(project=self.project)
        ProjectMembership.objects.create(team=team, user=self.student_user)

        self.client.login(username='labclient', password='Password123!')
        response = self.client.get(reverse('projects:project_workspace', kwargs={'pk': self.project.pk}))
        self.assertEqual(response.status_code, 200)
        student_profile_url = reverse('accounts:public_profile', kwargs={'pk': self.student_user.pk})
        client_profile_url = reverse('accounts:public_profile', kwargs={'pk': self.client_user.pk})
        self.assertContains(response, student_profile_url)
        self.assertContains(response, client_profile_url)

    def test_student_dashboard_links_to_client_public_profile(self):
        self.client.login(username='devstudent', password='Password123!')
        response = self.client.get(reverse('applications:student_dashboard'))
        self.assertEqual(response.status_code, 200)
        client_profile_url = reverse('accounts:public_profile', kwargs={'pk': self.client_user.pk})
        self.assertContains(response, client_profile_url)
