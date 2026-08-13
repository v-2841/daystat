// Random cat from cataas.com, with a spring reveal.
(() => {
    const button = document.getElementById("cat-button");
    const loading = document.getElementById("cat-loading");
    const image = document.getElementById("cat-image");
    if (!button || !loading || !image) return;

    button.addEventListener("click", () => {
        button.classList.add("hidden");
        loading.classList.remove("hidden");
        fetch("https://cataas.com/cat")
            .then((response) => response.blob())
            .then((blob) => {
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
