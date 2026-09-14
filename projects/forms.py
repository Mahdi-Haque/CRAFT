from django import forms

from .models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ('title', 'description', 'category', 'skills_required', 'budget', 'deadline', 'status')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'deadline': forms.DateInput(attrs={'type': 'date'}),
            'skills_required': forms.TextInput(attrs={
                'placeholder': 'e.g. Python, ROS, OpenCV, C++',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_status(self):
        new_status = self.cleaned_data.get('status')
        if self.instance and self.instance.pk:
            old_status = self.instance.status
            if old_status in (Project.Status.COMPLETED, Project.Status.CLOSED):
                if new_status != old_status:
                    raise forms.ValidationError(
                        f"Cannot change status of a {self.instance.get_status_display().lower()} project."
                    )
            elif old_status == Project.Status.IN_PROGRESS:
                if new_status == Project.Status.OPEN:
                    raise forms.ValidationError(
                        "An in-progress project cannot be reverted to open."
                    )
        return new_status

