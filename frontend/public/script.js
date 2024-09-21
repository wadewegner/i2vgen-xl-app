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

    const data = await response.json();

    if (data.videoUrl) {
      document.getElementById("generatedVideo").src = data.videoUrl;
      document.getElementById("result").style.display = "block";
    } else {
      alert("Error generating video");
    }
  } catch (error) {
    console.error("Error:", error);
    alert("An error occurred while generating the video");
  }
});
