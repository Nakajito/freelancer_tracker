(function () {
  var LANG_LABELS = { en: "EN", es: "ES" };

  function updateLangBtn(btn, val) {
    btn.dataset.value = val;
    var label = btn.querySelector("[data-lang-label]");
    if (label) label.textContent = LANG_LABELS[val] || val.toUpperCase();
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
    bindLangButtons();
    bindAutoSubmit();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
