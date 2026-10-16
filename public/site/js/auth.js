/* =========================================================
   auth.js — centralized authentication helper.

   APPLICATION ARCHITECTURE: Lovable Cloud (auth + database + storage).
   The previous Django contract is kept below for reference only.
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
   2. Lovable Cloud bridge
   All calls go to Lovable Cloud via window.CDDCloud
   (js/cloud.bundle.js, built from src/cloud-bridge/entry.ts).
   Sessions are real Cloud Auth sessions; passwords are hashed
   server-side and never stored in the browser.
   --------------------------------------------------------- */
function AuthError(code, message) {
  this.code = code;
  this.message = message;
}

var cloudReady = new Promise(function (resolve) {
  if (window.CDDCloud) return resolve(window.CDDCloud);
  window.addEventListener("cdd-cloud-ready", function () { resolve(window.CDDCloud); });
  setTimeout(function () { if (!window.CDDCloud) resolve(null); }, 8000);
});

function cloud(method) {
  var args = Array.prototype.slice.call(arguments, 1);
  return cloudReady.then(function (c) {
    if (!c) throw new AuthError("BACKEND_UNAVAILABLE", "The app could not connect to its server. Please reload the page.");
    return c[method].apply(c, args);
  }).catch(function (err) {
    if (err instanceof AuthError) throw err;
    if (err && err.code === "SESSION_EXPIRED") {
      clearSessionCache();
      Auth.state = AuthState.SESSION_EXPIRED;
    }
    throw new AuthError((err && err.code) || "AUTH_ERROR", (err && err.message) || "Something went wrong. Please try again.");
  });
}

/* Kept for pages that read it; Cloud requests do not need CSRF tokens
   because they authenticate with a bearer token, not cookies. */
function getCsrfToken() { return ""; }

/* ---------------------------------------------------------
   4. Public authentication API
   --------------------------------------------------------- */
/* Registration policy: Cloud sends a confirmation email; the user
   confirms, then logs in. Resolves { needsConfirmation, user }. */
function authRegister(input) {
  Auth.state = AuthState.AUTHENTICATING;
  return cloud("register", input).then(function (res) {
    if (res.user) afterAuthSuccess(res.user);
    else Auth.state = AuthState.UNAUTHENTICATED;
    return res;
  }).catch(afterAuthError);
}

function authLogin(email, password) {
  Auth.state = AuthState.AUTHENTICATING;
  return cloud("login", email, password).then(afterAuthSuccess).catch(afterAuthError);
}

function authGoogle() {
  Auth.state = AuthState.AUTHENTICATING;
  return cloud("google").then(function (res) {
    if (res.user) afterAuthSuccess(res.user);
    return res;
  }).catch(afterAuthError);
}

function authLogout() {
  Auth.state = AuthState.LOGGING_OUT;
  var done = function () {
    Auth.state = AuthState.UNAUTHENTICATED;
    Auth.user = null;
    clearSessionCache();
  };
  return cloud("logout").then(done).catch(done);
}

function authCheckSession() {
  return cloud("session").then(function (user) {
    if (user) {
      Auth.state = AuthState.AUTHENTICATED;
      Auth.user = user;
      cacheSessionUser(user);
      return user;
    }
    Auth.state = AuthState.UNAUTHENTICATED;
    Auth.user = null;
    clearSessionCache();
    return null;
  });
}

function authRequestPasswordReset(email) {
  return cloud("requestPasswordReset", email);
}

function authConfirmPasswordReset(password) {
  return cloud("confirmPasswordReset", password);
}

function authChangePassword(currentPassword, newPassword) {
  return cloud("changePassword", currentPassword, newPassword);
}

function authUpdateProfile(fullName, phone) {
  return cloud("updateProfile", fullName, phone).then(function (user) {
    if (user) {
      Auth.user = user;
      cacheSessionUser(user);
    }
    return user;
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
