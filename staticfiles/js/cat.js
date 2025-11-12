let catButton = document.getElementById("cat-button");
let catLoading = document.getElementById("cat-loading");
let catImage = document.getElementById("cat-image");

catButton.addEventListener("click", () => {
    catButton.classList.add("d-none");
    catLoading.classList.remove("d-none");
    fetch("https://cataas.com/cat")
        .then((response) => response.blob())
        .then((blob) => {
            catImage.src = URL.createObjectURL(blob);
        })
        .then(() => {
            catLoading.classList.add("d-none");
            catImage.classList.remove("d-none");
        })
        .catch((error) => console.error("Ошибка загрузки:", error));
});
