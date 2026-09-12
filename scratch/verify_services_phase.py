"""
Verification script for Contributor 1's Services Marketplace domain.
Tests all user journeys programmatically using Django's test Client.
"""
import os
import sys
import pathlib

# Setup Django environment
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jobportal.settings')

import django
django.setup()

from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from services.models import Service
from projects.models import Project
from applications.models import Application

User = get_user_model()

def run_verification():
    client = Client()
    print("=== CRAFT SERVICES DOMAIN END-TO-END VERIFICATION ===")

    # 1. Check Public Landing Page & Services Link
    res = client.get(reverse('home'))
    assert res.status_code == 200, f"Expected 200 for home, got {res.status_code}"
    assert 'Services Marketplace' in res.content.decode('utf-8')
    print(" [PASS] 1. Home page loads with Services navigation & CTA")

    # 2. Browse Public Services Marketplace
    res = client.get(reverse('services:service_list'))
    assert res.status_code == 200
    content = res.content.decode('utf-8')
    assert 'Campus Services Marketplace' in content
    assert 'Professional Event Poster Design' in content
    print(" [PASS] 2. Public marketplace lists active campus services")

    # 3. Search and Category Filtering
    res_search = client.get(reverse('services:service_list') + '?q=Poster')
    assert res_search.status_code == 200
    assert 'Professional Event Poster Design' in res_search.content.decode('utf-8')
    assert 'SolidWorks' not in res_search.content.decode('utf-8')

    res_cat = client.get(reverse('services:service_list') + f'?category={Service.Category.GRAPHIC_DESIGN}')
    assert res_cat.status_code == 200
    assert 'Professional Event Poster Design' in res_cat.content.decode('utf-8')
    print(" [PASS] 3. Keyword search and category filtering functioning cleanly")

    # 4. Open Service Detail View
    poster_service = Service.objects.filter(title__icontains='Event Poster Design').first()
    assert poster_service is not None
    res_detail = client.get(reverse('services:service_detail', kwargs={'pk': poster_service.pk}))
    assert res_detail.status_code == 200
    detail_html = res_detail.content.decode('utf-8')
    assert poster_service.title in detail_html
    assert poster_service.creator.username in detail_html
    assert 'Service Scope' in detail_html
    print(f" [PASS] 4. Service detail view loaded for ID {poster_service.pk}")

    # 5. Create a Service as firststudent
    firststudent = User.objects.get(username='firststudent')
    secondstudent = User.objects.get(username='secondstudent')
    client.force_login(firststudent)
    create_payload = {
        'title': 'E2E Testing Service: Embedded Firmware in Rust',
        'description': 'Modern zero-cost abstraction bare-metal programming for ARM Cortex microcontrollers.',
        'category': Service.Category.EMBEDDED,
        'skills': 'Rust, Embedded, ARM, Cortex-M',
        'delivery_time_days': 4,
        'price_estimate': '65.00',
        'is_active': True,
    }
    res_create = client.post(reverse('services:service_create'), create_payload)
    assert res_create.status_code == 302, f"Expected 302, got {res_create.status_code}"
    created_service = Service.objects.filter(title='E2E Testing Service: Embedded Firmware in Rust').first()
    assert created_service is not None
    assert created_service.creator.username == 'firststudent'
    print(f" [PASS] 5. Service successfully created (ID {created_service.pk}) by 'firststudent'")

    # 6. Edit Own Service
    update_payload = {
        'title': 'E2E Testing Service: Embedded Firmware in Rust (v2)',
        'description': 'Updated scope with custom bootloader.',
        'category': Service.Category.EMBEDDED,
        'skills': 'Rust, Embedded, ARM, Cortex-M, RTOS',
        'delivery_time_days': 3,
        'price_estimate': '70.00',
        'is_active': True,
    }
    res_update = client.post(reverse('services:service_update', kwargs={'pk': created_service.pk}), update_payload)
    assert res_update.status_code == 302
    created_service.refresh_from_db()
    assert created_service.title == 'E2E Testing Service: Embedded Firmware in Rust (v2)'
    assert created_service.delivery_time_days == 3
    print(" [PASS] 6. Owner can update service details successfully")

    # 7. Attempt Unauthorized Edit by secondstudent
    client.logout()
    client.force_login(secondstudent)
    res_unauth_edit = client.get(reverse('services:service_update', kwargs={'pk': created_service.pk}))
    assert res_unauth_edit.status_code == 403, f"Expected 403, got {res_unauth_edit.status_code}"
    res_unauth_post = client.post(reverse('services:service_update', kwargs={'pk': created_service.pk}), {
        'title': 'Hacked by stranger',
        'description': 'Hacked',
        'category': Service.Category.EMBEDDED,
        'delivery_time_days': 1,
    })
    assert res_unauth_post.status_code == 403
    created_service.refresh_from_db()
    assert created_service.title == 'E2E Testing Service: Embedded Firmware in Rust (v2)'
    print(" [PASS] 7. Unauthorized edit correctly blocked with HTTP 403 Forbidden")

    # 8. Attempt Unauthorized Delete by secondstudent
    res_unauth_del = client.post(reverse('services:service_delete', kwargs={'pk': created_service.pk}))
    assert res_unauth_del.status_code == 403
    assert Service.objects.filter(pk=created_service.pk).exists()
    print(" [PASS] 8. Unauthorized delete correctly blocked with HTTP 403 Forbidden")

    # 9. Toggle Availability / Activate / Deactivate by Owner
    client.logout()
    client.force_login(firststudent)
    res_toggle = client.post(reverse('services:service_toggle_active', kwargs={'pk': created_service.pk}))
    assert res_toggle.status_code == 302
    created_service.refresh_from_db()
    assert created_service.is_active is False
    print(" [PASS] 9. Owner toggled availability to Paused (is_active=False)")

    # 10. Verify Paused Service Inaccessible to Non-Owners
    client.logout()
    res_paused_anon = client.get(reverse('services:service_detail', kwargs={'pk': created_service.pk}))
    assert res_paused_anon.status_code == 302
    print(" [PASS] 10. Paused service hidden from anonymous viewers (redirected)")

    # 11. Owner Deletes Service
    client.force_login(firststudent)
    res_delete = client.post(reverse('services:service_delete', kwargs={'pk': created_service.pk}))
    assert res_delete.status_code == 302
    assert not Service.objects.filter(pk=created_service.pk).exists()
    print(" [PASS] 11. Owner successfully deleted service offering")

    # 12. Student Dashboard & Profile Integration Verification
    res_dash = client.get(reverse('accounts:dashboard'), follow=True)
    assert res_dash.status_code == 200
    dash_html = res_dash.content.decode('utf-8')
    assert 'My Offered Services' in dash_html
    assert 'Offer a Service' in dash_html

    res_prof = client.get(reverse('accounts:profile'))
    assert res_prof.status_code == 200
    prof_html = res_prof.content.decode('utf-8')
    assert 'My Services Offered' in prof_html
    print(" [PASS] 12. Services successfully integrated into Student Dashboard & Profile")

    # 13. Verify Existing Projects & Applications Functionality
    res_proj = client.get(reverse('projects:project_list'))
    assert res_proj.status_code == 200
    assert Project.objects.count() > 0
    print(f" [PASS] 13. Existing Projects ({Project.objects.count()}) and Applications ({Application.objects.count()}) intact")

    print("\n>>> ALL VERIFICATION CHECKS PASSED WITH 100% SUCCESS! <<<")

if __name__ == '__main__':
    run_verification()
