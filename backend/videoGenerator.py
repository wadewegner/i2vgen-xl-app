import sys
import os

# Add these lines at the beginning of the file
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
from diffusers import CogVideoXImageToVideoPipeline
from PIL import Image
import logging
import imageio
import numpy as np

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

        dtype = torch.bfloat16 if use_cuda else torch.float32
        logging.info(f"Using dtype: {dtype}")

        logging.info("Loading CogVideoXImageToVideoPipeline")
        pipeline = CogVideoXImageToVideoPipeline.from_pretrained(
            "THUDM/CogVideoX-5b-I2V",
            torch_dtype=dtype,
            use_auth_token=token
        )
        
        if use_cuda:
            logging.info("Moving pipeline to GPU and enabling optimizations")
            pipeline = pipeline.to("cuda")
            pipeline.enable_sequential_cpu_offload()
            pipeline.vae.enable_tiling()
            pipeline.vae.enable_slicing()
        else:
            logging.info("Using CPU for inference")
            pipeline = pipeline.to("cpu")

        logging.info(f"Loading image from {image_path}")
        image = Image.open(image_path).convert("RGB")
        
        # Resize image to 512x512 (default resolution for the model)
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

        logging.info("Starting pipeline execution")
        with torch.amp.autocast(device_type=device):
            video_frames = pipeline(
                prompt=prompt,
                image=image,
                num_inference_steps=50,
                num_frames=num_frames,
                negative_prompt=negative_prompt,
                guidance_scale=6.0,
                generator=generator
            ).frames[0]

        logging.info("Video frame generation complete")

        # Convert frames to numpy arrays
        video_frames_np = [np.array(frame) for frame in video_frames]

        # Use imageio to create a video from the frames
        uploads_dir = '/var/www/i2vgen-xl-app/uploads'
        video_path = os.path.join(uploads_dir, f"generated_video_{os.path.basename(image_path)}.mp4")
        
        writer = imageio.get_writer(video_path, fps=frame_rate)
        for frame in video_frames_np:
            writer.append_data(frame)
        writer.close()

        logging.info(f"Video saved to {video_path}")
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
