(function () {
    function initForecastChart(canvas) {
        if (!canvas) return;
        if (typeof Chart === "undefined") {
            console.error("Chart.js not loaded — forecastChart will not render");
            return;
        }
        let labels, data;
        try {
            labels = JSON.parse(canvas.dataset.labels || "[]");
            data = JSON.parse(canvas.dataset.data || "[]");
        } catch (e) {
            console.error("forecastChart: bad JSON in data attributes", e);
            return;
        }
        new Chart(canvas.getContext("2d"), {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: "Earnings",
                    data: data,
                    backgroundColor: "#00685f",
                    borderRadius: 4,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (value) {
                                return "$" + value.toLocaleString();
                            },
                        },
                    },
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                return "$" + ctx.parsed.y.toLocaleString();
                            },
                        },
                    },
                    legend: { display: false },
                },
            },
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        initForecastChart(document.getElementById("forecastChart"));
    });
})();
