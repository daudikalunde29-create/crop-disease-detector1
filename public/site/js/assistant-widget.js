(function () {
  if (document.getElementById("cdd-assistant-launcher")) return;
  var css = document.createElement("link");
  css.rel = "stylesheet";
  css.href = "/site/css/assistant.css";
  document.head.appendChild(css);
  var button = document.createElement("button");
  button.id = "cdd-assistant-launcher";
  button.type = "button";
  button.className = "btn cdd-assistant-launcher";
  button.setAttribute("aria-label", "Open Crop Assistant");
  button.setAttribute("aria-expanded", "false");
  button.title = "Crop Assistant";
  button.innerHTML = '<img src="/site/assets/images/crop-assistant.svg" alt=""><span>Crop Assistant</span>';
  var frame;
  function close() {
    if (frame) { frame.remove(); frame = null; }
    button.setAttribute("aria-expanded", "false");
    button.focus();
  }
  button.addEventListener("click", function () {
    if (frame) { close(); return; }
    frame = document.createElement("iframe");
    frame.src = "/assistant";
    frame.title = "Crop Assistant";
    frame.className = "cdd-assistant-frame";
    document.body.appendChild(frame);
    button.setAttribute("aria-expanded", "true");
  });
  window.addEventListener("message", function (event) {
    if (frame && event.origin === window.location.origin && event.source === frame.contentWindow && event.data && event.data.type === "cdd-assistant-close") close();
  });
  document.addEventListener("keydown", function (event) { if (event.key === "Escape") close(); });
  document.body.appendChild(button);
})();