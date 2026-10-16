/* =========================================================
   scan.js — image selection, preview, validation and the
   prediction request.
   NOTE: no AI runs in the browser and no prediction is faked.
   The image is sent (multipart/form-data, field "image") to
   POST /api/predict/. As of M4.2 Django validates the upload and
   answers {status:"not_ready"} because the TensorFlow engine does
   not exist yet (M6-M8); the page shows that message honestly and
   never shows a disease, confidence or treatment it did not receive.
   ========================================================= */

var MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB
var ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];
var selectedFile = null;

function formatSize(bytes) {
  return (bytes / 1024 / 1024).toFixed(2) + " MB";
}

function validateImage(file) {
  if (!file) {
    return "Please choose a crop image first.";
  }
  if (file.size === 0) {
    return "This file is empty. Please choose a real photo.";
  }
  if (ALLOWED_TYPES.indexOf(file.type) === -1) {
    return "Please use a JPG, PNG or WEBP image.";
  }
  if (file.size > MAX_FILE_SIZE) {
    return "The image is too large. Please use an image under 5 MB.";
  }
  return "";
}

function previewImage(file) {
  var reader = new FileReader();
  reader.onload = function (event) {
    document.getElementById("preview-img").src = event.target.result;
  };
  reader.readAsDataURL(file);

  document.getElementById("file-name").textContent = file.name;
  document.getElementById("file-size").textContent = formatSize(file.size);
  document.getElementById("preview-section").classList.remove("d-none");
  document.getElementById("choose-section").classList.add("d-none");
}

function removeImage() {
  selectedFile = null;
  document.getElementById("camera-input").value = "";
  document.getElementById("upload-input").value = "";
  document.getElementById("preview-section").classList.add("d-none");
  document.getElementById("choose-section").classList.remove("d-none");
  document.getElementById("scan-error").classList.add("d-none");
}

function handleFileChange(input) {
  var file = input.files[0];
  var message = validateImage(file);

  if (message) {
    var box = document.getElementById("scan-error");
    box.textContent = message;
    box.classList.remove("d-none");
    input.value = "";
    return;
  }

  document.getElementById("scan-error").classList.add("d-none");
  selectedFile = file;
  previewImage(file);
}

function showScanError(message) {
  var box = document.getElementById("scan-error");
  box.textContent = message;
  box.classList.remove("d-none");
}

function resetScanView() {
  document.getElementById("loading-section").classList.add("d-none");
  document.getElementById("preview-section").classList.remove("d-none");
}

/* Sends the image to Django. Multipart body: the browser sets the
   Content-Type (with boundary), so no Content-Type header is set here. */
function handleScan() {
  var message = validateImage(selectedFile);
  if (message) {
    showScanError(message);
    return;
  }

  document.getElementById("scan-error").classList.add("d-none");
  document.getElementById("preview-section").classList.add("d-none");
  document.getElementById("loading-section").classList.remove("d-none");

  var formData = new FormData();
  formData.append("image", selectedFile);

  fetch((window.CDD_API_BASE || "") + "/api/predict/", {
    method: "POST",
    body: formData,
    credentials: "same-origin",
    headers: { "X-CSRFToken": getCsrfToken() },
  })
    .then(
      function (response) {
        return response
          .json()
          .catch(function () {
            return null;
          })
          .then(function (data) {
            return { status: response.status, ok: response.ok, data: data || {} };
          });
      },
      function () {
        throw new Error(
          "Cannot reach the server. Please check that the backend is running and try again.",
        );
      },
    )
    .then(function (result) {
      var data = result.data;

      if (result.status === 401) {
        redirectToLogin("Your session has expired. Please log in again.");
        return;
      }

      /* Honest "no model yet" answer from Django (HTTP 503). */
      if (data.status === "not_ready") {
        throw new Error(
          (data.message || "Prediction service is not available yet.") +
            " Your image passed validation, but no result was generated.",
        );
      }

      /* Future (M8): a stored prediction with an id opens the result page. */
      if (result.ok && data.prediction && data.prediction.id) {
        window.location.href = "result.html?id=" + encodeURIComponent(data.prediction.id);
        return;
      }

      throw new Error(
        data.message ||
          (result.ok
            ? "The server sent an unexpected response. No result was generated."
            : "The image could not be analysed. Please try again."),
      );
    })
    .catch(function (error) {
      resetScanView();
      showScanError(
        error && error.message ? error.message : "Something went wrong. Please try again.",
      );
    });
}

/* Scan controls are wired only after the session check confirms a
   logged-in user, so guests cannot use the page before the redirect. */
function initScanPage() {
  document.getElementById("camera-input").addEventListener("change", function () {
    handleFileChange(this);
  });
  document.getElementById("upload-input").addEventListener("change", function () {
    handleFileChange(this);
  });
  document.getElementById("btn-camera").addEventListener("click", function () {
    document.getElementById("camera-input").click();
  });
  document.getElementById("btn-upload").addEventListener("click", function () {
    document.getElementById("upload-input").click();
  });
  document.getElementById("btn-remove").addEventListener("click", removeImage);
  document.getElementById("btn-analyze").addEventListener("click", handleScan);
}

document.addEventListener("DOMContentLoaded", function () {
  requireLogin().then(function (user) {
    if (user) {
      initScanPage();
    }
  });
});
