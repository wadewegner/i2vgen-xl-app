document.getElementById("uploadForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const formData = new FormData();
  formData.append("image", document.getElementById("imageInput").files[0]);
  formData.append("prompt", document.getElementById("promptInput").value);

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
