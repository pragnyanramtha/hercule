from PIL import Image
import os
import shutil

# Paths
source_image = r"c:\Users\Pragnyan\dev\privacy\image.png"
icons_dir = r"c:\Users\Pragnyan\dev\privacy\frontend\public\icons"

# Ensure directory exists
os.makedirs(icons_dir, exist_ok=True)

# Save as logo.png (for the app header)
logo_dest = os.path.join(icons_dir, "logo.png")
shutil.copy2(source_image, logo_dest)
print(f"Copied to {logo_dest}")

# Sizes for extension icons
sizes = [16, 32, 48, 128]

try:
    with Image.open(source_image) as img:
        # Convert to RGB if necessary (handle transparency if PNG)
        # Actually keep RGBA for icons if source has it
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        for size in sizes:
            # high quality downsampling
            resized_img = img.resize((size, size), Image.Resampling.LANCZOS)
            dest_path = os.path.join(icons_dir, f"icon{size}.png")
            resized_img.save(dest_path)
            print(f"Generated {dest_path}")
            
except ImportError:
    print("PIL (Pillow) not found. Falling back to simple file copy.")
    # Fallback: just copy the large image to all icon names. 
    # Browser usually scales them down, though not optimal.
    for size in sizes:
        dest_path = os.path.join(icons_dir, f"icon{size}.png")
        shutil.copy2(source_image, dest_path)
        print(f"Copied (fallback) {dest_path}")
except Exception as e:
    print(f"Error processing images: {e}")
