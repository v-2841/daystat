// Cycle length vs smoothed weight over the whole history.
(() => {
    const canvas = document.getElementById("cycleWeightChart");
    if (!canvas || !window.DaystatCharts) return;

    const { palette, fade, baseOptions, register, applyTheme } =
        window.DaystatCharts;
    const colors = palette();
    const options = baseOptions();

    options.plugins.legend.display = true;
    options.plugins.legend.position = "bottom";
    options.plugins.tooltip.displayColors = true;
    options.scales = {
        x: options.scales.x,
        cycleLength: {
            ...options.scales.y,
            position: "left",
            beginAtZero: true,
            ticks: { ...options.scales.y.ticks, precision: 0 },
        },
        weight: {
            ...options.scales.y,
            position: "right",
            grid: { display: false },
        },
    };

    const chart = new Chart(canvas, {
        type: "line",
        data: {
            datasets: [
                {
                    label: "Длина цикла, дн.",
                    data: [],
                    borderColor: colors.accent,
                    backgroundColor: colors.accent,
                    borderWidth: 2.5,
                    pointRadius: 3.5,
                    pointHoverRadius: 6,
                    tension: 0.3,
                    yAxisID: "cycleLength",
                },
                {
                    label: "Средний вес, кг",
                    data: [],
                    borderColor: colors.line2,
                    borderWidth: 2.5,
                    tension: 0.45,
                    fill: true,
                    backgroundColor: (ctx) => fade(ctx, palette().line2),
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    yAxisID: "weight",
                },
            ],
        },
        options,
    });

    register(chart, (instance, next) => {
        instance.data.datasets[0].borderColor = next.accent;
        instance.data.datasets[0].backgroundColor = next.accent;
        instance.data.datasets[1].borderColor = next.line2;
        applyTheme(instance, next, ["x", "cycleLength", "weight"]);
    });

    fetch("/cycle_weight_chart/api/")
        .then((response) => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then((data) => {
            chart.data.datasets[0].data = data.datasets[0].data;
            chart.data.datasets[1].data = data.datasets[1].data;
            chart.update();
        })
        .catch((error) => {
            console.error("Не удалось загрузить данные:", error);
            const status = document.getElementById("chart-status");
            if (status) {
                status.textContent =
                    "Не удалось загрузить данные. Попробуйте обновить страницу.";
            }
        });
})();
