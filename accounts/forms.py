from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

# This line finds your 'CustomUser' automatically
User = get_user_model()

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User  # Now this points to accounts.CustomUser
        fields = ('username', 'email')