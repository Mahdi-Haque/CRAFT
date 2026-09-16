from django import forms
from django.contrib.auth import get_user_model
from .models import Message

User = get_user_model()


class MessageForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Type your message here...',
            'aria-label': 'Message content',
        }),
        max_length=5000,
        required=True,
    )

    class Meta:
        model = Message
        fields = ['content']

    def clean_content(self):
        content = self.cleaned_data.get('content', '').strip()
        if not content:
            raise forms.ValidationError("Message content cannot be blank.")
        return content


class StartConversationForm(forms.Form):
    recipient = forms.ModelChoiceField(
        queryset=User.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="-- Select recipient --",
        required=True,
    )

    def __init__(self, *args, current_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = User.objects.filter(is_active=True).order_by('username')
        if current_user and current_user.is_authenticated:
            qs = qs.exclude(pk=current_user.pk)
        self.fields['recipient'].queryset = qs
        self.fields['recipient'].label_from_instance = (
            lambda u: f"{u.username} ({u.role.capitalize() if hasattr(u, 'role') else 'User'})"
        )

