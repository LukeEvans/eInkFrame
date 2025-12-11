from image_converter import ImageConverter
from display_manager import DisplayManager
import os
import shutil
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PIC_PATH = os.path.join(SCRIPT_DIR, 'pic')

if __name__ == "__main__":

    # Define source path and config path
    sd_path = os.path.expanduser("~/images")
    config_path = os.path.expanduser("~/config.txt")
    
    # Get refresh time from config or default
    refresh_time = 600
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                content = f.read().strip()
                if content.isdigit():
                    refresh_time = int(content)
        except Exception as e:
            print(f"Error reading config: {e}")

    print(f"Frame manager received Source path: {sd_path}")
    print(f"Frame manager received refresh time: {refresh_time} seconds")
    
    display_manager = DisplayManager(image_folder=PIC_PATH, refresh_time=refresh_time)
    print("Display manager created")

    # Delete existing directory and create a new one
    # This is where the images will be stored
    if os.path.exists(PIC_PATH):
        shutil.rmtree(PIC_PATH)
    os.makedirs(PIC_PATH)

    image_converter = ImageConverter(source_dir=sd_path, output_dir=PIC_PATH)
    print("Image converter created")

    # Process images from the SD card
    display_manager.display_message('start.jpg')
    try:
        print("Processing images, please wait...")
        image_converter.process_images()
    except Exception as e:
        print(f"Error during image processing: {e}")

    # Start displaying images
    try:
        display_manager.display_images()
    except Exception as e:
        print(f"Error during image display: {e}")
