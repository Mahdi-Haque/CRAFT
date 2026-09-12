/**
 * CRAFT — Campus Resource And Freelance Talent
 * Shared Frontend JavaScript Utilities (Vanilla JS)
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Auto-dismiss alerts after 5 seconds (except danger/critical errors)
    const alerts = document.querySelectorAll('.alert:not(.alert-danger)');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 300ms ease, transform 300ms ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-6px)';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });

    // 2. Dynamic Role Selector on Registration Page
    const roleInputs = document.querySelectorAll('input[name="role"]');
    const skillsGroup = document.getElementById('student-skills-group');
    const companyGroup = document.getElementById('client-company-group');

    function updateRoleVisibility() {
        const checkedRole = document.querySelector('input[name="role"]:checked');
        if (!checkedRole) return;

        const role = checkedRole.value;
        const roleBoxes = document.querySelectorAll('.cw-role-select-box');
        
        roleBoxes.forEach(box => {
            const radio = box.querySelector('input[type="radio"]');
            if (radio && radio.checked) {
                box.classList.add('active');
            } else {
                box.classList.remove('active');
            }
        });

        if (skillsGroup && companyGroup) {
            if (role === 'student') {
                skillsGroup.style.display = 'block';
                companyGroup.style.display = 'none';
                const compInput = companyGroup.querySelector('input');
                if (compInput) compInput.value = '';
            } else if (role === 'client') {
                skillsGroup.style.display = 'none';
                companyGroup.style.display = 'block';
            }
        }
    }

    if (roleInputs.length > 0) {
        roleInputs.forEach(input => input.addEventListener('change', updateRoleVisibility));
        updateRoleVisibility(); // Run on initial load
    }

    // 3. Prevent duplicate form submissions on primary action buttons
    const forms = document.querySelectorAll('form:not([data-no-disable])');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !form.dataset.submitted) {
                form.dataset.submitted = 'true';
                submitBtn.dataset.originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = `
                    <span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
                    Processing...
                `;
                submitBtn.disabled = true;
                // Allow form submit to proceed
            }
        });
    });

    // 4. Client-side Instant Filter for Projects / Cards (if input with data-filter-target exists)
    const filterInput = document.querySelector('[data-card-filter]');
    if (filterInput) {
        const targetSelector = filterInput.getAttribute('data-card-filter');
        filterInput.addEventListener('input', (e) => {
            const term = e.target.value.toLowerCase().trim();
            const items = document.querySelectorAll(targetSelector);
            let visibleCount = 0;

            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                const matches = text.includes(term);
                item.style.display = matches ? '' : 'none';
                if (matches) visibleCount++;
            });

            const emptyNotice = document.getElementById('filter-empty-state');
            if (emptyNotice) {
                emptyNotice.style.display = (visibleCount === 0 && term !== '') ? 'block' : 'none';
            }
        });
    }

    // 5. Delete Action Confirmation Dialog
    const deleteForms = document.querySelectorAll('form[data-confirm]');
    deleteForms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const message = form.getAttribute('data-confirm') || 'Are you sure you want to proceed?';
            if (!confirm(message)) {
                e.preventDefault();
                const btn = form.querySelector('button[type="submit"]');
                if (btn) btn.disabled = false;
                delete form.dataset.submitted;
            }
        });
    });
});
