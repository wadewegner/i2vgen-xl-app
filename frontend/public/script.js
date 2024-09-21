let socket;

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.hostname;
  const wsUrl = `${protocol}//${host}`;
  console.log(`Attempting to connect to WebSocket at ${wsUrl}`);
  socket = new WebSocket(wsUrl);

  socket.onopen = function (event) {
    console.log("WebSocket connection established");
    appendToLog("WebSocket connection established");
  };

  socket.onmessage = function (event) {
    console.log("Received WebSocket message:", event.data);
    try {
      const data = JSON.parse(event.data);
      if (data.type === "log") {
        appendToLog(data.message);
      }
    } catch (error) {
      console.error("Error parsing WebSocket message:", error);
      appendToLog("Error parsing WebSocket message: " + error.message);
    }
  };

  socket.onclose = function (event) {
    console.log("WebSocket connection closed. Reconnecting...");
    appendToLog("WebSocket connection closed. Reconnecting...");
    setTimeout(connectWebSocket, 1000);
  };

  socket.onerror = function (error) {
    console.error("WebSocket error:", error);
    appendToLog("WebSocket error: " + error.message);
  };
}

function appendToLog(message) {
  const logDiv = document.getElementById("logOutput");
  if (logDiv) {
    logDiv.innerHTML += message + "<br>";
    logDiv.scrollTop = logDiv.scrollHeight;
  } else {
    console.error("Log output element not found");
  }
}

connectWebSocket();

document.getElementById("uploadForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const formData = new FormData(e.target);

  // Clear previous log output
  const logDiv = document.getElementById("logOutput");
  if (logDiv) {
    logDiv.innerHTML = "";
    logDiv.style.display = "block";
  }

  appendToLog("Starting video generation process...");

  // Disable the submit button
  const submitButton = e.target.querySelector('button[type="submit"]');
  submitButton.disabled = true;

  try {
    const response = await fetch("/generate-video", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    if (data.videoUrl) {
      appendToLog("Video generated successfully");
      const video = document.getElementById("generatedVideo");
      video.src = data.videoUrl;
      video.onerror = function () {
        console.error("Error loading video:", video.error);
        appendToLog(`Error loading video: ${video.error.message}`);
      };
      video.onloadedmetadata = function () {
        console.log("Video metadata loaded successfully");
        appendToLog("Video metadata loaded successfully");
      };
      video.oncanplay = function () {
        console.log("Video can start playing");
        appendToLog("Video can start playing");
      };
      document.getElementById("result").style.display = "block";
    } else if (data.error) {
      throw new Error(data.error);
    } else {
      throw new Error("Unexpected server response");
    }
  } catch (error) {
    console.error("Error:", error);
    appendToLog(`An error occurred: ${error.message}`);
  } finally {
    // Re-enable the submit button
    submitButton.disabled = false;
  }
});
