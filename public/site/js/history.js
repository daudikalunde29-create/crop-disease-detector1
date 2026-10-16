/* =========================================================
   history.js — previous scans (table on desktop, cards on mobile)
   ========================================================= */

function renderHistory(scans) {
  var tableBody = document.getElementById("history-body");
  var cardWrap = document.getElementById("history-cards");

  if (!scans.length) {
    tableBody.innerHTML =
      '<tr><td colspan="6" class="text-center text-muted-soft py-4">No scans yet.</td></tr>';
    cardWrap.innerHTML = '<p class="text-muted-soft">No scans yet.</p>';
    return;
  }

  var rows = "";
  var cards = "";

  for (var i = 0; i < scans.length; i++) {
    var scan = scans[i];

    rows +=
      "<tr>" +
      "<td>" +
      scan.date +
      "</td>" +
      "<td>" +
      scan.crop +
      "</td>" +
      "<td>" +
      scan.condition +
      "</td>" +
      "<td>" +
      scan.confidence +
      "%</td>" +
      "<td>" +
      statusBadge(scan.status) +
      "</td>" +
      '<td><a class="btn btn-sm btn-outline-green" href="result.html?id=' +
      scan.id +
      '">View Result</a></td>' +
      "</tr>";

    cards +=
      '<div class="card-soft mb-3"><div class="card-body">' +
      '<div class="d-flex justify-content-between align-items-start gap-2">' +
      '<div class="min-w-0"><div class="fw-semibold">' +
      scan.crop +
      "</div>" +
      '<div class="small text-muted-soft">' +
      scan.date +
      "</div></div>" +
      statusBadge(scan.status) +
      "</div>" +
      '<p class="mb-1 mt-2">' +
      scan.condition +
      "</p>" +
      '<p class="small text-muted-soft">Confidence: ' +
      scan.confidence +
      "%</p>" +
      '<a class="btn btn-sm btn-green w-100" href="result.html?id=' +
      scan.id +
      '">View Result</a>' +
      "</div></div>";
  }

  tableBody.innerHTML = rows;
  cardWrap.innerHTML = cards;
}

document.addEventListener("DOMContentLoaded", function () {
  requireLogin();

  // FUTURE DJANGO API: fetch('/api/history/')
  loadJSON("../data/mock-predictions.json")
    .then(renderHistory)
    .catch(function (error) {
      console.error(error);
    });
});
