from django import forms
from .models import Service


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = (
            'title',
            'category',
            'skills',
            'delivery_time_days',
            'price_estimate',
            'description',
            'is_active',
        )
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'e.g. I will design high-impact posters for your RUET club event'
            }),
            'description': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Describe what you will provide, your tools/experience, and expected turnaround...'
            }),
            'skills': forms.TextInput(attrs={
                'placeholder': 'e.g. Photoshop, Illustrator, Figma, Print Design'
            }),
            'delivery_time_days': forms.NumberInput(attrs={
                'min': 1,
                'max': 365,
                'placeholder': '3'
            }),
            'price_estimate': forms.NumberInput(attrs={
                'min': 0,
                'step': '0.01',
                'placeholder': 'e.g. 2500.00'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'is_active':
                field.widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', 'form-select')
            else:
                field.widget.attrs.setdefault('class', 'form-control')
