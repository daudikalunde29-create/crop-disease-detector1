/* =========================================================
   google-auth.js — REAL Google Identity Services integration.
   =========================================================
   This uses Google's official Sign In With Google button.
   It is NOT a fake button and does NOT simulate anything
   with localStorage.

   FLOW (section 4 of the spec):
     User clicks "Continue with Google"
       -> Google Identity Services
       -> Google returns an ID token (credential)
       -> Frontend POSTs { credential } to /api/auth/google/
       -> Django verifies the token server-side
       -> Django finds-or-creates the user (account linking
          by verified email is a BACKEND decision)
       -> Django creates the application session
       -> Frontend redirects to the dashboard

   The Google ID token is NEVER used as the app session.

   CONFIGURATION (M4.2):
   ONE setting drives everything: GOOGLE_CLIENT_ID in backend/.env.
   The frontend asks Django for the (public) Client ID with
     GET /api/auth/google/config/  ->  { enabled, clientId }
   so the ID is never hardcoded here. For static hosting without a
   backend, an override still works: either
     <meta name="cdd-google-client-id" content="...apps.googleusercontent.com">
   or window.CDD_GOOGLE_CLIENT_ID set before this script.
   If no Client ID is configured anywhere, the Google button is shown
   as unavailable. Never put a Google client SECRET in frontend code
   or in GitHub (this flow does not need one).
   ========================================================= */

var GOOGLE_CLIENT_ID = (function () {
  if (typeof window !== "undefined" && window.CDD_GOOGLE_CLIENT_ID) {
    return String(window.CDD_GOOGLE_CLIENT_ID);
  }
  var meta = document.querySelector('meta[name="cdd-google-client-id"]');
  return meta ? meta.getAttribute("content") || "" : "";
})();

function isGoogleConfigured() {
  return /\.apps\.googleusercontent\.com$/.test(GOOGLE_CLIENT_ID);
}

/* Resolves to the Client ID ("" when Google sign-in is not configured).
   Local override first, otherwise the Django config endpoint. */
function resolveGoogleClientId() {
  if (isGoogleConfigured()) {
    return Promise.resolve(GOOGLE_CLIENT_ID);
  }
  return apiFetch("/api/auth/google/config/", { method: "GET" })
    .then(function (data) {
      GOOGLE_CLIENT_ID = (data && data.enabled && data.clientId) || "";
      return GOOGLE_CLIENT_ID;
    })
    .catch(function () {
      return "";
    });
}

/* Called by Google with the verified ID token. */
function handleGoogleCredential(response) {
  hideError("login-error");
  hideError("register-error");
  authGoogle(response.credential)
    .then(function () {
      window.location.href = "dashboard.html";
    })
    .catch(function (error) {
      showError("login-error", authErrorMessage(error));
      showError("register-error", authErrorMessage(error));
    });
}

function showGoogleUnavailable(containers) {
  /* Honest placeholder: no Client ID configured on the server. No fake login. */
  for (var i = 0; i < containers.length; i++) {
    containers[i].innerHTML =
      '<button type="button" class="btn btn-outline-green w-100" disabled>' +
      '<i class="bi bi-google me-2" aria-hidden="true"></i>' +
      '<span data-i18n="googleNeedsSetup">Continue with Google (needs backend setup)</span>' +
      "</button>";
  }
  applyLanguage();
}

function initGoogleSignIn() {
  var containers = document.querySelectorAll("[data-google-button]");
  if (!containers.length) {
    return;
  }

  resolveGoogleClientId().then(function (clientId) {
    if (!clientId) {
      showGoogleUnavailable(containers);
      return;
    }

    /* Load the official Google Identity Services script. */
    var script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = function () {
      /* global google */
      google.accounts.id.initialize({
        client_id: clientId,
        callback: handleGoogleCredential,
        cancel_on_tap_outside: true,
      });
      for (var i = 0; i < containers.length; i++) {
        google.accounts.id.renderButton(containers[i], {
          type: "standard",
          theme: "outline",
          size: "large",
          width: containers[i].offsetWidth || 320,
          text: "continue_with",
        });
      }
      /* Google One Tap stays disabled: sign-in only happens when the
         user clicks the button. */
      // google.accounts.id.prompt();
    };
    script.onerror = function () {
      showError("login-error", "Google sign-in could not be loaded. Please check your connection.");
      showError(
        "register-error",
        "Google sign-in could not be loaded. Please check your connection.",
      );
    };
    document.head.appendChild(script);
  });
}

document.addEventListener("DOMContentLoaded", initGoogleSignIn);
