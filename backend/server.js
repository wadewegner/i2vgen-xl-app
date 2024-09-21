const express = require("express");
const multer = require("multer");
const path = require("path");
const fs = require("fs");
const { PythonShell } = require("python-shell");
const WebSocket = require("ws");
const http = require("http");
require("dotenv").config();

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const port = process.env.PORT || 3000;

app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "../frontend/views"));
app.use(express.static(path.join(__dirname, "../frontend/public")));

// Update the path to the new uploads directory
const uploadsDir = "/var/www/i2vgen-xl-app/uploads";

// Serve files from the uploads directory
app.use("/uploads", express.static(uploadsDir));

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
    cb(null, uploadsDir);
  },
  filename: (req, file, cb) => {
    cb(null, Date.now() + path.extname(file.originalname));
  },
});

const upload = multer({
  storage: storage,
  limits: { fileSize: 50 * 1024 * 1024 }, // 50 MB limit
});

app.get("/", (req, res) => {
  res.render("index");
});

app.post("/generate-video", upload.single("image"), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: "No file uploaded" });
  }

  const { prompt, numFrames, frameRate } = req.body;
  const imagePath = req.file.path;

  console.log("Received request to generate video:");
  console.log("Image path:", imagePath);
  console.log("Prompt:", prompt);
  console.log("Number of frames:", numFrames);
  console.log("Frame rate:", frameRate);

  let options = {
    mode: "text",
    pythonPath: "/root/i2vgen-xl-app/venv/bin/python", // Make sure this path is correct
    pythonOptions: ["-u"],
    scriptPath: __dirname,
    args: [imagePath, prompt, numFrames, frameRate],
    env: {
      ...process.env,
      PYTHONUNBUFFERED: "1",
    },
  };

  console.log("Starting video generation process");

  const pyshell = new PythonShell("videoGenerator.py", options);

  pyshell.on("message", function (message) {
    console.log("Python output:", message);
    // Send this message to all connected WebSocket clients
    wss.clients.forEach(function each(client) {
      if (client.readyState === WebSocket.OPEN) {
        client.send(JSON.stringify({ type: "log", message: message }));
      }
    });
  });

  pyshell.end(function (err, code, signal) {
    if (err) {
      console.error("Python script error:", err);
      return res
        .status(500)
        .json({ error: "An error occurred while generating the video" });
    }

    console.log("Python script execution completed");
    console.log("Python script exit code:", code);

    // Process the results
    const videoPathLine = pyshell.messages.find((msg) =>
      msg.startsWith("FINAL_VIDEO_PATH:")
    );
    console.log("Video path line:", videoPathLine);

    if (videoPathLine) {
      const videoPath = videoPathLine.split(":")[1].trim();
      console.log("Generated video path:", videoPath);
      const videoUrl = "/uploads/" + path.basename(videoPath);
      console.log("Video URL:", videoUrl);
      res.json({ videoUrl: videoUrl });
    } else {
      console.error("Video path not found in Python script output");
      res.status(500).json({ error: "Failed to generate video" });
    }
  });
});

wss.on("connection", (ws) => {
  console.log("New WebSocket connection");

  ws.on("message", (message) => {
    console.log("Received message:", message);
  });

  ws.on("close", () => {
    console.log("WebSocket connection closed");
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).send("Something broke!");
});

// 404 handler
app.use((req, res, next) => {
  res.status(404).send("Sorry, that route doesn't exist.");
});

server.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});

// Graceful shutdown
process.on("SIGTERM", () => {
  console.log("SIGTERM signal received: closing HTTP server");
  server.close(() => {
    console.log("HTTP server closed");
  });
});
