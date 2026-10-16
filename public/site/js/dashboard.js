/* =========================================================
   dashboard.js — farmer dashboard with REAL account data
   from Lovable Cloud. AI is not enabled yet, so healthy /
   disease counts stay empty instead of being invented.
   ========================================================= */
document.addEventListener("DOMContentLoaded", function () {
  requireLogin().then(function (user) {
    if (!user) return;
    var nameNode = document.getElementById("welcome-name");
    if (nameNode) nameNode.textContent = "Welcome, " + (user.name || user.email) + " · " + user.email;
    document.getElementById("stat-healthy").textContent = "—";
    document.getElementById("stat-diseases").textContent = "—";
    loadMyScansInto(document.getElementById("recent-scans"), 4).then(function (scans) {
      document.getElementById("stat-total").textContent = scans.length;
      document.getElementById("stat-last").textContent = scans.length ? new Date(scans[0].created_at).toLocaleDateString() : "—";
    });
  });
});
