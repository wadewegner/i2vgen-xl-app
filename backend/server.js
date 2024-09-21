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
    pythonPath: "/root/i2vgen-xl-app/venv/bin/python", // Adjust this path to your virtual environment
    pythonOptions: ["-u"],
    scriptPath: __dirname,
    args: [imagePath, prompt, numFrames, frameRate],
    env: {
      ...process.env,
      PYTHONUNBUFFERED: "1",
    },
  };

  console.log("Starting video generation process");

  PythonShell.run("videoGenerator.py", options, function (err, results) {
    if (err) {
      console.error("Error running Python script:", err);
      return res
        .status(500)
        .json({ error: "An error occurred while generating the video" });
    }

    console.log("Python script execution completed");
    console.log("Python script output:", results);

    // Process the results
    const videoPathLine = results.find((line) =>
      line.startsWith("FINAL_VIDEO_PATH:")
    );

    if (videoPathLine) {
      const videoPath = videoPathLine.split(":")[1].trim();
      console.log("Generated video path:", videoPath);
      const videoUrl = "/" + videoPath;
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

// Broadcast function to send messages to all connected clients
function broadcast(message) {
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(message));
    }
  });
}

server.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});

// Error handling
process.on("uncaughtException", (error) => {
  console.error("Uncaught Exception:", error);
});

process.on("unhandledRejection", (reason, promise) => {
  console.error("Unhandled Rejection at:", promise, "reason:", reason);
});
