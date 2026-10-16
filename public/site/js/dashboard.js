/* =========================================================
   dashboard.js — farmer dashboard statistics & recent scans
   Data currently comes from data/mock-predictions.json
   ========================================================= */

function renderDashboard(scans) {
  var total = scans.length;
  var healthy = 0;
  var diseases = 0;

  for (var i = 0; i < scans.length; i++) {
    if (scans[i].status === "healthy") {
      healthy++;
    } else if (scans[i].status === "disease") {
      diseases++;
    }
  }

  document.getElementById("stat-total").textContent = total;
  document.getElementById("stat-healthy").textContent = healthy;
  document.getElementById("stat-diseases").textContent = diseases;
  document.getElementById("stat-last").textContent = total ? scans[0].date : "—";

  var list = document.getElementById("recent-scans");
  if (!list) {
    return;
  }

  if (!total) {
    list.innerHTML =
      '<p class="text-muted-soft mb-0">No scans yet. Start with your first crop scan.</p>';
    return;
  }

  var html = "";
  for (var j = 0; j < Math.min(scans.length, 4); j++) {
    var scan = scans[j];
    html +=
      '<div class="d-flex flex-wrap align-items-center justify-content-between gap-2 border-bottom py-3">' +
      '<div class="me-auto">' +
      '<div class="fw-semibold">' +
      scan.crop +
      " — " +
      scan.condition +
      "</div>" +
      '<div class="small text-muted-soft">' +
      scan.date +
      "</div>" +
      "</div>" +
      '<div class="text-end">' +
      statusBadge(scan.status) +
      '<div class="small text-muted-soft">' +
      scan.confidence +
      "% confidence</div>" +
      "</div>" +
      '<a class="btn btn-sm btn-outline-green" href="result.html?id=' +
      scan.id +
      '">View</a>' +
      "</div>";
  }
  list.innerHTML = html;
}

document.addEventListener("DOMContentLoaded", function () {
  requireLogin().then(function (user) {
    var nameNode = document.getElementById("welcome-name");
    if (nameNode && user) {
      nameNode.textContent = user.name || user.fullName || "";
    }
  });

  // FUTURE DJANGO API: fetch('/api/history/')
  loadJSON("../data/mock-predictions.json")
    .then(renderDashboard)
    .catch(function (error) {
      console.error(error);
    });
});
