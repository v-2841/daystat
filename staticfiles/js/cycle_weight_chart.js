moment.locale("ru");
Chart.defaults.color = "#991a7d";

document.addEventListener("DOMContentLoaded", function () {
    const refreshButton = document.getElementById(
        "refreshCycleWeightChartButton"
    );
    const ctx = document.getElementById("cycleWeightChart");

    let cycleWeightChart = new Chart(ctx, {
        type: "line",
        data: {
            datasets: [
                {
                    label: "Длина завершенного цикла",
                    data: [],
                    borderColor: "#991a7d",
                    backgroundColor: "#991a7d",
                    pointRadius: 4,
                    pointHoverRadius: 5,
                    tension: 0.2,
                    yAxisID: "cycleLength",
                },
                {
                    label: "Средний вес",
                    data: [],
                    borderColor: "#0d6efd",
                    backgroundColor: "#0d6efd",
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    tension: 0.45,
                    yAxisID: "weight",
                },
            ],
        },
        options: {
            maintainAspectRatio: false,
            interaction: {
                mode: "index",
                intersect: false,
            },
            plugins: {
                legend: {
                    display: true,
                },
            },
            scales: {
                x: {
                    type: "time",
                    time: {
                        unit: "day",
                        displayFormats: {
                            day: "DD MMM YYYY",
                        },
                        tooltipFormat: "DD MMM YYYY",
                    },
                    ticks: {
                        callback: (value) =>
                            moment(value).format("DD MMM YYYY"),
                    },
                    title: {
                        display: true,
                        text: "Дата",
                    },
                },
                cycleLength: {
                    type: "linear",
                    position: "left",
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: "Длина цикла, дн.",
                    },
                    ticks: {
                        precision: 0,
                    },
                },
                weight: {
                    type: "linear",
                    position: "right",
                    grid: {
                        drawOnChartArea: false,
                    },
                    title: {
                        display: true,
                        text: "Средний вес, кг",
                    },
                },
            },
        },
    });

    function updateChart(dataset) {
        cycleWeightChart.data.datasets[0].data = dataset.datasets[0].data;
        cycleWeightChart.data.datasets[1].data = dataset.datasets[1].data;
        cycleWeightChart.update();
    }

    function setRefreshState(isLoading) {
        if (!refreshButton) {
            return;
        }
        refreshButton.disabled = isLoading;
        refreshButton.classList.toggle("opacity-75", isLoading);
    }

    function fetchData() {
        setRefreshState(true);
        return fetch("/cycle_weight_chart/api/")
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then((data) => {
                updateChart(data);
            })
            .catch((error) =>
                console.error("Ошибка при получении данных:", error)
            )
            .finally(() => {
                setRefreshState(false);
            });
    }

    if (refreshButton) {
        refreshButton.addEventListener("click", function () {
            fetchData();
        });
    }

    fetchData();
});
