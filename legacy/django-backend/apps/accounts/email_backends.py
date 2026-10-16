"""Development email backend.

Django's stock console backend prints the raw MIME message. For long lines (our reset
link) that output is quoted-printable encoded - `=3D` for "=", soft line breaks ending
in "=" - so a link copied from the terminal is corrupted. This backend prints the
decoded message instead, so the reset link/code can be copied verbatim.

NOTHING is delivered to a real inbox. It is the default only when DJANGO_DEBUG=True;
production must configure SMTP (see backend/.env.example).
"""
import sys
import threading

from django.core.mail.backends.base import BaseEmailBackend


class ReadableConsoleEmailBackend(BaseEmailBackend):
    def __init__(self, *args, stream=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.stream = stream or sys.stdout
        self._lock = threading.RLock()

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        bar = "=" * 72
        with self._lock:
            for message in email_messages:
                self.stream.write(
                    f"\n{bar}\nDEV EMAIL - printed here, NOT delivered to any inbox\n"
                    f"From:    {message.from_email}\nTo:      {', '.join(message.to)}\n"
                    f"Subject: {message.subject}\n{'-' * 72}\n{message.body}\n{bar}\n"
                )
            self.stream.flush()
        return len(email_messages)
