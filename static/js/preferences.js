(function () {
  var THEME_CYCLE = ["system", "light", "dark"];
  var THEME_META = {
    system: { icon: "display_settings", label: "System" },
    light: { icon: "light_mode", label: "Light" },
    dark: { icon: "dark_mode", label: "Dark" },
  };
  var LANG_LABELS = { en: "EN", es: "ES" };

  function applyTheme() {
    var root = document.documentElement;
    var preference = root.dataset.theme || "system";
    var darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
    var resolved =
      preference === "system"
        ? darkQuery.matches
          ? "dark"
          : "light"
        : preference;
    root.dataset.themeResolved = resolved;
  }

  function updateThemeBtn(btn, val) {
    var meta = THEME_META[val] || THEME_META.system;
    btn.dataset.value = val;
    var icon = btn.querySelector("[data-theme-icon]");
    var label = btn.querySelector("[data-theme-label]");
    if (icon) icon.textContent = meta.icon;
    if (label) label.textContent = meta.label;
  }

  function updateLangBtn(btn, val) {
    btn.dataset.value = val;
    var label = btn.querySelector("[data-lang-label]");
    if (label) label.textContent = LANG_LABELS[val] || val.toUpperCase();
  }

  function bindThemeButtons() {
    document.querySelectorAll("[data-theme-btn]").forEach(function (btn) {
      updateThemeBtn(btn, btn.dataset.value || "system");

      btn.addEventListener("click", function () {
        var current = btn.dataset.value || "system";
        var idx = THEME_CYCLE.indexOf(current);
        var next = THEME_CYCLE[(idx + 1) % THEME_CYCLE.length];

        document.documentElement.dataset.theme = next;
        applyTheme();

        document.querySelectorAll("[data-theme-btn]").forEach(function (b) {
          updateThemeBtn(b, next);
        });

        var form = document.getElementById("prefs-form");
        if (form) {
          var input = document.getElementById("theme-input");
          if (input) {
            input.value = next;
            form.submit();
          }
        } else {
          localStorage.setItem("ft_theme", next);
        }
      });
    });
  }

  function bindLangButtons() {
    document.querySelectorAll("[data-lang-btn]").forEach(function (btn) {
      updateLangBtn(btn, btn.dataset.value || "en");

      btn.addEventListener("click", function () {
        var current = btn.dataset.value || "en";
        var next = current === "en" ? "es" : "en";

        document.querySelectorAll("[data-lang-btn]").forEach(function (b) {
          updateLangBtn(b, next);
        });

        var prefsForm = document.getElementById("prefs-form");
        if (prefsForm) {
          var input = document.getElementById("lang-input");
          if (input) {
            input.value = next;
            prefsForm.submit();
          }
        } else {
          var langInput = document.getElementById("lang-input-public");
          var langForm = document.getElementById("lang-form");
          if (langInput && langForm) {
            langInput.value = next;
            langForm.submit();
          }
        }
      });
    });
  }

  function bindAutoSubmit() {
    document.querySelectorAll("[data-auto-submit]").forEach(function (field) {
      field.addEventListener("change", function () {
        field.form.submit();
      });
    });
  }

  function init() {
    applyTheme();
    bindThemeButtons();
    bindLangButtons();
    bindAutoSubmit();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", applyTheme);
})();
