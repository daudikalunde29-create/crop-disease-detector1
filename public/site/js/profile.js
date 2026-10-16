/* =========================================================
   profile.js — profile view/edit + change password.
   Django (M4.2): POST /api/auth/change-password/
   { currentPassword, newPassword }.
   Profile name/phone updates use GET/PUT /api/profile/.
   ========================================================= */
document.addEventListener("DOMContentLoaded", function () {
  requireAuth().then(function (user) {
    if (!user) {
      return;
    }

    /* Profile details from the authenticated session. */
    document.getElementById("fullName").value = user.name || "";
    document.getElementById("phone").value = user.phone || "";
    document.getElementById("email").value = user.email || "";
    document.getElementById("accountType").value = user.role === "admin" ? "Admin" : "Farmer";
    document.getElementById("provider").value = user.provider === "google" ? "Google" : "Email";
    if (user.createdAt) {
      document.getElementById("createdAt").value = new Date(user.createdAt).toLocaleDateString();
    }

    /* Google accounts have no local password to change (the server also
       refuses with NO_LOCAL_PASSWORD). They can create one via
       "Forgot password" on the login page. */
    if (user.provider === "google") {
      document.getElementById("change-password-card").classList.add("d-none");
    }

    document.getElementById("profile-form").addEventListener("submit", function (event) {
      event.preventDefault();
      hideError("profile-error");

      var fullName = document.getElementById("fullName").value.trim();
      var phone = document.getElementById("phone").value.trim();
      if (!fullName || !phone) {
        showError("profile-error", "Name and phone number are required.");
        return;
      }
      if (fullName.length > 150 || phone.length > 32) {
        showError("profile-error", "Name must be 150 characters or fewer and phone 32 characters or fewer.");
        return;
      }

      var saveButton = document.querySelector("#profile-form button[type='submit']");
      setButtonLoading(saveButton, true, "Saving…");
      authUpdateProfile(fullName, phone)
        .then(function (updatedUser) {
          setButtonLoading(saveButton, false);
          document.getElementById("fullName").value = updatedUser.name || fullName;
          document.getElementById("phone").value = updatedUser.phone || phone;
          showSuccess("profile-saved", "Profile updated successfully.");
        })
        .catch(function (error) {
          setButtonLoading(saveButton, false);
          showError("profile-error", authErrorMessage(error));
        });
    });

    var changeForm = document.getElementById("change-password-form");
    if (changeForm) {
      changeForm.addEventListener("submit", function (event) {
        event.preventDefault();
        hideError("change-error");
        hideError("change-success");

        var current = document.getElementById("currentPassword").value;
        var next = document.getElementById("newPassword").value;
        var confirm = document.getElementById("confirmNewPassword").value;
        var button = changeForm.querySelector("button[type='submit']");

        if (!current || !next || !confirm) {
          showError("change-error", "All fields are required.");
          return;
        }
        var strengthError = passwordStrengthError(next);
        if (strengthError) {
          showError("change-error", strengthError);
          return;
        }
        if (next !== confirm) {
          showError("change-error", "The two passwords do not match.");
          return;
        }

        setButtonLoading(button, true, "Updating…");
        authChangePassword(current, next)
          .then(function () {
            setButtonLoading(button, false);
            changeForm.reset();
            showSuccess("change-success", "Your password has been changed.");
          })
          .catch(function (error) {
            setButtonLoading(button, false);
            showError("change-error", authErrorMessage(error));
          });
      });
    }
  });
});
