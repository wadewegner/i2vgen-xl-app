const express = require("express");
const multer = require("multer");
const path = require("path");
const fs = require("fs");
const { PythonShell } = require("python-shell");
require("dotenv").config();

const app = express();
const port = 3000;

app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "../frontend/views"));
app.use(express.static(path.join(__dirname, "../frontend/public")));

// Serve files from the uploads directory
app.use("/uploads", express.static(path.join(__dirname, "../uploads")));

// Set correct headers for video files
app.use("/uploads", (req, res, next) => {
  if (path.extname(req.url) === ".mp4") {
    res.setHeader("Content-Type", "video/mp4");
    res.setHeader("Accept-Ranges", "bytes");
    res.setHeader("Cache-Control", "public, max-age=3600");
  }
  next();
});

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, path.join(__dirname, "../uploads"));
  },
  filename: (req, file, cb) => {
    cb(null, Date.now() + path.extname(file.originalname));
  },
});

const upload = multer({ storage: storage });

app.get("/", (req, res) => {
  res.render("index");
});

app.post("/generate-video", upload.single("image"), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: "No file uploaded" });
  }

  const { prompt, numFrames, frameRate } = req.body;
  const imagePath = req.file.path;

  let options = {
    mode: "text",
    pythonPath: "python3",
    pythonOptions: ["-u"],
    scriptPath: path.join(__dirname),
    args: [imagePath, prompt, numFrames, frameRate],
    env: {
      ...process.env,
      PYTHONUNBUFFERED: "1",
    },
  };

  console.log("Starting video generation process");

  PythonShell.run("videoGenerator.py", options, function (err, results) {
    if (err) {
      console.error("Python script error:", err);
      return res
        .status(500)
        .json({ error: "An error occurred while generating the video" });
    }
    console.log("Python script output:", results);
    const videoUrl = results[results.length - 1]; // The last line should be the video path
    res.json({ videoUrl: videoUrl });
  });
});

// Add a route for testing video playback
app.get("/test-video", (req, res) => {
  res.sendFile(path.join(__dirname, "test_video.html"));
});

app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});
