// Weight / calories chart with range switching.
(() => {
    const canvas = document.getElementById("myChart");
    if (!canvas || !window.DaystatCharts) return;

    const { palette, fade, baseOptions, register } = window.DaystatCharts;
    const typeButtons = document.querySelectorAll('input[name="type"]');
    const rangeButtons = document.querySelectorAll('input[name="range"]');

    const selected = (buttons) => {
        const active = [...buttons].find((button) => button.checked);
        return active ? active.id.replace("Button", "").toLowerCase() : null;
    };

    const options = baseOptions();
    options.plugins.tooltip.callbacks = {
        label: (item) => `${item.formattedValue} ${canvas.dataset.unit || ""}`.trim(),
    };

    const chart = new Chart(canvas, {
        type: "line",
        data: {
            datasets: [
                {
                    data: [],
                    borderColor: palette().accent,
                    borderWidth: 2.5,
                    tension: 0.4,
                    fill: true,
                    backgroundColor: (ctx) => fade(ctx, palette().accent),
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    pointHoverBorderWidth: 2,
                    pointHoverBackgroundColor: palette().accent,
                    pointHoverBorderColor: "#fff",
                },
            ],
        },
        options,
    });

    register(chart, (instance, colors) => {
        instance.data.datasets[0].borderColor = colors.accent;
        instance.data.datasets[0].pointHoverBackgroundColor = colors.accent;
        instance.options.scales.x.grid.color = colors.grid;
        instance.options.scales.y.grid.color = colors.grid;
        instance.options.scales.x.ticks.color = colors.muted;
        instance.options.scales.y.ticks.color = colors.muted;
        instance.options.plugins.tooltip.backgroundColor = colors.tooltipBg;
        instance.options.plugins.tooltip.titleColor = colors.tooltipText;
        instance.options.plugins.tooltip.bodyColor = colors.text;
    });

    const load = () => {
        const type = selected(typeButtons);
        const range = selected(rangeButtons);
        if (!type || !range) return;
        fetch(`/chart/${type}/${range}/`)
            .then((response) => response.json())
            .then((data) => {
                canvas.dataset.unit = type === "weight" ? "кг" : "ккал";
                chart.data.datasets[0].data = data.data;
                chart.update();
            })
            .catch((error) => console.error("Не удалось загрузить данные:", error));
    };

    [...typeButtons, ...rangeButtons].forEach((button) =>
        button.addEventListener("change", load)
    );

    load();
})();
