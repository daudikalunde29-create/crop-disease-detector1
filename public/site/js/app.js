/* =========================================================
   app.js — shared behaviour for every page
   Vanilla JavaScript only.
   ========================================================= */

/* ---------------------------------------------------------
   1. App configuration
   Language support lives in js/language.js (load it first).
   LOW_CONFIDENCE_THRESHOLD: predictions below this % are NOT
   shown as a diagnosis. Placeholder value — to be tuned once the
   real TensorFlow model is evaluated.
   --------------------------------------------------------- */
var CDD_CONFIG = {
  LOW_CONFIDENCE_THRESHOLD: 60,
};

/* STAGE STATUS (M3):
     AUTHENTICATION = real Django API contract (js/auth.js), no mock auth
     SCAN AI        = not implemented yet (M6–M8)
     DEMO DATA      = data/mock-*.json, UI preview only (history, dashboard,
                      admin lists, result preview) — clearly labelled */

/* ---------------------------------------------------------
   2. Session
   Real session handling lives in js/session.js (protected
   pages, logout, navigation state). The helpers below are
   kept for backwards compatibility with existing pages.
   --------------------------------------------------------- */
/* Returns the session-verified user (set by authCheckSession),
   never the localStorage cache. */
function getCurrentUser() {
  return typeof Auth !== "undefined" && Auth.user ? Auth.user : null;
}

/* Used by the landing page "Scan Your Crop" button. */
function goToScan(pathPrefix) {
  var prefix = pathPrefix || "";
  authCheckSession()
    .then(function (user) {
      window.location.href = user ? prefix + "scan.html" : prefix + "login.html";
    })
    .catch(function () {
      window.location.href = prefix + "login.html";
    });
}

/* Redirect guests away from farmer pages (frontend-only guard).
   Returns a Promise resolving to the user or null. */
function requireLogin() {
  return requireAuth();
}

/* ---------------------------------------------------------
   3. Helpers
   --------------------------------------------------------- */
function loadJSON(url) {
  // FUTURE DJANGO API
  // Replace the mock file with a real endpoint, e.g. fetch('/api/history/')
  return fetch(url).then(function (response) {
    if (!response.ok) {
      throw new Error("Could not load " + url);
    }
    return response.json();
  });
}

function statusBadge(status) {
  if (status === "healthy") {
    return '<span class="badge badge-healthy">Healthy</span>';
  }
  if (status === "low") {
    return '<span class="badge badge-low">Low confidence</span>';
  }
  return '<span class="badge badge-disease">Disease</span>';
}

/* ---------------------------------------------------------
   4. Boot
   --------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", function () {
  applyLanguage();

  var langButtons = document.querySelectorAll("[data-lang]");
  for (var i = 0; i < langButtons.length; i++) {
    langButtons[i].addEventListener("click", function () {
      setLanguage(this.getAttribute("data-lang"));
    });
  }

  /* Logout buttons are wired in js/session.js. */
});
