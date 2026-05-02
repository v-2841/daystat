moment.locale("ru");
Chart.defaults.color = "#991a7d";

document.addEventListener("DOMContentLoaded", function () {
    const typeButtons = document.querySelectorAll('input[name="type"]');
    const rangeButtons = document.querySelectorAll('input[name="range"]');
    const refreshButton = document.getElementById("refreshChartButton");
    let selectedType = null;
    let selectedRange = null;

    const ctx = document.getElementById("myChart");
    let myChart = new Chart(ctx, {
        type: "line",
        data: {
            datasets: [
                {
                    data: [],
                    tension: 0.5,
                },
            ],
        },
        options: {
            maintainAspectRatio: false,
            elements: {
                line: {
                    borderColor: "#991a7d",
                },
            },
            plugins: {
                legend: {
                    display: false,
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
                        callback: (value) => {
                            const axisFormat =
                                selectedRange === "year" ||
                                selectedRange === "5years"
                                    ? "DD MMM YYYY"
                                    : "DD MMM";
                            return moment(value).format(axisFormat);
                        },
                    },
                    title: {
                        display: true,
                        text: "Дата",
                    },
                },
                y: {
                    title: {
                        display: true,
                    },
                },
            },
        },
    });

    function updateChart(dataset) {
        myChart.data.datasets[0].data = dataset.data;
        myChart.options.scales.y.title.text = dataset.title;
        myChart.update();
    }

    function setRefreshState(isLoading) {
        if (!refreshButton) {
            return;
        }
        refreshButton.disabled = isLoading;
        refreshButton.classList.toggle("opacity-75", isLoading);
    }

    function fetchData(type, range) {
        const url = `/chart/${type}/${range}/`;
        setRefreshState(true);
        return fetch(url)
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

    function handleChange() {
        if (selectedType && selectedRange) {
            fetchData(selectedType, selectedRange);
        }
    }

    typeButtons.forEach((button) => {
        button.addEventListener("change", function () {
            selectedType = this.id.replace("Button", "").toLowerCase();
            handleChange();
        });
    });

    rangeButtons.forEach((button) => {
        button.addEventListener("change", function () {
            selectedRange = this.id.replace("Button", "").toLowerCase();
            handleChange();
        });
    });

    if (refreshButton) {
        refreshButton.addEventListener("click", function () {
            handleChange();
        });
    }

    typeButtons[0].checked = true;
    selectedType = typeButtons[0].id.replace("Button", "").toLowerCase();
    rangeButtons[0].checked = true;
    selectedRange = rangeButtons[0].id.replace("Button", "").toLowerCase();

    handleChange();
});
