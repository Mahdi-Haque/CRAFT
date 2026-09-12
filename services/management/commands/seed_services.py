from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from services.models import Service

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds clearly identifiable demo services for RUET campus marketplace development."

    def handle(self, *args, **options):
        # Look for existing student users
        students = list(User.objects.filter(role=User.Role.STUDENT).order_by('id'))
        if not students:
            self.stdout.write(self.style.WARNING("No student users found. Creating a demo student..."))
            demo_student = User.objects.create_user(
                username='demostudent',
                email='demostudent@ruet.ac.bd',
                password='Password123!',
                role=User.Role.STUDENT,
                bio='3rd year CSE student at RUET. Hardware enthusiast and designer.'
            )
            students = [demo_student]

        student_1 = students[0]
        student_2 = students[1] if len(students) > 1 else student_1
        student_3 = students[2] if len(students) > 2 else student_1

        sample_services = [
            {
                'creator': student_1,
                'title': 'Professional Event Poster Design for RUET Clubs',
                'description': (
                    "I will design modern, high-resolution promotional posters and social media banners "
                    "for RUET club events, tech fests, seminars, and workshop announcements. "
                    "Includes 2 revisions, source files (PSD/Figma), and export formats optimized for Facebook and print."
                ),
                'category': Service.Category.GRAPHIC_DESIGN,
                'skills': 'Figma, Adobe Illustrator, Photoshop, Print Design',
                'delivery_time_days': 2,
                'price_estimate': Decimal('20.00'),
                'is_active': True,
            },
            {
                'creator': student_2,
                'title': 'ESP32 & Arduino Hardware Prototyping & Debugging',
                'description': (
                    "I will assist with circuit schematic design, PCB layout review, and microcontroller firmware "
                    "for term projects and robotics competitions. Specializing in sensor interfacing (I2C, SPI), "
                    "Wi-Fi/Bluetooth telemetry, and power regulation."
                ),
                'category': Service.Category.EMBEDDED,
                'skills': 'ESP32, Arduino, C++, KiCAD, Sensor Interfacing',
                'delivery_time_days': 4,
                'price_estimate': Decimal('45.00'),
                'is_active': True,
            },
            {
                'creator': student_1,
                'title': 'Full-Stack Django & REST API Web Application',
                'description': (
                    "I will build or refactor clean, responsive web applications using Django, SQLite/PostgreSQL, "
                    "and modern vanilla CSS. Suitable for university lab projects, club management portals, or research tools."
                ),
                'category': Service.Category.WEB_DEV,
                'skills': 'Python, Django, PostgreSQL, Bootstrap 5, JavaScript',
                'delivery_time_days': 7,
                'price_estimate': Decimal('80.00'),
                'is_active': True,
            },
            {
                'creator': student_3,
                'title': '3D CAD Modeling & Simulation for Engineering Projects',
                'description': (
                    "Assistance with SolidWorks and Fusion 360 parametric 3D modeling, stress analysis, and STL preparation "
                    "for 3D printing. Ideal for ME, MTE, and EEE project chassis, robotic arms, and mechanical enclosures."
                ),
                'category': Service.Category.CAD_ENGINEERING,
                'skills': 'SolidWorks, Fusion 360, 3D Printing, Simulation',
                'delivery_time_days': 5,
                'price_estimate': Decimal('35.00'),
                'is_active': True,
            },
            {
                'creator': student_2,
                'title': 'Figma Mobile App Wireframing & Interactive Prototyping',
                'description': (
                    "Need a clean UI/UX before writing code? I will design interactive user flow prototypes and wireframes "
                    "with responsive mobile design systems and reusable components."
                ),
                'category': Service.Category.UI_UX,
                'skills': 'Figma, UI/UX, Wireframing, User Flows',
                'delivery_time_days': 3,
                'price_estimate': Decimal('30.00'),
                'is_active': True,
            },
        ]

        created_count = 0
        for data in sample_services:
            svc, created = Service.objects.get_or_create(
                title=data['title'],
                defaults=data
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully seeded {created_count} demo services into CRAFT marketplace.")
        )
