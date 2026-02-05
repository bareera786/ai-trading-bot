# PWA Icon Generation Script
# This creates placeholder icons for the PWA
# Replace with actual logo later

from PIL import Image, ImageDraw, ImageFont
import os

# Create icons directory
icons_dir = "app/static/icons"
os.makedirs(icons_dir, exist_ok=True)

# Icon sizes needed for PWA
sizes = [72, 96, 128, 144, 152, 192, 384, 512]

# Colors matching the theme
bg_color = (15, 20, 25)  # Dark background
primary_color = (0, 212, 170)  # Cyan/teal primary

for size in sizes:
    # Create image with dark background
    img = Image.new('RGB', (size, size), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Draw a simple rocket emoji or gradient circle
    # For now, draw a circle with gradient effect
    center = size // 2
    radius = int(size * 0.35)
    
    # Draw outer glow
    for i in range(10):
        alpha = 255 - (i * 20)
        r = radius + (i * 2)
        draw.ellipse(
            [center - r, center - r, center + r, center + r],
            fill=primary_color,
            outline=None
        )
    
    # Draw main circle
    draw.ellipse(
        [center - radius, center - radius, center + radius, center + radius],
        fill=primary_color,
        outline=None
    )
    
    # Try to add text "AI" in the center
    try:
        font_size = int(size * 0.3)
        # Use default font
        draw.text(
            (center, center),
            "🚀",
            fill=(255, 255, 255),
            anchor="mm",
            font_size=font_size
        )
    except:
        # If font fails, just use the circle
        pass
    
    # Save icon
    img.save(f"{icons_dir}/icon-{size}.png", "PNG")
    print(f"✅ Created icon-{size}.png")

print("\n✅ All PWA icons created successfully!")
print("📝 Note: Replace these placeholder icons with your actual logo later")
