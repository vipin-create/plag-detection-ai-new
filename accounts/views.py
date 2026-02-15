from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.views.generic import CreateView, TemplateView
from django.urls import reverse_lazy
from .forms import SignUpForm

class SignUpView(CreateView):
    form_class = SignUpForm
    success_url = reverse_lazy('dashboard')  # <--- FIXED HERE
    template_name = 'accounts/signup.html'

    def form_valid(self, form):
        # Save the user and log them in immediately
        user = form.save()
        login(self.request, user)
        return redirect('dashboard')  # <--- FIXED HERE

class ProfileView(TemplateView):
    template_name = 'accounts/profile.html'