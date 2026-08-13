// Month grid: day details sheet + horizontal swipe between months.
(() => {
    const grid = document.getElementById("calendar");
    const sheet = document.getElementById("day-sheet");
    if (!grid || !sheet) return;

    const title = document.getElementById("sheet-title");
    const body = document.getElementById("sheet-body");
    const link = document.getElementById("sheet-link");
    const close = document.getElementById("sheet-close");

    const hide = () => sheet.classList.add("hidden");

    const describe = (cell) => {
        const parts = [];
        if (cell.dataset.weight) parts.push(`${cell.dataset.weight} кг`);
        if (cell.dataset.calories) parts.push(`${cell.dataset.calories} ккал`);
        if (cell.dataset.period) parts.push("начало цикла");
        if (cell.dataset.predicted === "upcoming") parts.push("прогноз цикла");
        if (cell.dataset.predicted === "overdue") parts.push("цикл задерживается");
        if (!parts.length) {
            parts.push(cell.dataset.future ? "будущий день" : "нет записей");
        }
        return parts.join(" · ");
    };

    grid.querySelectorAll(".day-cell").forEach((cell) => {
        cell.addEventListener("click", () => {
            title.textContent = cell.dataset.display;
            body.textContent = describe(cell);
            link.href = `/daystats/${cell.dataset.date}/`;
            sheet.classList.remove("hidden");
            sheet.classList.remove("animate-rise");
            void sheet.offsetWidth;
            sheet.classList.add("animate-rise");

            grid.querySelectorAll(".day-cell").forEach((other) =>
                other.classList.toggle("is-selected", other === cell)
            );
        });
    });

    close.addEventListener("click", hide);
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") hide();
    });

    // ---------------------------------------------------------- swipe
    const prev = grid.querySelector('[data-nav="prev"]');
    const next = grid.querySelector('[data-nav="next"]');
    let startX = 0;
    let startY = 0;
    let tracking = false;

    grid.addEventListener(
        "pointerdown",
        (event) => {
            if (event.pointerType === "mouse") return;
            tracking = true;
            startX = event.clientX;
            startY = event.clientY;
        },
        { passive: true }
    );

    grid.addEventListener(
        "pointerup",
        (event) => {
            if (!tracking) return;
            tracking = false;
            const dx = event.clientX - startX;
            const dy = event.clientY - startY;
            if (Math.abs(dx) < 60 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
            const target = dx < 0 ? next : prev;
            if (target) window.location.href = target.href;
        },
        { passive: true }
    );
})();
