from rest_framework.authentication import SessionAuthentication


class CsrfEnforcedSessionAuthentication(SessionAuthentication):
    """DRF's SessionAuthentication only checks CSRF for logged-in users.
    Login/register are unauthenticated POSTs, so we enforce CSRF for every
    unsafe request — anonymous ones included."""

    def authenticate(self, request):
        user = getattr(request._request, "user", None)
        if request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            self.enforce_csrf(request)
        if not user or not user.is_active:
            return None
        return (user, None)

    def authenticate_header(self, request):
        # Makes DRF return 401 (not 403) for unauthenticated requests.
        return 'Session realm="api"'
