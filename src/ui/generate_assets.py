#!/usr/bin/env python3
import os
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtCore import QByteArray, Qt

def svg_to_png(svg_path, png_path, width=120, height=120):
    """Convert SVG file to PNG."""
    # Read SVG content
    with open(svg_path, 'r') as f:
        svg_content = f.read().encode('utf-8')
    
    # Create QImage to render to
    image = QImage(width, height, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    
    # Create renderer and painter
    renderer = QSvgRenderer(QByteArray(svg_content))
    painter = QPainter(image)
    
    # Render SVG to image
    renderer.render(painter)
    painter.end()
    
    # Save as PNG
    image.save(png_path)
    print(f"Converted {svg_path} to {png_path}")

def main():
    """Convert all SVG assets to PNG."""
    # Initialize QApplication (required for QPainter)
    app = QApplication(sys.argv)
    
    # Get asset directories
    script_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(script_dir, "assets")
    
    # Convert non-thinking SVG files to PNG
    for file in os.listdir(assets_dir):
        if file.endswith(".svg") and file != "thinking.svg":
            svg_path = os.path.join(assets_dir, file)
            png_path = os.path.join(assets_dir, file.replace(".svg", ".png"))
            svg_to_png(svg_path, png_path)
    
    print("Asset generation complete!")

if __name__ == "__main__":
    main()
