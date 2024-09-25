import sys
import os

print("Python version:", sys.version)
print("Python path:", sys.path)
print("Working directory:", os.getcwd())

sys.path.append('/usr/local/lib/python3.10/dist-packages')
sys.path.append('/root/i2vgen-xl-app/venv/lib/python3.10/site-packages')
os.environ['PYTHONPATH'] = os.environ.get('PYTHONPATH', '') + ':/usr/local/lib/python3.10/dist-packages:/root/i2vgen-xl-app/venv/lib/python3.10/site-packages'

try:
    import sentencepiece
    print("SentencePiece version:", sentencepiece.__version__)
except ImportError as e:
    print("Failed to import SentencePiece:", e)

try:
    from transformers import T5Tokenizer
    print("T5Tokenizer imported successfully")
except ImportError as e:
    print("Failed to import T5Tokenizer:", e)

from dotenv import load_dotenv
import torch
import torch.amp
from diffusers import DiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image
import logging
import imageio
import numpy as np
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

def check_cuda_gpu():
    logging.info(f"CUDA available: {torch.cuda.is_available()}")
    logging.info(f"CUDA version: {torch.version.cuda}")
    logging.info(f"Number of GPUs: {torch.cuda.device_count()}")
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            logging.info(f"GPU {i}: {torch.cuda.get_device_name(i)}")

def generate_video(image_path, prompt, num_frames, frame_rate):
    try:
        logging.info("Starting video generation process")
        check_cuda_gpu()

        use_cuda = os.getenv('USE_CUDA', 'false').lower() == 'true'
        device = "cuda" if use_cuda and torch.cuda.is_available() else "cpu"
        logging.info(f"Using device: {device}")

        token = os.getenv('HUGGINGFACE_TOKEN')
        if not token:
            raise ValueError("HUGGINGFACE_TOKEN not found in environment variables")
        
        logging.info(f"Hugging Face Token: {token[:5]}...{token[-5:]}")

        dtype = torch.float16 if use_cuda else torch.float32
        logging.info(f"Using dtype: {dtype}")

        logging.info("Loading DiffusionPipeline")
        pipeline = DiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-2-1",
            torch_dtype=dtype,
            use_auth_token=token
        )
        pipeline.scheduler = DPMSolverMultistepScheduler.from_config(pipeline.scheduler.config)
        
        if use_cuda:
            logging.info("Moving pipeline to GPU and enabling optimizations")
            pipeline = pipeline.to("cuda")
            pipeline.enable_attention_slicing()
        else:
            logging.info("Using CPU for inference")
            pipeline = pipeline.to("cpu")

        logging.info(f"Loading image from {image_path}")
        image = Image.open(image_path).convert("RGB")
        
        # Resize image to 512x512
        image = image.resize((512, 512), Image.LANCZOS)
        logging.info(f"Resized image to 512x512")

        negative_prompt = "Distorted, discontinuous, Ugly, blurry, low detail, unrealistic distortions, low resolution, motionless, static, disfigured, disconnected limbs, Ugly faces, incomplete arms"
        generator = torch.Generator(device=device).manual_seed(8888)

        # Limit the number of frames to 48
        num_frames = min(int(num_frames), 48)
        logging.info(f"Adjusted number of frames: {num_frames}")

        logging.info(f"Generating video frames: {num_frames} frames")
        logging.info(f"CUDA available: {torch.cuda.is_available()}")
        logging.info(f"Current device: {torch.cuda.current_device()}")
        logging.info(f"Device name: {torch.cuda.get_device_name(0)}")

        uploads_dir = '/var/www/i2vgen-xl-app/uploads'

        # Generate a single test image
        logging.info("Generating a single test image")
        single_image = pipeline(
            prompt=prompt,
            image=image,
            negative_prompt=negative_prompt,
            num_inference_steps=50,
            guidance_scale=7.5,
            generator=generator
        ).images[0]

        single_image_path = os.path.join(uploads_dir, "single_generated_image.png")
        single_image.save(single_image_path)
        logging.info(f"Saved single generated image to {single_image_path}")

        logging.info("Starting pipeline execution for video frames")
        video_frames = []
        with torch.amp.autocast(device_type=device):
            for i in range(num_frames):
                logging.info(f"Generating frame {i+1}/{num_frames}")
                frame = pipeline(
                    prompt=prompt,
                    image=image,
                    negative_prompt=negative_prompt,
                    num_inference_steps=50,
                    guidance_scale=7.5,
                    generator=generator
                ).images[0]
                video_frames.append(frame)
                
                # Save each frame as an image
                frame_path = os.path.join(uploads_dir, f"frame_{i:04d}.png")
                frame.save(frame_path)
                logging.info(f"Saved frame to {frame_path}")

                # Check frame content
                frame_array = np.array(frame)
                if np.all(frame_array == 0):
                    logging.warning(f"Frame {i} is completely black")
                else:
                    logging.info(f"Frame {i} has content (min: {frame_array.min()}, max: {frame_array.max()})")

        logging.info("Video frame generation complete")

        # Save first and last frames separately
        first_frame_path = os.path.join(uploads_dir, "first_frame.png")
        last_frame_path = os.path.join(uploads_dir, "last_frame.png")
        video_frames[0].save(first_frame_path)
        video_frames[-1].save(last_frame_path)
        logging.info(f"Saved first frame to {first_frame_path}")
        logging.info(f"Saved last frame to {last_frame_path}")

        # Use ffmpeg to create a video from the frames
        video_path = os.path.join(uploads_dir, f"generated_video_{os.path.basename(image_path)}.mp4")
        
        logging.info("Starting video creation using ffmpeg")
        ffmpeg_cmd = [
            'ffmpeg',
            '-framerate', str(frame_rate),
            '-i', os.path.join(uploads_dir, 'frame_%04d.png'),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-v', 'verbose',  # Add verbose output
            video_path
        ]
        result = subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
        logging.info(f"FFmpeg output: {result.stdout}")
        logging.error(f"FFmpeg errors: {result.stderr}")

        if os.path.exists(video_path):
            video_size = os.path.getsize(video_path)
            logging.info(f"Generated video file size: {video_size} bytes")
            if video_size == 0:
                logging.error("Generated video file is empty")
        else:
            logging.error("Video file was not created")

        print(f"FINAL_VIDEO_PATH:{video_path}")

        return video_path
    except Exception as e:
        logging.error(f"Error in generate_video: {str(e)}", exc_info=True)
        return None

if __name__ == "__main__":
    if len(sys.argv) != 5:
        logging.error("Usage: python videoGenerator.py <image_path> <prompt> <num_frames> <frame_rate>")
        sys.exit(1)

    image_path = sys.argv[1]
    prompt = sys.argv[2]
    num_frames = int(sys.argv[3])
    frame_rate = float(sys.argv[4])

    if not os.path.exists(image_path):
        logging.error(f"Error: Image file not found: {image_path}")
        sys.exit(1)

    video_path = generate_video(image_path, prompt, num_frames, frame_rate)
    if video_path:
        print(f"FINAL_VIDEO_PATH:{video_path}")
    else:
        logging.error("Failed to generate video")
        sys.exit(1)
