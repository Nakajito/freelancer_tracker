(function () {
  function dismiss(notification) {
    notification.style.opacity = "0";
    notification.style.transform = "translateY(-4px)";
    window.setTimeout(function () {
      notification.remove();
    }, 180);
  }

  function initNotifications() {
    document.querySelectorAll("[data-auto-dismiss]").forEach(function (notification) {
      var close = notification.querySelector(".notification-close");
      if (close) {
        close.addEventListener("click", function () {
          dismiss(notification);
        });
      }

      var delay = Number(notification.dataset.autoDismiss || 5000);
      if (delay > 0) {
        window.setTimeout(function () {
          dismiss(notification);
        }, delay);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initNotifications);
  } else {
    initNotifications();
  }
})();
