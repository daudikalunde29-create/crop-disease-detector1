/* =========================================================
   google-auth.js — Google sign-in through Lovable Cloud.
   The Google token is verified by Lovable Cloud (issuer,
   audience, signature, expiry, verified email); the browser
   only receives a normal Cloud session afterwards.
   ========================================================= */
function initGoogleSignIn() {
  var containers = document.querySelectorAll("[data-google-button]");
  for (var i = 0; i < containers.length; i++) {
    containers[i].innerHTML =
      '<button type="button" class="btn btn-outline-green w-100" data-google-start>' +
      '<i class="bi bi-google me-2" aria-hidden="true"></i>Continue with Google</button>';
  }
  var buttons = document.querySelectorAll("[data-google-start]");
  for (var j = 0; j < buttons.length; j++) {
    buttons[j].addEventListener("click", function () {
      var btn = this;
      hideError("login-error");
      hideError("register-error");
      setButtonLoading(btn, true, "Opening Google…");
      authGoogle()
        .then(function (res) {
          if (res && res.user) window.location.href = "dashboard.html";
        })
        .catch(function (error) {
          setButtonLoading(btn, false);
          showError("login-error", authErrorMessage(error));
          showError("register-error", authErrorMessage(error));
        });
    });
  }
}

document.addEventListener("DOMContentLoaded", initGoogleSignIn);
