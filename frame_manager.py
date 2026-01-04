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
    request_path = os.path.expanduser("~/display_request.txt")

    print(f"Frame manager received Source path: {sd_path}")

    # Create the directory if it doesn't exist
    # This is where the images will be stored
    os.makedirs(PIC_PATH, exist_ok=True)

    image_converter = ImageConverter(source_dir=sd_path, output_dir=PIC_PATH)
    print("Image converter created")

    display_manager = DisplayManager(image_folder=PIC_PATH, request_file=request_path, image_converter=image_converter)
    print("Display manager created")

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
