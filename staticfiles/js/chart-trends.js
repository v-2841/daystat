// Weight / calories chart with range switching.
(() => {
    const canvas = document.getElementById("myChart");
    if (!canvas || !window.DaystatCharts) return;

    const { palette, fade, baseOptions, register, applyTheme } =
        window.DaystatCharts;
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
        applyTheme(instance, colors, ["x", "y"]);
    });

    const status = document.getElementById("chart-status");
    let pending = null;

    const load = () => {
        const type = selected(typeButtons);
        const range = selected(rangeButtons);
        if (!type || !range) return;
        // a slower earlier request must not overwrite the current range
        pending?.abort();
        pending = new AbortController();
        if (status) status.textContent = "";
        fetch(`/chart/${type}/${range}/`, { signal: pending.signal })
            .then((response) => {
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                return response.json();
            })
            .then((data) => {
                canvas.dataset.unit = type === "weight" ? "кг" : "ккал";
                chart.data.datasets[0].data = data.data;
                chart.update();
            })
            .catch((error) => {
                if (error.name === "AbortError") return;
                console.error("Не удалось загрузить данные:", error);
                if (status) {
                    status.textContent =
                        "Не удалось загрузить данные. Попробуйте обновить страницу.";
                }
            });
    };

    [...typeButtons, ...rangeButtons].forEach((button) =>
        button.addEventListener("change", load)
    );

    load();
})();
