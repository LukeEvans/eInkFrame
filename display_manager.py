import os
import sys
import time
import random
import json
import logging
from datetime import datetime, timedelta
from PIL import Image
from lib.waveshare_epd import epd7in3f

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_PATH = os.path.join(SCRIPT_DIR, 'lib')
sys.path.append(LIB_PATH)

class DisplayManager:
    """
    Class to manage the display of images on the e-Paper screen.
    """

    # Initializes the display using the epd7in3f library.
    # Sets the rotation for the display.
    # Initializes image history tracking.
    def __init__(self, image_folder, request_file=None, image_converter=None):
        self.image_folder = image_folder
        self.image_converter = image_converter
        self.rotation = 180
        self.request_file = request_file
        self.history_file = os.path.join(image_folder, '.display_history.json')
        self.image_history = self.load_history()
        self.last_daily_refresh = self.get_last_daily_refresh_time()
        self.epd = epd7in3f.EPD()
        self.epd.init()
        self.stop_display = False

    def load_history(self):
        """Load image display history from file."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_history(self):
        """Save image display history to file."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.image_history, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

    def get_last_daily_refresh_time(self):
        """Get the last time we did a daily refresh."""
        # Check if we have any history, if so use the most recent display time
        if self.image_history:
            latest_time = max(self.image_history.values())
            return datetime.fromtimestamp(latest_time)
        return datetime.now() - timedelta(days=1)  # Default to yesterday if no history

    def should_refresh_daily(self):
        """Check if it's time for daily refresh (2 AM)."""
        now = datetime.now()
        # Refresh at 2 AM
        refresh_time = now.replace(hour=2, minute=0, second=0, microsecond=0)

        # If it's past 2 AM today and we haven't refreshed today
        if now >= refresh_time and self.last_daily_refresh < refresh_time:
            return True
        return False


    # Fetches the image files from the specified folder.
    def fetch_image_files(self):
        files = [f for f in os.listdir(self.image_folder) if not f.startswith('.')]
        print(f"Found {len(files)} images in {self.image_folder}")
        return files


    # Selects an image preferring ones not shown recently.
    def select_random_image(self, images):
        # If one image or less
        if len(images) <= 1:
            return images[0]

        current_time = time.time()

        # Calculate weights based on how long ago each image was shown
        # Images never shown get highest weight, recently shown get lower weight
        weights = []
        for img in images:
            last_shown = self.image_history.get(img, 0)
            if last_shown == 0:
                # Never shown - highest priority
                weight = 100
            else:
                # Weight decreases with how recently it was shown
                days_since_shown = (current_time - last_shown) / (24 * 3600)
                # Weight from 1 (shown today) to 50 (shown long ago)
                weight = min(50, max(1, days_since_shown * 2))
            weights.append(weight)

        # Use weighted random selection
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(images)

        pick = random.uniform(0, total_weight)
        current_weight = 0
        for i, img in enumerate(images):
            current_weight += weights[i]
            if pick <= current_weight:
                # Update history when we select an image
                self.image_history[img] = current_time
                self.save_history()
                return img

        # Fallback
        return random.choice(images)


    # Continuously loop to display a random image from the specified folder at the specified refresh time.
    def display_images(self):
        self.stop_display = False

        images = self.fetch_image_files()

        if not images:
            print("No images found, displaying default image.")
            self.display_message('no_valid_images.jpg')
            return

        random_image = self.select_random_image(images)

        # Open and display the image
        with Image.open(os.path.join(self.image_folder, random_image)) as pic:
            # Driver auto-handles rotation for 480x800 input, but if it is upside down
            # we need to rotate it 180 degrees first.
            pic = pic.rotate(self.rotation, expand=False)
            self.epd.display(self.get_enhanced_buffer(pic, dither_mode='none'))

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

                    # If requested image not in processed images, try to process it
                    if requested_image not in images:
                        print(f"Requested image {requested_image} not found in display folder, processing...")
                        if self.image_converter and self.image_converter.process_single_image(requested_image):
                            images = self.fetch_image_files()  # Refresh list after processing
                        else:
                            print(f"Failed to process image: {requested_image}")
                            continue

                    if requested_image in images:
                        print(f"Displaying requested image: {requested_image}")
                        # Update history for requested image
                        self.image_history[requested_image] = time.time()
                        self.save_history()

                        with Image.open(os.path.join(self.image_folder, requested_image)) as pic:
                            pic = pic.rotate(self.rotation, expand=False)
                            self.epd.display(self.get_enhanced_buffer(pic, dither_mode='none'))
                except Exception as e:
                    print(f"Error processing display request: {e}")

            # Check if it's time for daily refresh (2 AM)
            if self.should_refresh_daily():
                images = self.fetch_image_files()
                if images:
                    random_image = self.select_random_image(images)

                    # Open and display the image
                    with Image.open(os.path.join(self.image_folder, random_image)) as pic:
                        print(f"Daily refresh: Displaying new image: {random_image}")
                        pic = pic.rotate(self.rotation, expand=False)
                        self.epd.display(self.get_enhanced_buffer(pic, dither_mode='none'))

                    # Update last daily refresh time
                    self.last_daily_refresh = datetime.now()

            time.sleep(60) # Sleep for 1 minute to reduce CPU usage
    

    def get_enhanced_buffer(self, image, dither_mode='none'):
        """
        Enhanced getbuffer method with different dithering options for better image quality.
        """
        # Create a palette with the 7 colors supported by the panel (matching epd7in3f)
        pal_image = Image.new("P", (1,1))
        pal_image.putpalette((0,0,0, 255,255,255, 0,255,0, 0,0,255, 255,0,0, 255,255,0, 255,128,0) + (0,0,0)*249)

        # Check if we need to rotate the image
        imwidth, imheight = image.size
        if(imwidth == self.epd.width and imheight == self.epd.height):
            image_temp = image
        elif(imwidth == self.epd.height and imheight == self.epd.width):
            image_temp = image.rotate(90, expand=True)
        else:
            logger.warning("Invalid image dimensions: %d x %d, expected %d x %d" %
                          (imwidth, imheight, self.epd.width, self.epd.height))
            image_temp = image

        # Convert the source image to the 7 colors with different dithering options
        if dither_mode == 'floyd':
            # Floyd-Steinberg dithering (more detailed but can look noisy)
            image_7color = image_temp.convert('RGB').quantize(palette=pal_image, dither=Image.Dither.FLOYDSTEINBERG)
        elif dither_mode == 'ordered':
            # Ordered dithering (more structured pattern)
            image_7color = image_temp.convert('RGB').quantize(palette=pal_image, dither=Image.Dither.ORDERED)
        else:
            # No dithering (cleaner but may have banding)
            image_7color = image_temp.convert('RGB').quantize(palette=pal_image, dither=Image.Dither.NONE)

        buf_7color = bytearray(image_7color.tobytes('raw'))

        # PIL does not support 4 bit color, so pack the 4 bits of color
        # into a single byte to transfer to the panel
        buf = [0x00] * int(self.epd.width * self.epd.height / 2)
        idx = 0
        for i in range(0, len(buf_7color), 2):
            buf[idx] = (buf_7color[i] << 4) + buf_7color[i+1]
            idx += 1

        return buf

    def display_message(self, message_file):
        with Image.open(os.path.join(SCRIPT_DIR, f"messages/{message_file}")) as img_start:
                # Assuming messages are pre-formatted or small enough,
                # but if they need rotation, we might need to handle them differently.
                # For now, let's trust the driver handles it if dimensions match.
                self.epd.display(self.get_enhanced_buffer(img_start, dither_mode='none'))

