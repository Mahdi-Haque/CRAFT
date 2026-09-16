import re

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError

from .models import User


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class RegisterForm(UserCreationForm):
    ROLE_CHOICES = (
        (User.Role.STUDENT, 'Student'),
        (User.Role.CLIENT, 'Client'),
    )

    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect)
    email = forms.EmailField(required=True)
    skills = forms.CharField(required=False, help_text="Comma separated, e.g. Python, Django, React")
    company_name = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'skills', 'company_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'role':
                field.widget.attrs.setdefault('class', 'form-control')

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        company_name = cleaned_data.get('company_name')
        email = cleaned_data.get('email')
        if role == User.Role.CLIENT and not company_name:
            raise ValidationError({'company_name': 'Company name is required for client accounts.'})
        if role == User.Role.STUDENT and (
            not email
            or not re.fullmatch(r'[0-9]{7}@student\.ruet\.ac\.bd', email, re.IGNORECASE)
        ):
            raise ValidationError({
                'email': (
                    'Student accounts require a valid RUET student email in the '
                    'format XXXXXXX@student.ruet.ac.bd.'
                )
            })
        return cleaned_data

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data['role']
        user.email = self.cleaned_data['email']
        user.skills = self.cleaned_data.get('skills', '')
        user.company_name = self.cleaned_data.get('company_name', '')
        if commit:
            user.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'bio', 'skills', 'company_name')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
