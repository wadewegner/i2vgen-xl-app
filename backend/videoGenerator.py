import sys
import os
from dotenv import load_dotenv
import torch
import cv2
from diffusers import I2VGenXLPipeline
from diffusers.utils import export_to_video
from PIL import Image
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

def generate_video(image_path, prompt):
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
        pipeline = I2VGenXLPipeline.from_pretrained("ali-vilab/i2vgen-xl", torch_dtype=dtype, variant="fp16" if use_cuda else None, use_auth_token=token)
        
        if use_cuda:
            logging.info("Enabling model CPU offload")
            pipeline.enable_model_cpu_offload()
        else:
            logging.info(f"Moving pipeline to {device}")
            pipeline = pipeline.to(device)

        logging.info(f"Loading image from {image_path}")
        image = Image.open(image_path).convert("RGB")

        negative_prompt = "Distorted, discontinuous, Ugly, blurry, low resolution, motionless, static, disfigured, disconnected limbs, Ugly faces, incomplete arms"
        generator = torch.manual_seed(8888)

        logging.info("Generating video frames")
        frames = pipeline(
            prompt=prompt,
            image=image,
            num_inference_steps=50,
            negative_prompt=negative_prompt,
            guidance_scale=9.0,
            generator=generator
        ).frames[0]

        video_path = os.path.join('uploads', f"generated_video_{os.path.basename(image_path)}.mp4")
        logging.info(f"Exporting video to {video_path}")
        export_to_video(frames, video_path)
        
        logging.info("Video generation complete")
        return video_path
    except Exception as e:
        logging.error(f"Error in generate_video: {str(e)}", exc_info=True)
        return None

if __name__ == "__main__":
    if len(sys.argv) != 3:
        logging.error("Usage: python videoGenerator.py <image_path> <prompt>")
        sys.exit(1)

    image_path = sys.argv[1]
    prompt = sys.argv[2]

    if not os.path.exists(image_path):
        logging.error(f"Error: Image file not found: {image_path}")
        sys.exit(1)

    video_path = generate_video(image_path, prompt)
    if video_path:
        print(video_path)
    else:
        logging.error("Failed to generate video")
        sys.exit(1)
