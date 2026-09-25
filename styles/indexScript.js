const form = document.getElementById("downloadForm");
const downloadButton = document.getElementById("downloadBtn");
const downloadTypeSelect = document.getElementById("downloadType");
const formatSelect = document.getElementById("format");
const qualitySelect = document.getElementById("quality");
const videoUrlInput = document.getElementById("videoUrl");
const mediaInfo = document.getElementById("mediaInfo");
const loader = document.getElementById("loader");
const loaderText = document.querySelector("#loader p");
const youtubeRegex = /^https?:\/\/(?:[a-z0-9-]+\.)?(?:youtube\.com|youtu\.be)\/.+$/i;

let infoRequestToken = 0;
let infoDebounce;
let loadedMediaKey = "";

function currentMediaKey() {
    return `${downloadTypeSelect.value}:${videoUrlInput.value.trim()}`;
}

function resetQualities(label = "Enter a link to load qualities") {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = label;
    qualitySelect.replaceChildren(option);
    qualitySelect.disabled = true;
}

function populateQualities(qualities) {
    const ordered = [...qualities].sort(
        (left, right) => Number.parseInt(right, 10) - Number.parseInt(left, 10),
    );
    const options = ordered.map((quality) => {
        const option = document.createElement("option");
        option.value = quality;
        option.textContent = quality;
        return option;
    });
    qualitySelect.replaceChildren(...options);

    const preferred = ordered.find((quality) => Number.parseInt(quality, 10) <= 1080);
    qualitySelect.value = preferred || ordered[0];
    qualitySelect.disabled = formatSelect.value === "mp3";
}

async function loadMediaInfo(showErrors = false) {
    const url = videoUrlInput.value.trim();
    const requestKey = currentMediaKey();
    const requestToken = ++infoRequestToken;

    if (!url || !youtubeRegex.test(url)) {
        loadedMediaKey = "";
        mediaInfo.textContent = "";
        resetQualities();
        return false;
    }

    resetQualities("Loading available qualities...");
    mediaInfo.textContent = downloadTypeSelect.value === "playlist"
        ? "Checking every video in the playlist..."
        : "Checking video...";

    try {
        const params = new URLSearchParams({
            url,
            download_type: downloadTypeSelect.value,
        });
        const response = await fetch(`/api/media-info?${params}`);
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || `Could not read this link (${response.status}).`);
        }
        if (requestToken !== infoRequestToken) {
            return false;
        }
        if (!result.qualities?.length) {
            throw new Error("No downloadable video qualities were found.");
        }

        populateQualities(result.qualities);
        loadedMediaKey = requestKey;
        const countLabel = result.count > 1 ? ` · ${result.count} videos` : "";
        const warning = result.metadata_failures
            ? ` · ${result.metadata_failures} item(s) could not be inspected`
            : "";
        mediaInfo.textContent = `${result.title}${countLabel}${warning}`;
        return true;
    } catch (error) {
        if (requestToken !== infoRequestToken) {
            return false;
        }
        loadedMediaKey = "";
        mediaInfo.textContent = "";
        resetQualities("Could not load qualities");
        if (showErrors) {
            displayMessage(error.message, "danger");
        }
        return false;
    }
}

function scheduleMediaInfo() {
    clearTimeout(infoDebounce);
    loadedMediaKey = "";
    infoDebounce = setTimeout(() => loadMediaInfo(false), 700);
}

downloadTypeSelect.addEventListener("change", function () {
    const isPlaylist = downloadTypeSelect.value === "playlist";
    document.querySelector('label[for="videoUrl"]').textContent = isPlaylist
        ? "Playlist Link"
        : "Video Link";
    videoUrlInput.placeholder = isPlaylist ? "Enter playlist link" : "Enter video link";
    scheduleMediaInfo();
});

formatSelect.addEventListener("change", function () {
    if (formatSelect.value === "mp3") {
        qualitySelect.disabled = true;
    } else if (loadedMediaKey === currentMediaKey()) {
        qualitySelect.disabled = false;
    } else {
        scheduleMediaInfo();
    }
});

videoUrlInput.addEventListener("input", scheduleMediaInfo);
videoUrlInput.addEventListener("blur", () => loadMediaInfo(false));

form.addEventListener("submit", async function (event) {
    event.preventDefault();

    const videoUrl = videoUrlInput.value.trim();
    const downloadType = downloadTypeSelect.value;
    const format = formatSelect.value;

    if (!videoUrl || !youtubeRegex.test(videoUrl)) {
        displayMessage("Please enter a valid YouTube link.", "danger");
        return;
    }

    loader.classList.remove("d-none");
    document.getElementById("message").replaceChildren();
    downloadButton.disabled = true;

    try {
        if (format === "mp4" && loadedMediaKey !== currentMediaKey()) {
            loaderText.textContent = "Checking available qualities...";
            if (!await loadMediaInfo(true)) {
                return;
            }
        }

        const quality = qualitySelect.value || "720p";
        loaderText.textContent = downloadType === "playlist"
            ? "Downloading and packaging the playlist... This may take several minutes."
            : "Preparing your download... This can take a moment.";

        const endpoint = downloadType === "playlist"
            ? "/api/download-playlist"
            : "/api/download";
        const response = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: videoUrl, format, quality }),
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
        loader.classList.add("d-none");
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
        if (messageDiv.contains(alert)) {
            messageDiv.replaceChildren();
        }
    }, 8000);
}
