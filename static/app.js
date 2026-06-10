document.addEventListener("DOMContentLoaded", () => {
    const fileInput = document.getElementById("file-input");
    const preview = document.getElementById("preview");
    const fileLabel = document.getElementById("file-label");
    const analysisResult = document.getElementById("analysis-result");
    const confirmationCard = document.getElementById("confirmation-card");
    const confirmationContainer = document.getElementById("confirmation-container");
    const resetBtn = document.getElementById("reset-btn");

    // Prévisualisation de l'image sélectionnée
    fileInput.addEventListener("change", () => {
        const file = fileInput.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            preview.src = event.target.result;
            preview.classList.remove("hidden");
        };
        reader.readAsDataURL(file);

        fileLabel.textContent = file.name;
    });

    // Après un swap HTMX réussi
    document.body.addEventListener("htmx:afterSwap", (evt) => {
        // Le formulaire d'analyse vient d'être inséré
        if (evt.detail.target.id === "analysis-result") {
            confirmationCard.classList.add("hidden");
            confirmationContainer.innerHTML = "";
            resetBtn.classList.add("hidden");
        }

        // La confirmation de soumission vient d'être insérée
        if (evt.detail.target.id === "confirmation-container") {
            confirmationCard.classList.remove("hidden");
            resetBtn.classList.remove("hidden");
        }
    });

    // En cas d'erreur HTTP (4xx/5xx), HTMX ne swap pas automatiquement :
    // on récupère le fragment d'erreur retourné par le backend et on l'affiche nous-mêmes.
    document.body.addEventListener("htmx:responseError", (evt) => {
        const errorHtml = evt.detail.xhr.responseText;
        const requestPath = evt.detail.requestConfig.path;

        if (requestPath === "/api/submit") {
            confirmationCard.classList.remove("hidden");
            confirmationContainer.innerHTML = errorHtml;
            resetBtn.classList.remove("hidden");
        } else {
            analysisResult.innerHTML = errorHtml;
        }
    });

    // Bouton "Nouvelle note de frais" : on recharge simplement la page
    resetBtn.addEventListener("click", () => {
        location.reload();
    });
});
