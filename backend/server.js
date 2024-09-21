const express = require("express");
const multer = require("multer");
const path = require("path");
const fs = require("fs");
const { PythonShell } = require("python-shell");
const http = require("http");
const WebSocket = require("ws");
require("dotenv").config();

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

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

  const pyshell = new PythonShell("videoGenerator.py", options);

  pyshell.on("message", function (message) {
    console.log(message);
    // Broadcast the message to all connected clients
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
    console.log("Python script finished");
    const videoUrl = "/uploads/" + path.basename(code); // Assuming the last line of output is the video path
    res.json({ videoUrl: videoUrl });
  });
});

wss.on("connection", function connection(ws) {
  console.log("New WebSocket connection");
});

server.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});
