from django import forms
from django.contrib.auth import get_user_model


User = get_user_model()


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'gender')
        widgets = {
            # the radios are hidden, their labels make a segmented control
            'gender': forms.RadioSelect(attrs={'class': 'sr-only'}),
        }
