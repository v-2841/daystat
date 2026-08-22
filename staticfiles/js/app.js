// Shared UI behaviour: theme toggle, profile menu, entrance animation.
(() => {
    const root = document.documentElement;

    // the browser chrome should follow the chosen theme, not the OS one
    const paintChrome = (dark) => {
        document.querySelectorAll('meta[name="theme-color"]').forEach((tag) => {
            tag.media = "";
            tag.content = dark
                ? tag.dataset.dark || "#2c0724"
                : tag.dataset.light || "#fdd8f6";
        });
    };
    paintChrome(root.classList.contains("dark"));

    // ---------------------------------------------------------- theme
    const toggle = document.getElementById("theme-toggle");
    if (toggle) {
        toggle.addEventListener("click", () => {
            const dark = !root.classList.contains("dark");
            root.classList.toggle("dark", dark);
            localStorage.setItem("daystat-theme", dark ? "dark" : "light");
            paintChrome(dark);
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
            paintChrome(event.matches);
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

        const close = ({ restoreFocus = false } = {}) => {
            if (panel.classList.contains("hidden")) return;
            // keyboard users must not be dropped back to the page start
            if (restoreFocus || panel.contains(document.activeElement)) {
                button.focus();
            }
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
            if (event.key === "Escape") close({ restoreFocus: true });
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
