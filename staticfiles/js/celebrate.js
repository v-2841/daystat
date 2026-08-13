// Confetti burst + mascot wiggle after a successful save.
(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const cat = document.getElementById("day-cat");
    if (cat) {
        cat.classList.add("animate-wiggle");
        cat.addEventListener("animationend", () =>
            cat.classList.remove("animate-wiggle")
        );
    }

    const COLORS = ["#991a7d", "#fdc3f5", "#f5b544", "#34c9a3", "#58a6f5"];
    const layer = document.createElement("div");
    layer.style.cssText =
        "position:fixed;inset:0;pointer-events:none;z-index:60;overflow:hidden";
    document.body.appendChild(layer);

    const origin = cat ? cat.getBoundingClientRect() : null;
    const startX = origin ? origin.left + origin.width / 2 : innerWidth / 2;
    const startY = origin ? origin.top + origin.height / 2 : innerHeight / 3;

    for (let i = 0; i < 70; i += 1) {
        const bit = document.createElement("i");
        const size = 6 + Math.random() * 7;
        bit.style.cssText = `
            position:absolute;left:${startX}px;top:${startY}px;
            width:${size}px;height:${size * 0.6}px;
            background:${COLORS[i % COLORS.length]};
            border-radius:${Math.random() > 0.5 ? "999px" : "2px"};
            will-change:transform,opacity`;
        layer.appendChild(bit);

        const angle = Math.random() * Math.PI * 2;
        const distance = 90 + Math.random() * 240;
        bit.animate(
            [
                { transform: "translate(0,0) rotate(0deg)", opacity: 1 },
                {
                    transform: `translate(${Math.cos(angle) * distance}px, ${
                        Math.sin(angle) * distance + 220
                    }px) rotate(${Math.random() * 720 - 360}deg)`,
                    opacity: 0,
                },
            ],
            {
                duration: 1100 + Math.random() * 700,
                easing: "cubic-bezier(.2,.7,.35,1)",
                fill: "forwards",
            }
        );
    }

    setTimeout(() => layer.remove(), 2200);

    // drop the ?saved=1 flag so a refresh doesn't replay the celebration
    const url = new URL(window.location.href);
    url.searchParams.delete("saved");
    window.history.replaceState({}, "", url);
})();
