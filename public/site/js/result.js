/* =========================================================
   result.js — shows one prediction result.
   PREVIEW ONLY: until the AI backend exists (M8), the layout is
   filled from data/mock-predictions.json and a banner states
   clearly that this is NOT a real AI prediction.
   Later: GET /api/predictions/<id>/.
   ========================================================= */

var LOW_CONFIDENCE_LIMIT = CDD_CONFIG.LOW_CONFIDENCE_THRESHOLD;

function getQueryId() {
  var params = new URLSearchParams(window.location.search);
  return params.get("id");
}

function renderResult(prediction, disease) {
  document.getElementById("result-crop").textContent = prediction.crop;
  document.getElementById("result-condition").textContent = prediction.condition;
  document.getElementById("result-date").textContent = prediction.date;
  document.getElementById("result-confidence").textContent = prediction.confidence + "%";

  var bar = document.getElementById("confidence-bar");
  bar.style.width = prediction.confidence + "%";
  bar.setAttribute("aria-valuenow", prediction.confidence);

  document.getElementById("result-status").innerHTML = statusBadge(prediction.status);

  if (prediction.confidence < LOW_CONFIDENCE_LIMIT) {
    document.getElementById("low-confidence").classList.remove("d-none");
    document.getElementById("condition-details").classList.add("d-none");
    document.querySelector(".confidence-bar").classList.add("low");
    return;
  }

  if (disease) {
    document.getElementById("result-symptoms").textContent = disease.symptoms;
    document.getElementById("result-about").textContent = disease.about;
    document.getElementById("result-management").textContent = disease.management;
    document.getElementById("result-prevention").textContent = disease.prevention;
  }
}

document.addEventListener("DOMContentLoaded", function () {
  requireLogin();

  var main = document.querySelector(".app-main");
  if (main) {
    var banner = document.createElement("div");
    banner.className = "alert alert-warning";
    banner.setAttribute("role", "status");
    banner.innerHTML =
      "<strong>Preview data only.</strong> This is sample content to show the result layout. " +
      "It is NOT a real AI prediction — the AI model is not connected yet.";
    main.insertBefore(banner, main.firstChild);
  }

  var id = getQueryId();

  Promise.all([loadJSON("../data/mock-predictions.json"), loadJSON("../data/mock-diseases.json")])
    .then(function (results) {
      var predictions = results[0];
      var diseases = results[1];

      var prediction = predictions[0];
      for (var i = 0; i < predictions.length; i++) {
        if (predictions[i].id === id) {
          prediction = predictions[i];
        }
      }

      var disease = null;
      for (var j = 0; j < diseases.length; j++) {
        if (diseases[j].name === prediction.condition) {
          disease = diseases[j];
        }
      }

      renderResult(prediction, disease);
    })
    .catch(function (error) {
      console.error(error);
    });
});
