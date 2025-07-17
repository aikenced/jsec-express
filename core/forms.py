from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser
from datetime import datetime, timedelta

class CustomAdminLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Admin Username",
        widget=forms.TextInput(attrs={"autofocus": True})
    )

class SignUpForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('student_id', 'full_name', 'contact_number', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and not email.endswith("@student.ateneo.edu"):
            raise forms.ValidationError("Must be a @student.ateneo.edu email.")
        return email

class CheckoutForm(forms.Form):
    pickup_time = forms.ChoiceField(choices=[], label="Pickup Time")

    def __init__(self, *args, **kwargs):
        pickup_options = kwargs.pop('pickup_options', [])
        super().__init__(*args, **kwargs)
        self.fields['pickup_time'].choices = pickup_options
