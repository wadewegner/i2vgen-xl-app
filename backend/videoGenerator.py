import sys
import os
from dotenv import load_dotenv
import torch
import torch.amp
from diffusers import I2VGenXLPipeline
from PIL import Image
import subprocess
import logging

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

        logging.info("Loading I2VGenXLPipeline")
        pipeline = I2VGenXLPipeline.from_pretrained(
            "ali-vilab/i2vgen-xl", 
            torch_dtype=dtype, 
            variant="fp16" if use_cuda else None, 
            use_auth_token=token
        )
        
        if use_cuda:
            logging.info("Moving pipeline to GPU and enabling memory efficient attention")
            pipeline = pipeline.to("cuda")
            pipeline.enable_attention_slicing()
        else:
            logging.info("Using CPU for inference")
            pipeline = pipeline.to("cpu")

        logging.info(f"Loading image from {image_path}")
        image = Image.open(image_path).convert("RGB")
        
        # Determine aspect ratio
        width, height = image.size
        aspect_ratio = width / height
        
        # Set video dimensions based on aspect ratio
        if aspect_ratio > 1:  # Landscape
            video_width, video_height = 512, int(512 / aspect_ratio)
        else:  # Portrait or square
            video_width, video_height = int(512 * aspect_ratio), 512
        
        # Resize image
        image = image.resize((video_width, video_height), Image.LANCZOS)

        negative_prompt = "Distorted, discontinuous, Ugly, blurry, low resolution, motionless, static, disfigured, disconnected limbs, Ugly faces, incomplete arms"
        generator = torch.manual_seed(8888)

        logging.info(f"Generating video frames: {num_frames} frames")
        logging.info(f"CUDA available: {torch.cuda.is_available()}")
        logging.info(f"Current device: {torch.cuda.current_device()}")
        logging.info(f"Device name: {torch.cuda.get_device_name(0)}")

        logging.info("Starting pipeline execution")
        with torch.amp.autocast(device_type='cuda' if use_cuda else 'cpu'):
            frames = pipeline(
                prompt=prompt,
                image=image,
                num_inference_steps=50,
                num_frames=int(num_frames),
                negative_prompt=negative_prompt,
                guidance_scale=9.0,
                generator=generator,
                width=video_width,
                height=video_height
            ).frames[0]

        logging.info("Video frame generation complete")

        # Use FFmpeg to create a video from the frames
        uploads_dir = '/var/www/i2vgen-xl-app/uploads'
        video_path = os.path.join(uploads_dir, f"generated_video_{os.path.basename(image_path)}.mp4")
        
        # Save frames as individual PNG files
        frames_dir = os.path.join(uploads_dir, 'frames')
        os.makedirs(frames_dir, exist_ok=True)
        for i, frame in enumerate(frames):
            frame.save(os.path.join(frames_dir, f'frame_{i:04d}.png'))

        ffmpeg_command = [
            'ffmpeg',
            '-framerate', str(frame_rate),
            '-i', os.path.join(frames_dir, 'frame_%04d.png'),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-y',  # Overwrite output file if it exists
            video_path
        ]
        subprocess.run(ffmpeg_command, check=True)

        logging.info(f"Video saved to {video_path}")
        print(f"FINAL_VIDEO_PATH:{video_path}")
        
        # Clean up individual frame files
        for file in os.listdir(frames_dir):
            os.remove(os.path.join(frames_dir, file))
        os.rmdir(frames_dir)

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
