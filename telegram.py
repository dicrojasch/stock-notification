import os
from datetime import datetime

import pandas as pd
import requests
from pdf2image import convert_from_path
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

TOKEN = "" # Remember to change it for security!
CHAT_ID = ""

def send_pdf_as_image(pdf_path):
    # 1. Convert PDF to list of images (one per page)
    # If on Windows, add: poppler_path=r'C:\Path\To\poppler\bin'
    pages = convert_from_path(pdf_path, dpi=200)

    for i, page in enumerate(pages):
        img_name = f"page_{i}.jpg"
        page.save(img_name, "JPEG")

        # 2. Send the image to Telegram
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        with open(img_name, 'rb') as photo:
            payload = {'chat_id': CHAT_ID}
            files = {'photo': photo}
            response = requests.post(url, data=payload, files=files)
        
        # 3. Clean up temporary file
        os.remove(img_name)
        
    return response.json()

def create_pdf(text, file_name):
    letter_size = landscape(letter)
    
    c = canvas.Canvas(file_name, pagesize=letter_size)
    width, height = letter_size # Width: 612 pts, Height: 792 pts
    
    # Start text leaving a 50-point margin
    textobject = c.beginText(50, height - 50)
    textobject.setFont("Courier", 8)
    
    # Process message line by line
    for line in text.split('\n'):
        textobject.textLine(line)
        
        # If text gets close to the bottom of the page (bottom margin)
        if textobject.getY() < 50:
            c.drawText(textobject)
            c.showPage() # New page
            textobject = c.beginText(50, height - 50)
            textobject.setFont("Courier", 8)
    
    c.drawText(textobject)
    c.save()

def dataframe_to_pdf(df, file_name):
    # Configure document in Landscape
    doc = SimpleDocTemplate(file_name, pagesize=landscape(letter))
    elements = []

    # Convert DataFrame to a list of lists (including headers)
    table_data = [df.columns.to_list()] + df.values.tolist()

    # Create Table object
    table = Table(table_data)

    # Add style to table (borders, colors, fonts)
    styles = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2C3E50")), # Elegant dark blue header
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#BDC3C7")), # Subtle gray grid
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    
    # Rows with interleaved colors (Zebra Effect)
    for i in range(1, len(table_data)):
        bg_color = colors.HexColor("#F9F9F9") if i % 2 == 0 else colors.HexColor("#FFFFFF")
        styles.append(('BACKGROUND', (0, i), (-1, i), bg_color))

    style = TableStyle(styles)
    table.setStyle(style)

    # Build the PDF
    elements.append(table)
    doc.build(elements)

def send_document(file_path):
    url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
    with open(file_path, 'rb') as file:
        payload = {'chat_id': CHAT_ID}
        files = {'document': file}
        response = requests.post(url, data=payload, files=files)
    return response.json()
