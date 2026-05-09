// Chart.js initializers for PropoTrack dashboards.
// Reads canvas data attributes (data-labels, data-data) that views populate
// via JSON. Keeps chart logic out of templates.

(function () {
    function initForecastChart(canvas) {
        if (!canvas || typeof Chart === "undefined") return;
        const labels = JSON.parse(canvas.dataset.labels || "[]");
        const data = JSON.parse(canvas.dataset.data || "[]");
        new Chart(canvas.getContext("2d"), {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: "Earnings",
                    data: data,
                    backgroundColor: "#00685f",
                }],
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true } },
            },
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        initForecastChart(document.getElementById("forecastChart"));
    });
})();
