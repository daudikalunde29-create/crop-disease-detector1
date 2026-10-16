/* my-scans.js — renders the signed-in user's real uploads (Lovable Cloud). */
function escapeHtml(v) {
  return String(v).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}
function formatDate(iso) {
  try { return new Date(iso).toLocaleString(); } catch (e) { return iso; }
}
function renderMyScans(container, scans, limit) {
  if (!scans.length) {
    container.innerHTML =
      '<div class="note-box">No scans yet. <a href="scan.html">Upload your first crop photo</a> to get started.</div>';
    return;
  }
  var html = "";
  var list = limit ? scans.slice(0, limit) : scans;
  for (var i = 0; i < list.length; i++) {
    var s = list[i];
    html +=
      '<div class="d-flex flex-wrap align-items-center gap-3 border-bottom py-2" data-scan="' + s.id + '">' +
      '<img alt="Uploaded crop photo" class="rounded" style="width:56px;height:56px;object-fit:cover;background:#eee" data-path="' + escapeHtml(s.image_path) + '">' +
      '<div class="me-auto min-w-0"><div class="fw-semibold text-truncate">' + escapeHtml(s.file_name || "Crop photo") + "</div>" +
      '<div class="small text-muted-soft">' + formatDate(s.created_at) + "</div></div>" +
      '<span class="badge text-bg-secondary">Awaiting AI (not enabled)</span>' +
      (limit ? "" : '<button type="button" class="btn btn-sm btn-outline-danger" data-delete="' + s.id + '" data-path="' + escapeHtml(s.image_path) + '">Delete</button>') +
      "</div>";
  }
  container.innerHTML = html;
  var imgs = container.querySelectorAll("img[data-path]");
  for (var j = 0; j < imgs.length; j++) {
    (function (img) {
      cloud("scanImageUrl", img.getAttribute("data-path")).then(function (u) { img.src = u; }).catch(function () {});
    })(imgs[j]);
  }
  var dels = container.querySelectorAll("[data-delete]");
  for (var k = 0; k < dels.length; k++) {
    dels[k].addEventListener("click", function () {
      if (!confirm("Delete this image from your history?")) return;
      var btn = this;
      btn.disabled = true;
      cloud("deleteScan", btn.getAttribute("data-delete"), btn.getAttribute("data-path"))
        .then(loadMyScansInto.bind(null, container, limit))
        .catch(function (e) { btn.disabled = false; alert(e.message); });
    });
  }
}
function loadMyScansInto(container, limit) {
  return cloud("listScans")
    .then(function (scans) { renderMyScans(container, scans, limit); return scans; })
    .catch(function (e) {
      container.innerHTML = '<div class="alert alert-danger">' + escapeHtml(e.message) + "</div>";
      return [];
    });
}
