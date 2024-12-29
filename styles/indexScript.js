document.getElementById("downloadBtn").addEventListener("click", function () {
    const videoUrl = document.getElementById("videoUrl").value;
    const format = document.getElementById("format").value;
    const quality = document.getElementById("quality").value;

    // Regex to check if the URL is a valid YouTube link
    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$/;

    if (!videoUrl.trim()) {
        displayMessage("Please enter a valid YouTube link!", "danger");
        return;
    }

    if (!youtubeRegex.test(videoUrl)) {
        displayMessage("Invalid YouTube link! Please enter a valid link.", "danger");
        return;
    }

    document.getElementById("loader").classList.remove("d-none");
    document.getElementById("message").innerHTML = "";

    // Simulate downloading
    setTimeout(() => {
        document.getElementById("loader").classList.add("d-none");
        displayMessage("Download started successfully!", "success");
    }, 2000); // Simulated delay
});

function displayMessage(message, type) {
    const messageDiv = document.getElementById("message");
    messageDiv.innerHTML = `<div class="alert alert-${type}" role="alert">${message}</div>`;
    setTimeout(() => {
        messageDiv.innerHTML = "";
    }, 5000);
}
