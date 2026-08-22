// Month grid: day details sheet + horizontal swipe between months.
(() => {
    const grid = document.getElementById("calendar");
    const sheet = document.getElementById("day-sheet");
    if (!grid || !sheet) return;

    const title = document.getElementById("sheet-title");
    const body = document.getElementById("sheet-body");
    const link = document.getElementById("sheet-link");
    const close = document.getElementById("sheet-close");

    let opener = null;

    const hide = ({ restoreFocus = false } = {}) => {
        if (sheet.classList.contains("hidden")) return;
        sheet.classList.add("hidden");
        if (restoreFocus && opener) opener.focus();
    };

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
            link.href = grid.dataset.dayUrl.replace("__date__",
                cell.dataset.date);
            sheet.classList.remove("hidden");
            sheet.classList.remove("animate-rise");
            void sheet.offsetWidth;
            sheet.classList.add("animate-rise");
            opener = cell;
            link.focus();

            grid.querySelectorAll(".day-cell").forEach((other) =>
                other.classList.toggle("is-selected", other === cell)
            );
        });
    });

    close.addEventListener("click", () => hide({ restoreFocus: true }));
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") hide({ restoreFocus: true });
    });

    // ------------------------------------------------------------- swipe
    // touch events, because a horizontal drag over the grid makes the
    // browser fire pointercancel instead of pointerup
    const prev = grid.querySelector('[data-nav="prev"]');
    const next = grid.querySelector('[data-nav="next"]');
    let startX = 0;
    let startY = 0;
    let tracking = false;

    grid.addEventListener(
        "touchstart",
        (event) => {
            if (event.touches.length !== 1) {
                tracking = false;
                return;
            }
            tracking = true;
            startX = event.touches[0].clientX;
            startY = event.touches[0].clientY;
        },
        { passive: true }
    );

    grid.addEventListener(
        "touchend",
        (event) => {
            if (!tracking) return;
            tracking = false;
            const touch = event.changedTouches[0];
            if (!touch) return;
            const dx = touch.clientX - startX;
            const dy = touch.clientY - startY;
            if (Math.abs(dx) < 60 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
            const target = dx < 0 ? next : prev;
            if (target) window.location.href = target.href;
        },
        { passive: true }
    );

    grid.addEventListener("touchcancel", () => {
        tracking = false;
    });
})();
