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
    MAX_UPLOAD_SIZE = 3 * 1024 * 1024  # 3 MB
    ALLOWED_IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp')

    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
            'email',
            'department',
            'student_id',
            'bio',
            'skills',
            'company_name',
            'website_url',
            'portfolio_url',
            'github_url',
            'linkedin_url',
            'profile_picture',
        )
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'profile_picture':
                field.widget.attrs.setdefault('class', 'form-control')
                field.widget.attrs.setdefault('accept', 'image/png, image/jpeg, image/webp')
            else:
                field.widget.attrs.setdefault('class', 'form-control')

        user = self.instance
        if user and user.pk:
            if user.is_client:
                # Remove student-specific fields
                self.fields.pop('skills', None)
                self.fields.pop('student_id', None)
            elif user.is_student:
                # Remove client-specific fields
                self.fields.pop('company_name', None)
                self.fields.pop('website_url', None)

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        user = self.instance
        if user and user.pk and user.is_student:
            if email != (user.email or '').strip().lower():
                if not email or not re.fullmatch(r'[0-9]{7}@student\.ruet\.ac\.bd', email, re.IGNORECASE):
                    raise ValidationError(
                        'Student accounts require a valid RUET student email in the '
                        'format XXXXXXX@student.ruet.ac.bd.'
                    )
        # Check uniqueness against other users
        if email and User.objects.exclude(pk=user.pk).filter(email__iexact=email).exists():
            raise ValidationError('A user with this email address already exists.')
        return email

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')
        if picture and hasattr(picture, 'size'):
            if picture.size > self.MAX_UPLOAD_SIZE:
                raise ValidationError("Profile picture file size cannot exceed 3MB.")
            name = picture.name.lower()
            if not any(name.endswith(ext) for ext in self.ALLOWED_IMAGE_EXTENSIONS):
                raise ValidationError(
                    f"Unsupported image format. Allowed formats: {', '.join(self.ALLOWED_IMAGE_EXTENSIONS)}."
                )
        return picture


class ReviewForm(forms.ModelForm):
    RATING_CHOICES = (
        (5, '★★★★★ (5 Stars - Exceptional)'),
        (4, '★★★★☆ (4 Stars - Very Good)'),
        (3, '★★★☆☆ (3 Stars - Satisfactory)'),
        (2, '★★☆☆☆ (2 Stars - Needs Improvement)'),
        (1, '★☆☆☆☆ (1 Star - Poor)'),
    )

    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Rate your collaboration experience from 1 to 5 stars."
    )

    class Meta:
        from .models import Review
        model = Review
        fields = ('rating', 'comment')
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your experience collaborating on this project, work quality, communication, and professionalism...'
            }),
        }

    def clean_rating(self):
        val = self.cleaned_data.get('rating')
        try:
            rating = int(val)
        except (ValueError, TypeError):
            raise ValidationError("Please provide a valid numeric rating between 1 and 5.")
        if rating < 1 or rating > 5:
            raise ValidationError("Rating must be between 1 and 5 stars.")
        return rating

    def clean_comment(self):
        comment = self.cleaned_data.get('comment', '').strip()
        if not comment:
            raise ValidationError("Review comment cannot be blank.")
        return comment
