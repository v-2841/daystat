// Shared UI behaviour: theme toggle, profile menu, entrance animation.
(() => {
    const root = document.documentElement;

    // ---------------------------------------------------------- theme
    const toggle = document.getElementById("theme-toggle");
    if (toggle) {
        toggle.addEventListener("click", () => {
            const dark = !root.classList.contains("dark");
            root.classList.toggle("dark", dark);
            localStorage.setItem("daystat-theme", dark ? "dark" : "light");
            toggle.classList.remove("animate-pop");
            void toggle.offsetWidth;
            toggle.classList.add("animate-pop");
            document.dispatchEvent(
                new CustomEvent("daystat:theme", { detail: { dark } })
            );
        });
    }

    window
        .matchMedia("(prefers-color-scheme: dark)")
        .addEventListener("change", (event) => {
            if (localStorage.getItem("daystat-theme")) return;
            root.classList.toggle("dark", event.matches);
            document.dispatchEvent(
                new CustomEvent("daystat:theme", {
                    detail: { dark: event.matches },
                })
            );
        });

    // ----------------------------------------------------- profile menu
    document.querySelectorAll("[data-menu]").forEach((menu) => {
        const button = menu.querySelector("[data-menu-button]");
        const panel = menu.querySelector("[data-menu-panel]");
        if (!button || !panel) return;

        const close = () => {
            panel.classList.add("hidden");
            button.setAttribute("aria-expanded", "false");
        };

        button.addEventListener("click", (event) => {
            event.stopPropagation();
            const open = panel.classList.toggle("hidden");
            button.setAttribute("aria-expanded", open ? "false" : "true");
            if (!open) panel.classList.add("animate-rise");
        });

        document.addEventListener("click", (event) => {
            if (!menu.contains(event.target)) close();
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") close();
        });
    });

    // ---------------------------------------------------------- dialogs
    document.querySelectorAll("[data-dialog-open]").forEach((button) => {
        const dialog = document.getElementById(button.dataset.dialogOpen);
        if (!dialog) return;
        button.addEventListener("click", () => dialog.showModal());
        dialog
            .querySelectorAll("[data-dialog-close]")
            .forEach((close) => close.addEventListener("click", () => dialog.close()));
    });

    // ------------------------------------------------ entrance animation
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!reduced) {
        document.querySelectorAll("[data-stagger]").forEach((group) => {
            [...group.children].forEach((child, index) => {
                child.style.animationDelay = `${Math.min(index * 55, 400)}ms`;
                child.classList.add("animate-rise");
            });
        });
    }
})();
