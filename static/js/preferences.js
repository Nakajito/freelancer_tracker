(function () {
  function applyTheme() {
    var root = document.documentElement;
    var preference = root.dataset.theme || "system";
    var darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
    var resolved = preference === "system" ? (darkQuery.matches ? "dark" : "light") : preference;
    root.dataset.themeResolved = resolved;
  }

  function bindAutoSubmit() {
    document.querySelectorAll("[data-auto-submit]").forEach(function (field) {
      field.addEventListener("change", function () {
        field.form.submit();
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      applyTheme();
      bindAutoSubmit();
    });
  } else {
    applyTheme();
    bindAutoSubmit();
  }

  var darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
  if (darkQuery.addEventListener) {
    darkQuery.addEventListener("change", applyTheme);
  }
})();
