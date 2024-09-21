let socket;

function connectWebSocket() {
  socket = new WebSocket("ws://" + window.location.host);

  socket.onmessage = function (event) {
    const data = JSON.parse(event.data);
    if (data.type === "log") {
      appendLog(data.message);
    }
  };

  socket.onclose = function (event) {
    console.log("WebSocket connection closed. Reconnecting...");
    setTimeout(connectWebSocket, 1000);
  };

  socket.onerror = function (error) {
    console.error("WebSocket error:", error);
  };
}

function appendLog(message) {
  const logDiv = document.getElementById("logOutput");
  logDiv.innerHTML += message + "<br>";
  logDiv.scrollTop = logDiv.scrollHeight;
}

connectWebSocket();

document.getElementById("uploadForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const formData = new FormData();
  formData.append("image", document.getElementById("imageInput").files[0]);
  formData.append("prompt", document.getElementById("promptInput").value);
  formData.append("numFrames", document.getElementById("numFrames").value);
  formData.append("frameRate", document.getElementById("frameRate").value);

  // Clear previous log output
  document.getElementById("logOutput").innerHTML = "";

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
      const video = document.getElementById("generatedVideo");
      video.src = data.videoUrl;
      video.onerror = function () {
        console.error("Error loading video:", video.error);
        alert(`Error loading video: ${video.error.message}`);
      };
      video.onloadedmetadata = function () {
        console.log("Video metadata loaded successfully");
      };
      video.oncanplay = function () {
        console.log("Video can start playing");
      };
      document.getElementById("result").style.display = "block";
    } else {
      throw new Error("No video URL in response");
    }
  } catch (error) {
    console.error("Error:", error);
    alert(`An error occurred: ${error.message}`);
  }
});
