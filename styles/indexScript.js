const form = document.getElementById("downloadForm");
const downloadButton = document.getElementById("downloadBtn");
const downloadTypeSelect = document.getElementById("downloadType");
const formatSelect = document.getElementById("format");
const qualitySelect = document.getElementById("quality");
const videoUrlInput = document.getElementById("videoUrl");

downloadTypeSelect.addEventListener("change", function () {
    const isPlaylist = downloadTypeSelect.value === "playlist";
    document.querySelector('label[for="videoUrl"]').textContent = isPlaylist
        ? "Playlist Link"
        : "Video Link";
    videoUrlInput.placeholder = isPlaylist ? "Enter playlist link" : "Enter video link";
});

formatSelect.addEventListener("change", function () {
    qualitySelect.disabled = formatSelect.value === "mp3";
});

form.addEventListener("submit", async function (event) {
    event.preventDefault();

    const videoUrl = videoUrlInput.value;
    const downloadType = downloadTypeSelect.value;
    const format = formatSelect.value;
    const quality = qualitySelect.value;

    const youtubeRegex = /^https?:\/\/(?:[a-z0-9-]+\.)?(?:youtube\.com|youtu\.be)\/.+$/i;

    if (!videoUrl.trim()) {
        displayMessage("Please enter a valid YouTube link!", "danger");
        return;
    }

    if (!youtubeRegex.test(videoUrl)) {
        displayMessage("Invalid YouTube link! Please enter a valid link.", "danger");
        return;
    }

    document.getElementById("loader").classList.remove("d-none");
    document.querySelector("#loader p").textContent = downloadType === "playlist"
        ? "Downloading and packaging the playlist... This may take several minutes."
        : "Preparing your download... This can take a moment.";
    document.getElementById("message").replaceChildren();
    downloadButton.disabled = true;

    try {
        const endpoint = downloadType === "playlist"
            ? "/api/download-playlist"
            : "/api/download";
        const response = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: videoUrl.trim(), format, quality }),
        });

        if (!response.ok) {
            let message = `Download failed (${response.status}).`;
            try {
                const error = await response.json();
                message = error.detail || message;
            } catch (_) {
                // Keep the generic HTTP error when the response is not JSON.
            }
            throw new Error(message);
        }

        const file = await response.blob();
        const disposition = response.headers.get("Content-Disposition") || "";
        const utf8Name = disposition.match(/filename\*=utf-8''([^;]+)/i);
        const plainName = disposition.match(/filename="?([^";]+)"?/i);
        const filename = utf8Name
            ? decodeURIComponent(utf8Name[1])
            : plainName
                ? plainName[1]
                : downloadType === "playlist"
                    ? "youtube-playlist.zip"
                    : `youtube-download.${format}`;

        const objectUrl = URL.createObjectURL(file);
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(objectUrl);

        displayMessage(
            downloadType === "playlist"
                ? "Your playlist ZIP is ready."
                : "Your download is ready.",
            "success",
        );
    } catch (error) {
        displayMessage(error.message, "danger");
    } finally {
        document.getElementById("loader").classList.add("d-none");
        downloadButton.disabled = false;
    }
});

function displayMessage(message, type) {
    const messageDiv = document.getElementById("message");
    const alert = document.createElement("div");
    alert.className = `alert alert-${type}`;
    alert.setAttribute("role", "alert");
    alert.textContent = message;
    messageDiv.replaceChildren(alert);
    setTimeout(() => {
        messageDiv.replaceChildren();
    }, 5000);
}
