import sys
import os
from dotenv import load_dotenv
import torch
import torch.amp
from diffusers import I2VGenXLPipeline
from PIL import Image
import subprocess

# Load environment variables
load_dotenv()

def check_cuda_gpu():
    print(f"CUDA available: {torch.cuda.is_available()}")
    print(f"CUDA version: {torch.version.cuda}")
    print(f"Number of GPUs: {torch.cuda.device_count()}")
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            print(f"GPU {i}: {torch.cuda.get_device_name(i)}")

def generate_video(image_path, prompt, num_frames, frame_rate):
    try:
        print("Starting video generation process")
        check_cuda_gpu()

        use_cuda = os.getenv('USE_CUDA', 'false').lower() == 'true'
        device = "cuda" if use_cuda and torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")

        token = os.getenv('HUGGINGFACE_TOKEN')
        if not token:
            raise ValueError("HUGGINGFACE_TOKEN not found in environment variables")
        
        print(f"Hugging Face Token: {token[:5]}...{token[-5:]}")

        dtype = torch.float16 if use_cuda else torch.float32
        print(f"Using dtype: {dtype}")

        print("Loading I2VGenXLPipeline")
        pipeline = I2VGenXLPipeline.from_pretrained(
            "ali-vilab/i2vgen-xl", 
            torch_dtype=dtype, 
            variant="fp16" if use_cuda else None, 
            token=token
        )
        
        if use_cuda:
            print("Moving pipeline to GPU and enabling memory efficient attention")
            pipeline = pipeline.to("cuda")
            pipeline.enable_attention_slicing()
        else:
            print("Using CPU for inference")
            pipeline = pipeline.to("cpu")

        print(f"Loading image from {image_path}")
        image = Image.open(image_path).convert("RGB")

        negative_prompt = "Distorted, discontinuous, Ugly, blurry, low resolution, motionless, static, disfigured, disconnected limbs, Ugly faces, incomplete arms"
        generator = torch.manual_seed(8888)

        print(f"Generating video frames: {num_frames} frames")
        print(f"CUDA available: {torch.cuda.is_available()}")
        print(f"Current device: {torch.cuda.current_device()}")
        print(f"Device name: {torch.cuda.get_device_name(0)}")

        print("Starting pipeline execution")
        with torch.amp.autocast(device_type='cuda' if use_cuda else 'cpu'):
            frames = pipeline(
                prompt=prompt,
                image=image,
                num_inference_steps=50,
                num_frames=int(num_frames),
                negative_prompt=negative_prompt,
                guidance_scale=9.0,
                generator=generator
            ).frames[0]

        print("Video frame generation complete")

        # Save frames as individual PNG files
        frames_dir = os.path.join('uploads', 'frames')
        os.makedirs(frames_dir, exist_ok=True)
        for i, frame in enumerate(frames):
            frame.save(os.path.join(frames_dir, f'frame_{i:04d}.png'))

        # Use FFmpeg to create a video from the frames
        video_path = os.path.join('uploads', f"generated_video_{os.path.basename(image_path)}.mp4")
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

        print(f"Video saved to {video_path}")
        print(f"FINAL_VIDEO_PATH:{video_path}")  # Add this line
        
        # Clean up individual frame files
        for file in os.listdir(frames_dir):
            os.remove(os.path.join(frames_dir, file))
        os.rmdir(frames_dir)

        return video_path
    except Exception as e:
        print(f"Error in generate_video: {str(e)}")
        return None

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python videoGenerator.py <image_path> <prompt> <num_frames> <frame_rate>")
        sys.exit(1)

    image_path = sys.argv[1]
    prompt = sys.argv[2]
    num_frames = int(sys.argv[3])
    frame_rate = float(sys.argv[4])

    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        sys.exit(1)

    video_path = generate_video(image_path, prompt, num_frames, frame_rate)
    if video_path:
        print(f"FINAL_VIDEO_PATH:{video_path}")  # Add this line
    else:
        print("Failed to generate video")
        sys.exit(1)
