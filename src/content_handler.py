import fitz  # PyMuPDF
import base64
import logging
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, elevenSeventeen
from reportlab.platypus import SimpleDocTemplate, TableStyle, Paragraph, Spacer, LongTable
from reportlab.lib.styles import getSampleStyleSheet
from pdf2image import convert_from_bytes
from PIL import Image

logger = logging.getLogger(__name__)

class ContentHandler:
    """
    A utility class for handling content transformations, such as PDF to image conversion,
    string parsing, and file saving.
    """

    @staticmethod
    def get_image_from_pdf_content(pdf_content):
        """Converts all pages of the PDF bytes to a single PIL Image, stitched vertically."""
        try:
            # pdf2image.convert_from_bytes returns a list of PIL Images
            images = convert_from_bytes(pdf_content, dpi=200)
            
            if not images:
                logger.warning("Error: No images generated from PDF")
                return None
            
            logger.info(f"PDF converted to {len(images)} images. Stitching...")
            
            # Calculate total dimensions
            widths, heights = zip(*(i.size for i in images))
            max_width = max(widths)
            total_height = sum(heights)
            
            # Create a new white background image
            stitched_image = Image.new('RGB', (max_width, total_height), (255, 255, 255))
            
            current_y = 0
            for i, img in enumerate(images):
                logger.info(f"Pasting page {i} at y={current_y} (size: {img.size})")
                # Ensure image is in RGB mode for consistent pasting
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                stitched_image.paste(img, (0, current_y))
                current_y += img.size[1]
            
            return stitched_image
            
        except Exception as e:
            logger.error(f"Error converting PDF to image: {e}")
            return None

    @staticmethod
    def pix_to_base64(image):
        """Converts a PIL Image to a base64 encoded string."""
        if image:
            try:
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                img_bytes = buffer.getvalue()
                base64_string = base64.b64encode(img_bytes).decode('utf-8')
                return base64_string
            except Exception as e:
                logger.error(f"Error converting image to base64: {e}")
                return None
        return None

    @staticmethod
    def convert_pdf_to_image(pdf_content):
        """Converts PDF bytes to a stitched PIL Image."""
        return ContentHandler.get_image_from_pdf_content(pdf_content)

    @staticmethod
    def dataframe_to_pdf_content(df):
        """
        Generates a PDF from a DataFrame and returns the content as bytes.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=landscape(elevenSeventeen),
            topMargin=30,
            bottomMargin=30,
            leftMargin=30,
            rightMargin=30
        )
        elements = []
        
        # Add Header with current date and time
        styles_sheet = getSampleStyleSheet()
        header_style = styles_sheet['Heading1']
        header_style.alignment = 1  # 1=Center
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = Paragraph(f"Stock Notification Scan Report - {now}", header_style)
        elements.append(header)
        elements.append(Spacer(1, 20))

        # Convert DataFrame to a list of lists (including headers)
        table_data = [df.columns.to_list()] + df.values.tolist()

        # Create Table object using LongTable for better multi-page support
        # repeatRows=1 ensures header is on every page
        table = LongTable(table_data, repeatRows=1)

        # Add style to table
        styles = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#BDC3C7")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        
        # Zebra Effect - apply to the whole range
        # Note: ReportLab handles split background styles correctly for Table/LongTable
        for i in range(1, len(table_data)):
            bg_color = colors.HexColor("#F9F9F9") if i % 2 == 0 else colors.HexColor("#FFFFFF")
            styles.append(('BACKGROUND', (0, i), (-1, i), bg_color))

        table.setStyle(TableStyle(styles))

        # Build the PDF
        elements.append(table)
        doc.build(elements)
        
        pdf_content = buffer.getvalue()
        buffer.close()
        return pdf_content