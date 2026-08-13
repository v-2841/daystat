// Cycle length vs smoothed weight over the whole history.
(() => {
    const canvas = document.getElementById("cycleWeightChart");
    if (!canvas || !window.DayStatCharts) return;

    const { palette, fade, baseOptions, register } = window.DayStatCharts;
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
                    borderColor: colors.sky,
                    borderWidth: 2.5,
                    tension: 0.45,
                    fill: true,
                    backgroundColor: (ctx) => fade(ctx, palette().sky),
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
        instance.data.datasets[1].borderColor = next.sky;
        instance.options.plugins.legend.labels.color = next.text;
        instance.options.scales.x.grid.color = next.grid;
        instance.options.scales.cycleLength.grid.color = next.grid;
        instance.options.scales.x.ticks.color = next.muted;
        instance.options.scales.cycleLength.ticks.color = next.muted;
        instance.options.scales.weight.ticks.color = next.muted;
        instance.options.plugins.tooltip.backgroundColor = next.tooltipBg;
        instance.options.plugins.tooltip.titleColor = next.tooltipText;
        instance.options.plugins.tooltip.bodyColor = next.text;
    });

    fetch("/cycle_weight_chart/api/")
        .then((response) => response.json())
        .then((data) => {
            chart.data.datasets[0].data = data.datasets[0].data;
            chart.data.datasets[1].data = data.datasets[1].data;
            chart.update();
        })
        .catch((error) => console.error("Не удалось загрузить данные:", error));
})();
