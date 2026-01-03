"""Generate placeholder icon files for the extension"""
from PIL import Image, ImageDraw, ImageFont

def create_icon(size, filename):
    # Create a blue square with white text
    img = Image.new('RGB', (size, size), color='#3b82f6')
    draw = ImageDraw.Draw(img)

    # Add "PP" text (Privacy Policy)
    try:
        font_size = size // 2
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    text = "PP"
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Center the text
    x = (size - text_width) // 2
    y = (size - text_height) // 2

    draw.text((x, y), text, fill='white', font=font)

    img.save(filename)
    print(f"Created {filename}")

# Create icons in different sizes
sizes = [16, 32, 48, 128]
for size in sizes:
    create_icon(size, f'extension/public/icons/icon{size}.png')

print("All icons created successfully!")
