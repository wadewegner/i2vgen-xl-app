import sys
from diffusers import I2VGenXLPipeline
import torch
from PIL import Image

def generate_video(image_path, prompt):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    pipe = I2VGenXLPipeline.from_pretrained("microsoft/i2vgen-xl", torch_dtype=torch.float16)
    pipe = pipe.to(device)

    image = Image.open(image_path)
    video_frames = pipe(prompt, image=image, num_inference_steps=50, num_frames=16).frames[0]
    
    # Save the video frames as a video file
    video_path = f"generated_video_{image_path.split('/')[-1]}.mp4"
    video_frames[0].save(video_path, save_all=True, append_images=video_frames[1:], duration=100, loop=0)
    
    return video_path

if __name__ == "__main__":
    image_path = sys.argv[1]
    prompt = sys.argv[2]
    video_path = generate_video(image_path, prompt)
    print(video_path)
