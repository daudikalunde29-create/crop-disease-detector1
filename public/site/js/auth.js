/* =========================================================
   auth.js — centralized authentication helper.

   APPLICATION ARCHITECTURE (Django + SQLite for M4.x; MySQL planned for M5):
   Functions below call the real Django endpoints currently implemented.
   There is NO mock authentication: every call hits Django.
   Until the Django endpoints exist, calls fail with a clear
   "backend unavailable" error instead of faking success.

   API CONTRACT (JSON request/response):
     POST /api/auth/register/                { fullName, email, phone, password }
     POST /api/auth/login/                   { email, password, remember }
     POST /api/auth/google/                  { credential: "GOOGLE_ID_TOKEN" }
     POST /api/auth/logout/
     GET  /api/auth/session/                 -> { authenticated, user }
     POST /api/auth/password-reset/          { email }
     POST /api/auth/password-reset-confirm/  { token, password }
     POST /api/auth/change-password/         { currentPassword, newPassword }
     GET  /api/auth/me/                      -> { user }

   Authenticated user shape:
     { id, name, email, phone, role: "farmer"|"admin",
       provider: "email"|"google", createdAt }

   SECURITY RULES (enforced here):
     - Passwords are NEVER stored in localStorage/JSON/variables.
     - No fake session tokens: the session is a Django cookie.
     - Role/authorization decisions belong to the backend.
   ========================================================= */

/* ---------------------------------------------------------
   1. Authentication states (section 7 of the spec)
   --------------------------------------------------------- */
var AuthState = {
  UNAUTHENTICATED: "UNAUTHENTICATED",
  AUTHENTICATING: "AUTHENTICATING",
  AUTHENTICATED: "AUTHENTICATED",
  SESSION_EXPIRED: "SESSION_EXPIRED",
  LOGGING_OUT: "LOGGING_OUT",
  AUTH_ERROR: "AUTH_ERROR",
};

var Auth = {
  state: AuthState.UNAUTHENTICATED,
  user: null,
};

/* ---------------------------------------------------------
   2. CSRF-ready fetch wrapper (section 19)
   Reads Django's csrftoken cookie and sends it as
   X-CSRFToken. Credentials are always included so the
   Django session cookie travels with every request.
   --------------------------------------------------------- */
