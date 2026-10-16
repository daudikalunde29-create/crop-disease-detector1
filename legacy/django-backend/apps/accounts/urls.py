from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="auth-register"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("session/", views.SessionView.as_view(), name="auth-session"),
    path("me/", views.MeView.as_view(), name="auth-me"),
    path("google/", views.GoogleAuthView.as_view(), name="auth-google"),
    path("google/config/", views.GoogleConfigView.as_view(), name="auth-google-config"),
    path("password-reset/", views.PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path("password-reset-confirm/", views.PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("change-password/", views.ChangePasswordView.as_view(), name="auth-change-password"),
]
