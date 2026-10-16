/* =========================================================
   admin.js — admin dashboard (frontend UI only)
   No real database operations. Django + MySQL will follow.
   ========================================================= */

function renderAdmin(crops, diseases, predictions) {
  
  document.getElementById("admin-crops").textContent = crops.length;
  document.getElementById("admin-diseases").textContent = diseases.length;
  document.getElementById("admin-predictions").textContent = predictions.length;

  var cropRows = "";
  for (var i = 0; i < crops.length; i++) {
    cropRows +=
      "<tr><td>" +
      crops[i].name +
      "</td><td>" +
      crops[i].scientificName +
      "</td><td>" +
      crops[i].commonDiseases +
      "</td></tr>";
  }
  document.getElementById("admin-crop-body").innerHTML = cropRows;

  var diseaseRows = "";
  for (var j = 0; j < diseases.length; j++) {
    diseaseRows +=
      "<tr><td>" +
      diseases[j].name +
      "</td><td>" +
      diseases[j].crop +
      "</td><td>" +
      diseases[j].about +
      "</td></tr>";
  }
  document.getElementById("admin-disease-body").innerHTML = diseaseRows;

  var predictionRows = "";
  for (var k = 0; k < predictions.length; k++) {
    var p = predictions[k];
    predictionRows +=
      "<tr><td>" +
      p.date +
      "</td><td>" +
      p.crop +
      "</td><td>" +
      p.condition +
      "</td><td>" +
      p.confidence +
      "%</td><td>" +
      statusBadge(p.status) +
      "</td></tr>";
  }
  document.getElementById("admin-prediction-body").innerHTML = predictionRows;
}

document.addEventListener("DOMContentLoaded", function () {
  /* UX gate only — Django must re-check the admin role server-side. */
  requireAdmin().then(function (user) {
    if (!user) {
      return;
    }
    /* Real counts — Cloud only returns other users' rows to admins. */
    cloud("adminStats").then(function (st) {
      document.getElementById("admin-users").textContent = st.users;
      var real = document.getElementById("admin-real-scans");
      if (real) real.textContent = st.scans;
    }).catch(function () {});
    // FUTURE DJANGO API: /api/crops/, /api/diseases/, /api/predictions/
    Promise.all([
      loadJSON("../data/mock-crops.json"),
      loadJSON("../data/mock-diseases.json"),
      loadJSON("../data/mock-predictions.json"),
    ])
      .then(function (results) {
        renderAdmin(results[0], results[1], results[2]);
      })
      .catch(function (error) {
        console.error(error);
      });
  });
});
