import fitz  # PyMuPDF
import base64
import logging
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, elevenSeventeen
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

logger = logging.getLogger(__name__)

class ContentHandler:
    """
    A utility class for handling content transformations, such as PDF to image conversion,
    string parsing, and file saving.
    """

    @staticmethod
    def get_image_from_pdf_content(pdf_content):
        """Converts the first page of the PDF bytes to a pixmap, cropped to visible content."""
        try:
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            if len(doc) > 0:
                page = doc.load_page(0)
                content_rect = page.get_bboxlog()
                if content_rect:
                    full_bbox = fitz.Rect()
                    for item in content_rect:
                        full_bbox.include_rect(item[1])
                    padding = 0.5
                    full_bbox = full_bbox + (-padding, -padding, padding, padding)
                    page.set_cropbox(full_bbox)
                pix = page.get_pixmap(dpi=300)
                doc.close()
                return pix
            else:
                logger.debug("Error: Empty PDF")
                doc.close()
                return None
        except Exception as e:
            logger.debug(f"Error converting PDF to image: {e}")
            return None

    @staticmethod
    def pix_to_base64(pixmap):
        """Converts a fitz.Pixmap to a base64 encoded string."""
        if pixmap:
            img_bytes = pixmap.tobytes("png")
            base64_string = base64.b64encode(img_bytes).decode('utf-8')
            return base64_string
        return None

    @staticmethod
    def convert_pdf_to_image(pdf_content, output_image_path=None):
        """Converts PDF bytes to an image pixmap."""
        pix = ContentHandler.get_image_from_pdf_content(pdf_content)
        if pix:
            if output_image_path:
                ContentHandler.save_image_to_file(pix, output_image_path)
            return pix
        return None

    @staticmethod
    def dataframe_to_pdf_content(df):
        """
        Generates a PDF from a DataFrame and returns the content as bytes.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(elevenSeventeen))
        elements = []
        
        # Add Header with current date and time
        styles_sheet = getSampleStyleSheet()
        header_style = styles_sheet['Heading1']
        header_style.alignment = 1  # 0=Left, 1=Center, 2=Right
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = Paragraph(f"Stock Notification Scan Report - {now}", header_style)
        elements.append(header)
        elements.append(Spacer(1, 20))

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
        
        pdf_content = buffer.getvalue()
        buffer.close()
        return pdf_content