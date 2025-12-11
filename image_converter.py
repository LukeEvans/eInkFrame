import os
from PIL import Image, ImageEnhance, ImageOps


class ImageConverter:
    """
    Class to convert images for display on the e-Paper screen.
    """

    def __init__(self, source_dir, output_dir):
        self.source_dir = source_dir
        self.output_dir = output_dir

    # Finds valid image files in the source directory to process.
    def process_images(self):
        valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff')

        for img in os.listdir(self.source_dir):

            if img.startswith('.'):
                continue
            
            print(f"Found file: {img}")
            img_path = os.path.join(self.source_dir, img)

            if os.path.isfile(img_path) and img.lower().endswith(valid_extensions):
                print(f"Resizing image: {img_path}")
                self.resize_image(img_path, img)
            

    # Resizes the image to fit the target dimensions while maintaining aspect ratio.
    # Crops the image to the target dimensions and enhances color and contrast.
    # Saves the processed image to the output directory.
    def resize_image(self, img_path, file_name):
        # Screen target size dims (Portrait)
        target_width = 480
        target_height = 800

        with Image.open(img_path) as img:
            img = ImageOps.exif_transpose(img)

            # Original dimensions
            orig_width, orig_height = img.size

            original_aspect_ratio = orig_width / orig_height
            target_aspect_ratio = target_width / target_height

            # Fit height and crop sides
            if original_aspect_ratio > target_aspect_ratio:
                new_height = target_height
                new_width = int(new_height * original_aspect_ratio)
            # Fit width and crop top/bottom
            else:
                new_width = target_width
                new_height = int(new_width / original_aspect_ratio)

            print("Resizing image...")
            # Resize the image while maintaining aspect ratio
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Calculate the cropping box to center the crop
            left = (new_width - target_width) // 2
            top = (new_height - target_height) // 2
            right = left + target_width
            bottom = top + target_height

            print("Cropping image...")
            # Crop the image
            cropped_img = resized_img.crop((left, top, right, bottom))

            print("Enchancing image...")
            color = ImageEnhance.Color(cropped_img)
            cropped_img = color.enhance(1.5)

            contrast = ImageEnhance.Contrast(cropped_img)
            cropped_img = contrast.enhance(1.5)
            
            print("Saving image...")
            # Save the final image
            cropped_img.save(os.path.join(self.output_dir, file_name))