function getCsrfToken() {
  var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

function apiFetch(url, options) {
  var opts = Object.assign({}, options || {});
  var method = String(opts.method || "GET").toUpperCase();
  opts.method = method;
  opts.credentials = "same-origin";
  opts.headers = Object.assign({}, opts.headers || {});

  if (opts.body && typeof opts.body !== "string") {
    opts.body = JSON.stringify(opts.body);
  }

  function sendRequest() {
    opts.headers["Content-Type"] = opts.headers["Content-Type"] || "application/json";
    var csrf = getCsrfToken();
    if (method !== "GET" && method !== "HEAD" && method !== "OPTIONS" && csrf) {
      opts.headers["X-CSRFToken"] = csrf;
    }
    return fetch(AUTH_API_BASE + url, opts);
  }

  /* Login/register/forgot-password pages do not always render a public
     navbar that triggers the session check. Ensure Django has issued its
     CSRF cookie before the first unsafe request (POST/PUT/PATCH/DELETE). */
  var needsCsrf = method !== "GET" && method !== "HEAD" && method !== "OPTIONS" && !getCsrfToken();
  var prepare = needsCsrf
    ? fetch(AUTH_API_BASE + "/api/auth/session/", { method: "GET", credentials: "same-origin" })
        .then(function (response) {
          if (!response.ok) {
            throw new Error("Could not initialize the security session.");
          }
        })
    : Promise.resolve();

  return prepare
    .then(sendRequest)
    .catch(function (error) {
      if (error instanceof AuthError) throw error;
      throw new AuthError(
        "NETWORK_ERROR",
        "Cannot reach the authentication server. Check that Django is running at 127.0.0.1:8000.",
      );
    })
    .then(function (response) {
      if (response.status === 401) {
        clearSessionCache();
        Auth.state = AuthState.SESSION_EXPIRED;
        throw new AuthError("SESSION_EXPIRED", "Your session has expired. Please log in again.");
      }
      return response.json().catch(function () {
        throw new AuthError(
          "BACKEND_UNAVAILABLE",
          "The server returned an unreadable response. Check the Django terminal for errors.",
        );
      }).then(function (data) {
        if (!response.ok) {
          throw new AuthError(data.code || "AUTH_ERROR", data.message || "Unable to connect to the server.");
        }
        return data;
      });
    });
}

function AuthError(code, message) {
  this.code = code;
  this.message = message;
}

/* ---------------------------------------------------------
   3. Backend configuration (Django only — no mock auth)
   --------------------------------------------------------- */
/* All auth traffic goes to the real Django backend. Change the
   base URL here (or set window.CDD_API_BASE before this script). */
var AUTH_API_BASE = (typeof window !== "undefined" && window.CDD_API_BASE) || "";

/* ---------------------------------------------------------
   4. Public authentication API
   Each function returns a Promise resolving to the user
   object (or a status object for password flows).
   --------------------------------------------------------- */

function authRegister(input) {
  Auth.state = AuthState.AUTHENTICATING;
  return apiFetch("/api/auth/register/", { method: "POST", body: input })
    .then(function (data) {
      return afterAuthSuccess(data.user);
    })
    .catch(afterAuthError);
}

function authLogin(email, password, remember) {
  Auth.state = AuthState.AUTHENTICATING;
  return apiFetch("/api/auth/login/", {
    method: "POST",
    body: { email: email, password: password, remember: !!remember },
  })
    .then(function (data) {
      return afterAuthSuccess(data.user);
    })
    .catch(afterAuthError);
}

/* Google: the ID token from Google Identity Services is sent
   to Django for server-side verification. It is NEVER used
   as the application session itself. */
function authGoogle(credential) {
  Auth.state = AuthState.AUTHENTICATING;
  return apiFetch("/api/auth/google/", { method: "POST", body: { credential: credential } })
    .then(function (data) {
      return afterAuthSuccess(data.user);
    })
    .catch(afterAuthError);
}

function authLogout() {
  Auth.state = AuthState.LOGGING_OUT;
  var done = function () {
    Auth.state = AuthState.UNAUTHENTICATED;
    Auth.user = null;
    clearSessionCache();
  };
  return apiFetch("/api/auth/logout/", { method: "POST" }).then(done).catch(done);
}

/* Session verification — used by protected pages. */
function authCheckSession() {
  return apiFetch("/api/auth/session/", { method: "GET" }).then(function (data) {
    if (data.authenticated) {
      Auth.state = AuthState.AUTHENTICATED;
      Auth.user = data.user;
      cacheSessionUser(data.user);
      return data.user;
    }
    /* Backend says logged out: stale cache is discarded. */
    Auth.state = AuthState.UNAUTHENTICATED;
    Auth.user = null;
    clearSessionCache();
    return null;
  });
}

function authRequestPasswordReset(email) {
  return apiFetch("/api/auth/password-reset/", { method: "POST", body: { email: email } });
}

function authConfirmPasswordReset(token, password) {
  return apiFetch("/api/auth/password-reset-confirm/", {
    method: "POST",
    body: { token: token, password: password },
  });
}

function authChangePassword(currentPassword, newPassword) {
  return apiFetch("/api/auth/change-password/", {
    method: "POST",
    body: { currentPassword: currentPassword, newPassword: newPassword },
  });
}

function authUpdateProfile(fullName, phone) {
  return apiFetch("/api/profile/", {
    method: "PUT",
    body: { fullName: fullName, phone: phone },
  }).then(function (data) {
    if (data.user) {
      Auth.user = data.user;
      cacheSessionUser(data.user);
    }
    return data.user;
  });
}

/* ---------------------------------------------------------
   5. Session cache (non-sensitive UI state only)
   --------------------------------------------------------- */
/* localStorage.cdd_user is a UI cache ONLY (e.g. show a name
   before the session check returns). It is NEVER proof of
   authentication — GET /api/auth/session/ is the source of truth.
   Only non-sensitive fields are stored: no password, token or
   Google credential. */
function cacheSessionUser(user) {
  if (!user) {
    clearSessionCache();
    return;
  }
  var safe = {
    id: user.id,
    name: user.name || user.fullName,
    email: user.email,
    role: user.role,
    provider: user.provider,
  };
  localStorage.setItem("cdd_user", JSON.stringify(safe));
}

function clearSessionCache() {
  localStorage.removeItem("cdd_user");
}

function afterAuthSuccess(user) {
  Auth.state = AuthState.AUTHENTICATED;
  Auth.user = user;
  cacheSessionUser(user);
  return user;
}

function afterAuthError(error) {
  Auth.state = AuthState.AUTH_ERROR;
  throw error;
}

/* ---------------------------------------------------------
   6. Validation helpers (shared by all auth pages)
   --------------------------------------------------------- */
function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function isValidPhone(value) {
  return /^[0-9+\s-]{9,15}$/.test(value);
}

/* Minimum strength: 8+ chars, at least one letter and one digit. */
function passwordStrengthError(password) {
  if (password.length < 8) {
    return "Password must be at least 8 characters.";
  }
  if (!/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) {
    return "Password must contain at least one letter and one number.";
  }
  return null;
}

/* ---------------------------------------------------------
   7. UI helpers: loading state, errors, success
   --------------------------------------------------------- */
function setButtonLoading(button, isLoading, loadingText) {
  if (!button) {
    return;
  }
  if (isLoading) {
    button.dataset.originalText = button.textContent;
    button.disabled = true;
    button.innerHTML =
      '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>' +
      (loadingText || "Please wait…");
  } else {
    button.disabled = false;
    button.textContent = button.dataset.originalText || button.textContent;
  }
}

function showError(id, message) {
  var box = document.getElementById(id);
  if (box) {
    box.textContent = message;
    box.classList.remove("d-none");
    box.setAttribute("role", "alert");
  }
}

function hideError(id) {
  var box = document.getElementById(id);
  if (box) {
    box.classList.add("d-none");
  }
}

function showSuccess(id, message) {
  var box = document.getElementById(id);
  if (box) {
    box.textContent = message;
    box.classList.remove("d-none");
    box.setAttribute("role", "status");
  }
}

/* Password visibility toggle — accessible. */
function initPasswordToggles() {
  var toggles = document.querySelectorAll("[data-toggle-password]");
  for (var i = 0; i < toggles.length; i++) {
    toggles[i].addEventListener("click", function () {
      var input = document.getElementById(this.getAttribute("data-toggle-password"));
      if (!input) {
        return;
      }
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      this.setAttribute("aria-label", show ? "Hide password" : "Show password");
      this.innerHTML = show
        ? '<i class="bi bi-eye-slash" aria-hidden="true"></i>'
        : '<i class="bi bi-eye" aria-hidden="true"></i>';
    });
  }
}

/* Human-readable message for an AuthError. */
function authErrorMessage(error) {
  if (error && error.message) {
    return error.message;
  }
  return "Unable to connect to the server.";
}

document.addEventListener("DOMContentLoaded", initPasswordToggles);
