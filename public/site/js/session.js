/* =========================================================
   session.js — session state, protected pages, navigation.
   Load AFTER app.js, and auth.js.

   Frontend protection is UX only. The Django backend is the
   real security layer and must enforce authentication and
   authorization on every request.
   ========================================================= */

/* ---------------------------------------------------------
   1. Protected pages (section 8)
   If no valid session exists, redirect to login with a
   message instead of just hiding content.
   --------------------------------------------------------- */
function requireAuth() {
  return authCheckSession()
    .then(function (user) {
      if (!user) {
        redirectToLogin(
          Auth.state === AuthState.SESSION_EXPIRED
            ? "Your session has expired. Please log in again."
            : "Please log in to continue.",
        );
        return null;
      }
      return user;
    })
    .catch(function (error) {
      /* Backend unreachable or session invalid: never show protected content. */
      redirectToLogin(error && error.message ? error.message : "Please log in to continue.");
      return null;
    });
}

function redirectToLogin(message) {
  if (message) {
    sessionStorage.setItem("cdd_login_notice", message);
  }
  window.location.href = "login.html";
}

/* Show a pending notice (e.g. expired session) on login page. */
function consumeLoginNotice() {
  var notice = sessionStorage.getItem("cdd_login_notice");
  if (notice) {
    sessionStorage.removeItem("cdd_login_notice");
    showError("login-error", notice);
  }
}

/* ---------------------------------------------------------
   2. Admin protection (section 17)
   UX gate only — Django must re-check the role server-side.
   --------------------------------------------------------- */
function requireAdmin() {
  return requireAuth().then(function (user) {
    if (user && user.role !== "admin") {
      window.location.href = "dashboard.html";
      return null;
    }
    return user;
  });
}

/* ---------------------------------------------------------
   3. Logout (section 9)
   Calls the backend endpoint, clears cached UI state and
   redirects. After logout, protected pages stay inaccessible
   even via the back button because they re-check the session.
   --------------------------------------------------------- */
function performLogout() {
  authLogout().then(function () {
    var inPages = window.location.pathname.indexOf("/pages/") !== -1;
    window.location.href = inPages ? "../index.html" : "index.html";
  });
}

/* ---------------------------------------------------------
   4. Navigation state (section 23)
   Elements tagged data-auth="guest" show only when logged out,
   data-auth="user" only when logged in, data-auth="admin"
   only for admins. Public pages update their navbar after the
   session check resolves.
   --------------------------------------------------------- */
function applyNavState(user) {
  var guests = document.querySelectorAll('[data-auth="guest"]');
  var users = document.querySelectorAll('[data-auth="user"]');
  var admins = document.querySelectorAll('[data-auth="admin"]');
  var i;
  for (i = 0; i < guests.length; i++) {
    guests[i].classList.toggle("d-none", !!user);
  }
  for (i = 0; i < users.length; i++) {
    users[i].classList.toggle("d-none", !user);
  }
  for (i = 0; i < admins.length; i++) {
    admins[i].classList.toggle("d-none", !(user && user.role === "admin"));
  }
}

document.addEventListener("DOMContentLoaded", function () {
  /* Update navbar state on public pages. */
  if (document.querySelector("[data-auth]")) {
    authCheckSession()
      .then(applyNavState)
      .catch(function () {
        /* Backend unreachable: show the guest navigation. */
        applyNavState(null);
      });
  }

  /* Wire all logout links/buttons. */
  var logoutButtons = document.querySelectorAll("[data-action='logout']");
  for (var i = 0; i < logoutButtons.length; i++) {
    logoutButtons[i].addEventListener("click", function (event) {
      event.preventDefault();
      performLogout();
    });
  }
});
