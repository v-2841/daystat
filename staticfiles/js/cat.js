// Random cat from cataas.com, with a spring reveal.
(() => {
    const button = document.getElementById("cat-button");
    const loading = document.getElementById("cat-loading");
    const image = document.getElementById("cat-image");
    if (!button || !loading || !image) return;

    button.addEventListener("click", () => {
        button.classList.add("hidden");
        loading.textContent = "Ищем котика...";
        loading.classList.remove("hidden");
        fetch("https://cataas.com/cat")
            .then((response) => {
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                return response.blob();
            })
            .then((blob) => {
                // the previous cat would otherwise stay in memory
                if (image.src.startsWith("blob:")) {
                    URL.revokeObjectURL(image.src);
                }
                image.src = URL.createObjectURL(blob);
                loading.classList.add("hidden");
                image.classList.remove("hidden");
                image.classList.add("animate-rise");
                button.classList.remove("hidden");
                button.querySelector("span").textContent = "Ещё котика!";
            })
            .catch(() => {
                loading.textContent = "Котик не пришёл, попробуйте ещё раз";
                button.classList.remove("hidden");
            });
    });
})();
