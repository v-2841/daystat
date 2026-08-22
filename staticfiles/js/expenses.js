// Whole-row click targets in the desktop expenses table.
(() => {
    document.querySelectorAll(".expense-row").forEach((row) => {
        let startX = 0;
        let startY = 0;

        row.addEventListener("pointerdown", (event) => {
            startX = event.clientX;
            startY = event.clientY;
        });

        row.addEventListener("click", (event) => {
            // a drag is text selection, not a click on the row
            const moved = Math.hypot(event.clientX - startX,
                                     event.clientY - startY);
            if (moved > 8) return;
            // let a real link inside the row do its own job
            if (event.target.closest("a")) return;
            window.location.href = row.dataset.url;
        });
    });

    if (window.location.hash) {
        const target = document.querySelector(window.location.hash);
        if (target) target.scrollIntoView({ behavior: "smooth", block: "center" });
    }
})();
