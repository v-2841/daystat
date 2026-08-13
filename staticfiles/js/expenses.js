// Whole-row click targets in the desktop expenses table.
(() => {
    document.querySelectorAll(".expense-row").forEach((row) => {
        row.addEventListener("click", () => {
            window.location.href = row.dataset.url;
        });
    });

    if (window.location.hash) {
        const target = document.querySelector(window.location.hash);
        if (target) target.scrollIntoView({ behavior: "smooth", block: "center" });
    }
})();
