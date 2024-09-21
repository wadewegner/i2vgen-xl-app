const express = require("express");
const multer = require("multer");
const path = require("path");
const { PythonShell } = require("python-shell");

const app = express();
const port = 3000;

app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "../frontend/views"));
app.use(express.static(path.join(__dirname, "../frontend/public")));

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, "uploads/");
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
  const { prompt } = req.body;
  const imagePath = req.file.path;

  let options = {
    mode: "text",
    pythonPath: "python3",
    pythonOptions: ["-u"],
    scriptPath: "./backend",
    args: [imagePath, prompt],
  };

  PythonShell.run("videoGenerator.py", options)
    .then((results) => {
      console.log("Results:", results);
      res.json({ videoUrl: results[0] });
    })
    .catch((err) => {
      console.error(err);
      res
        .status(500)
        .json({ error: "An error occurred while generating the video" });
    });
});

app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});
