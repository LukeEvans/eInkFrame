import os
import sys
import time
import random
from PIL import Image
from lib.waveshare_epd import epd7in3e

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_PATH = os.path.join(SCRIPT_DIR, 'lib')
sys.path.append(LIB_PATH)

class DisplayManager:
    """
    Class to manage the display of images on the e-Paper screen.
    """

    # Initializes the display using the epd7in3f library.
    # Sets the rotation and refresh time for the display.
    # Initializes the last display time and selected image to None.
    def __init__(self, image_folder, refresh_time, request_file=None):
        self.last_display_time = time.time()
        self.last_selected_image = None
        self.image_folder = image_folder
        self.rotation = 180
        self.refresh_time = refresh_time
        self.request_file = request_file
        self.epd = epd7in3e.EPD()
        self.epd.init()
        self.stop_display = False

    # Fetches the image files from the specified folder.
    def fetch_image_files(self):
        files = [f for f in os.listdir(self.image_folder) if not f.startswith('.')]
        print(f"Found {len(files)} images in {self.image_folder}")
        return files


    # Selects a random image from the list of images.
    def select_random_image(self, images):
        # If one image or less
        if len(images) <= 1:
            return images[0]
        
        # Select a random image unless it was previously selected
        random_image = random.choice([img for img in images if img != self.last_selected_image])
        
        return random_image


    # Continuously loop to display a random image from the specified folder at the specified refresh time.
    def display_images(self):
        self.stop_display = False

        images = self.fetch_image_files()

        if not images:
            print("No images found, displaying default image.")
            self.display_message('no_valid_images.jpg')
            return

        random_image = self.select_random_image(images)
        self.last_selected_image = random_image
            
        # Open and display the image
        with Image.open(os.path.join(self.image_folder, random_image)) as pic:
            # Driver auto-handles rotation for 480x800 input, but if it is upside down
            # we need to rotate it 180 degrees first.
            pic = pic.rotate(self.rotation, expand=False)
            self.epd.display(self.epd.getbuffer(pic))
            self.last_display_time = time.time()

        while not self.stop_display:
            # Check for display request
            if self.request_file and os.path.exists(self.request_file):
                try:
                    with open(self.request_file, 'r') as f:
                        requested_image = f.read().strip()
                    
                    try:
                        os.remove(self.request_file)
                    except OSError:
                        pass
                    
                    # Refresh images list in case it's new
                    images = self.fetch_image_files()
                    
                    if requested_image in images:
                        print(f"Displaying requested image: {requested_image}")
                        self.last_selected_image = requested_image
                        
                        with Image.open(os.path.join(self.image_folder, requested_image)) as pic:
                            pic = pic.rotate(self.rotation, expand=False)
                            self.epd.display(self.epd.getbuffer(pic))
                            self.last_display_time = time.time()
                except Exception as e:
                    print(f"Error processing display request: {e}")

            current_time = time.time()
            elapsed_time = current_time - self.last_display_time
            
            if elapsed_time >= self.refresh_time:
                images = self.fetch_image_files()
                random_image = self.select_random_image(images)
                self.last_selected_image = random_image

                # Open and display the image
                with Image.open(os.path.join(self.image_folder, random_image)) as pic:
                    print(f"Displaying new image: {random_image}")
                    pic = pic.rotate(self.rotation, expand=False)
                    self.epd.display(self.epd.getbuffer(pic))
                    self.last_display_time = time.time()
            
            time.sleep(1) # Sleep to reduce CPU usage
    

    def display_message(self, message_file):
        with Image.open(os.path.join(SCRIPT_DIR, f"messages/{message_file}")) as img_start:
                # Assuming messages are pre-formatted or small enough, 
                # but if they need rotation, we might need to handle them differently.
                # For now, let's trust the driver handles it if dimensions match.
                self.epd.display(self.epd.getbuffer(img_start))

