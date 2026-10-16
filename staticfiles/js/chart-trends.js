// Weight / calories chart with range switching and labelled highs and lows.
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

    // the value of every key point, above a high and below a low
    const keyLabels = {
        id: "keyLabels",
        afterDatasetsDraw(chart, args, options) {
            const { ctx, chartArea } = chart;
            const number = new Intl.NumberFormat(chart.options.locale, {
                minimumFractionDigits: options.digits,
                maximumFractionDigits: options.digits,
            });
            ctx.save();
            ctx.font = "bold 11px Nunito";
            ctx.textAlign = "center";
            ctx.lineJoin = "round";
            ctx.lineWidth = 3;
            ctx.strokeStyle = options.halo;
            ctx.fillStyle = options.color;
            chart.data.datasets.forEach((dataset, index) => {
                if (!dataset.keyPoint) return;
                const above = dataset.keyPoint === "high";
                ctx.textBaseline = above ? "bottom" : "top";
                chart.getDatasetMeta(index).data.forEach((point, i) => {
                    const text = number.format(dataset.data[i][1]);
                    const half = ctx.measureText(text).width / 2;
                    // the first and the last day would push it off the plot
                    const x = Math.min(
                        Math.max(point.x, chartArea.left + half),
                        chartArea.right - half
                    );
                    const y = point.y + (above ? -8 : 8);
                    ctx.strokeText(text, x, y);
                    ctx.fillText(text, x, y);
                });
            });
            ctx.restore();
        },
    };

    const colors = palette();
    const options = baseOptions();
    // the key points share dates with the line, so both show in the tooltip
    options.interaction = { mode: "nearest", axis: "x", intersect: false };
    // room for the labels above the highs and below the lows
    options.scales.y.grace = "12%";
    options.plugins.keyLabels = {
        color: colors.tooltipText,
        halo: colors.surface,
        digits: 1,
    };
    options.plugins.tooltip.callbacks = {
        label: (item) => {
            const value = `${item.formattedValue} ${canvas.dataset.unit || ""}`.trim();
            return item.dataset.keyPoint
                ? `${item.dataset.label}: ${value}`
                : value;
        },
    };

    const keyDataset = (kind, label) => ({
        keyPoint: kind,
        label,
        data: [],
        // drawn over the line and its fill
        order: 0,
        showLine: false,
        pointRadius: 4.5,
        pointHoverRadius: 6,
        pointBorderWidth: 2,
        pointHoverBorderWidth: 2,
        pointBackgroundColor: colors.accent,
        pointHoverBackgroundColor: colors.accent,
        pointBorderColor: colors.surface,
        pointHoverBorderColor: colors.surface,
    });

    const chart = new Chart(canvas, {
        type: "line",
        data: {
            datasets: [
                {
                    data: [],
                    order: 1,
                    borderColor: colors.accent,
                    borderWidth: 2.5,
                    tension: 0.4,
                    fill: true,
                    backgroundColor: (ctx) => fade(ctx, palette().accent),
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    pointHoverBorderWidth: 2,
                    pointHoverBackgroundColor: colors.accent,
                    pointHoverBorderColor: "#fff",
                },
                keyDataset("high", "максимум"),
                keyDataset("low", "минимум"),
            ],
        },
        options,
        plugins: [keyLabels],
    });

    register(chart, (instance, next) => {
        const [line, ...keys] = instance.data.datasets;
        line.borderColor = next.accent;
        line.pointHoverBackgroundColor = next.accent;
        keys.forEach((dataset) => {
            dataset.pointBackgroundColor = next.accent;
            dataset.pointHoverBackgroundColor = next.accent;
            dataset.pointBorderColor = next.surface;
            dataset.pointHoverBorderColor = next.surface;
        });
        instance.options.plugins.keyLabels.color = next.tooltipText;
        instance.options.plugins.keyLabels.halo = next.surface;
        applyTheme(instance, next, ["x", "y"]);
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
                // «56,0» next to «56,9», not «56»
                chart.options.plugins.keyLabels.digits = type === "weight" ? 1 : 0;
                const [line, highs, lows] = chart.data.datasets;
                line.data = data.data;
                highs.data = data.highs;
                lows.data = data.lows;
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
