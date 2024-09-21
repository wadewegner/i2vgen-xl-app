import sys
import os
from dotenv import load_dotenv
import torch
from diffusers import I2VGenXLPipeline
from diffusers.utils import export_to_video
from PIL import Image

# Load environment variables
load_dotenv()

def generate_video(image_path, prompt):
    try:
        use_cuda = os.getenv('USE_CUDA', 'false').lower() == 'true'
        device = "cuda" if use_cuda and torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")

        # Use the token from .env file
        token = os.getenv('HUGGINGFACE_TOKEN')
        if not token:
            raise ValueError("HUGGINGFACE_TOKEN not found in environment variables")
        
        print(f"Token: {token[:5]}...{token[-5:]}")  # Print first and last 5 characters of token

        # Determine dtype based on CUDA availability
        dtype = torch.float16 if use_cuda else torch.float32

        pipeline = I2VGenXLPipeline.from_pretrained("ali-vilab/i2vgen-xl", torch_dtype=dtype, variant="fp16" if use_cuda else None, use_auth_token=token)
        
        if use_cuda:
            pipeline.enable_model_cpu_offload()
        else:
            pipeline = pipeline.to(device)

        image = Image.open(image_path).convert("RGB")

        negative_prompt = "Distorted, discontinuous, Ugly, blurry, low resolution, motionless, static, disfigured, disconnected limbs, Ugly faces, incomplete arms"
        generator = torch.manual_seed(8888)

        frames = pipeline(
            prompt=prompt,
            image=image,
            num_inference_steps=50,
            negative_prompt=negative_prompt,
            guidance_scale=9.0,
            generator=generator
        ).frames[0]

        # Save the video frames as a video file
        video_path = os.path.join('uploads', f"generated_video_{os.path.basename(image_path)}.mp4")
        export_to_video(frames, video_path)
        
        return video_path
    except Exception as e:
        print(f"Error in generate_video: {str(e)}", file=sys.stderr)
        return None

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python videoGenerator.py <image_path> <prompt>", file=sys.stderr)
        sys.exit(1)

    image_path = sys.argv[1]
    prompt = sys.argv[2]

    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    video_path = generate_video(image_path, prompt)
    if video_path:
        print(video_path)
    else:
        print("Error: Failed to generate video", file=sys.stderr)
        sys.exit(1)
