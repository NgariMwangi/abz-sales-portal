from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, white
import os
from datetime import datetime

def create_receipt_pdf(invoice_data, user_data, output_path):
    """
    Create a professional thermal receipt (80mm width)
    output_path can be a file path (string) or BytesIO object
    """
    # Create custom page size for 80mm thermal receipt
    from reportlab.lib.units import mm
    
    # 80mm = 226.77 points
    receipt_width = 80 * 2.83465
    
    # Use a very tall height to ensure all content fits on one page
    # ReportLab will automatically adjust the final page height
    receipt_height = 1200  # About 423mm - more than enough for any receipt
    
    # Create custom page size
    custom_pagesize = (receipt_width, receipt_height)
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=custom_pagesize,
        rightMargin=3*mm,
        leftMargin=3*mm,
        topMargin=8*mm,
        bottomMargin=8*mm
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Professional thermal receipt styles (optimized for 80mm) - ALL BOLD
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=12,
        textColor=black,
        alignment=TA_CENTER,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    
    tagline_style = ParagraphStyle(
        'Tagline',
        parent=styles['Normal'],
        fontSize=7,
        textColor=black,
        alignment=TA_CENTER,
        spaceAfter=5,
        fontName='Helvetica-Bold'
    )
    
    contact_style = ParagraphStyle(
        'Contact',
        parent=styles['Normal'],
        fontSize=6,
        textColor=black,
        alignment=TA_CENTER,
        spaceAfter=2,
        fontName='Helvetica-Bold'
    )
    
    divider_style = ParagraphStyle(
        'Divider',
        parent=styles['Normal'],
        fontSize=6,
        textColor=black,
        alignment=TA_CENTER,
        spaceAfter=6,
        spaceBefore=6,
        fontName='Helvetica-Bold'
    )
    
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=6,
        textColor=black,
        alignment=TA_LEFT,
        spaceAfter=1,
        fontName='Helvetica-Bold'
    )
    
    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontSize=6,
        textColor=black,
        alignment=TA_LEFT,
        spaceAfter=1,
        fontName='Helvetica-Bold'
    )
    
    total_style = ParagraphStyle(
        'Total',
        parent=styles['Normal'],
        fontSize=9,
        textColor=black,
        alignment=TA_CENTER,
        spaceAfter=5,
        fontName='Helvetica-Bold'
    )
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=6,
        textColor=black,
        alignment=TA_CENTER,
        spaceAfter=2,
        fontName='Helvetica-Bold'
    )
    
    # Build the story (content)
    story = []
    
    # Company header with logo
    from reportlab.platypus import Image
    from reportlab.lib.units import mm
    
    # Add company logo
    try:
        logo_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'logo.png')
        if os.path.exists(logo_path):
            # Logo size: 18mm x 18mm (scaled proportionally)
            logo = Image(logo_path, width=18*mm, height=18*mm)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 4))
    except Exception as e:
        print(f"Warning: Could not load logo: {e}")
    
    # Company name and tagline
    story.append(Paragraph("ABZ HARDWARE", header_style))
    story.append(Paragraph("Quality Tools & Building Materials", tagline_style))
    
    # Contact information
    story.append(Paragraph("Phone: 0725000055 or 0711732341", contact_style))
    story.append(Paragraph("Email: info@abzhardware.co.ke", contact_style))
    story.append(Paragraph("Website: www.abzhardware.co.ke", contact_style))
    
    story.append(Spacer(1, 8))
    
    # Divider line
    story.append(Paragraph("─" * 30, divider_style))
    
    # Items table - clean and simple
    if invoice_data.get('order_items'):
        # Simple table without borders for thermal printing
        table_data = []
        
        # Add table headers
        table_data.append([
            Paragraph("ITEM", label_style),
            Paragraph("QTY", label_style),
            Paragraph("PRICE", label_style),
            Paragraph("TOTAL", label_style)
        ])
        
        # Add items
        for item in invoice_data['order_items']:
            product_name = item.get('product_name', 'N/A')
            quantity = item.get('quantity', 0)
            unit_price = item.get('unit_price', 0)
            total = item.get('total', 0)
            
            # Create product name paragraph that can wrap to multiple lines
            # Use smaller font size for product names to fit more text
            product_style = ParagraphStyle(
                'ProductName',
                parent=value_style,
                fontSize=5,  # Smaller font size for product names
                spaceAfter=1,
                spaceBefore=1,
                leading=6  # Line spacing for multi-line text
            )
            
            table_data.append([
                Paragraph(product_name, product_style),
                Paragraph(str(quantity), value_style),
                Paragraph(f"{int(unit_price)}", value_style),
                Paragraph(f"{int(total)}", value_style)
            ])
        
        # Create table with optimized widths for 80mm
        # Available width: 80mm - 6mm margins = 74mm = 209.8 points
        # Give more space to product name column for multi-line text
        table = Table(table_data, colWidths=[100, 30, 45, 45])  # Total: 220 points
        
        # Clean table style for thermal printing
        table_style = TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),  # All text bold
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('TEXTCOLOR', (0, 0), (-1, -1), black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),    # Product name left
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),  # Quantity center
            ('ALIGN', (2, 0), (3, -1), 'RIGHT'),   # Prices right
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
        ])
        
        table.setStyle(table_style)
        story.append(table)
    
    story.append(Spacer(1, 8))
    
    # Divider line
    story.append(Paragraph("─" * 30, divider_style))
    
    # Total amount - prominent display
    story.append(Paragraph(f"TOTAL: {int(invoice_data.get('subtotal', 0))}", total_style))
    
    story.append(Spacer(1, 8))
    
    # Divider line
    story.append(Paragraph("─" * 30, divider_style))
    
    # Receipt details below total
    story.append(Paragraph(f"Order: #{invoice_data.get('order_id', 'N/A')}", label_style))
    story.append(Paragraph(f"Date: {invoice_data.get('order_date', 'N/A')} at {invoice_data.get('order_time', 'N/A')}", label_style))
    story.append(Paragraph(f"Branch: {invoice_data.get('branch', 'N/A')}", label_style))
    story.append(Paragraph(f"Served by: {user_data.get('firstname', 'N/A')}", label_style))
    
    story.append(Spacer(1, 10))
    
    # Footer
    story.append(Paragraph("Thank you for choosing ABZ Hardware!", footer_style))
    story.append(Paragraph("For queries, contact us on 0725000055 or 0711732341", footer_style))
    story.append(Paragraph("or visit our branch", footer_style))
    
    # Build the PDF
    doc.build(story)
    
    return output_path

def generate_receipt_filename(invoice_number):
    """Generate a filename for the receipt"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"receipt_{invoice_number}_{timestamp}.pdf"

def generate_invoice_pdf(invoice_id):
    """
    Generate PDF invoice data for email attachments
    Returns BytesIO object for email attachment
    """
    from io import BytesIO
    from app.models import Invoice, Order, OrderItem, Product, User, Branch
    
    # Get invoice and related data
    invoice = Invoice.query.get_or_404(invoice_id)
    order = Order.query.get_or_404(invoice.orderid)
    
    # Prepare invoice data
    invoice_data = {
        'invoice_number': invoice.invoice_number,
        'order_id': order.id,
        'customer_name': f"{order.user.firstname} {order.user.lastname}",
        'customer_email': order.user.email,
        'customer_phone': getattr(order.user, 'phone', 'N/A'),
        'branch': order.branch.name,
        'order_date': order.created_at.strftime('%B %d, %Y'),
        'order_time': order.created_at.strftime('%I:%M %p'),
        'order_items': [],
        'subtotal': 0
    }
    
    # Calculate totals and prepare items
    for item in order.order_items:
        if item.final_price is not None:
            final_price = float(item.final_price)
        elif item.product.sellingprice is not None:
            final_price = float(item.product.sellingprice)
        else:
            final_price = 0.0
        
        item_total = item.quantity * final_price
        invoice_data['subtotal'] += item_total
        
        invoice_data['order_items'].append({
            'product_name': item.product.name,
            'quantity': item.quantity,
            'unit_price': final_price,
            'total': item_total
        })
    
    # Prepare user data
    user_data = {
        'firstname': order.user.firstname,
        'lastname': order.user.lastname,
        'email': order.user.email
    }
    
    # Create BytesIO object for email attachment
    pdf_buffer = BytesIO()
    
    # Generate PDF to BytesIO
    create_receipt_pdf(invoice_data, user_data, pdf_buffer)
    
    # Reset buffer position
    pdf_buffer.seek(0)
    
    return pdf_buffer

def create_quotation_pdf(quotation, user_data, output_path):
    """
    Create a professional quotation PDF (80mm width)
    output_path can be a file path (string) or BytesIO object
    """
    # Create custom page size for 80mm thermal receipt
    from reportlab.lib.units import mm
    
    # 80mm = 226.77 points
    receipt_width = 80 * 2.83465
    
    # Use a very tall height to ensure all content fits on one page
    # ReportLab will automatically adjust the final page height
    receipt_height = 1200  # About 423mm - more than enough for any quotation
    
    # Create custom page size
    custom_pagesize = (receipt_width, receipt_height)
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=custom_pagesize,
        rightMargin=3*mm,
        leftMargin=3*mm,
        topMargin=8*mm,
        bottomMargin=8*mm
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Professional quotation styles (optimized for 80mm) - ALL BOLD
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=12,
        textColor=black,
        alignment=TA_CENTER,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    
    tagline_style = ParagraphStyle(
        'Tagline',
        parent=styles['Normal'],
        fontSize=7,
        textColor=black,
        alignment=TA_CENTER,
        spaceAfter=5,
        fontName='Helvetica-Bold'
    )
    
    contact_style = ParagraphStyle(
        'Contact',
        parent=styles['Normal'],
        fontSize=6,
        textColor=black,
        alignment=TA_CENTER,
        spaceAfter=2,
        fontName='Helvetica-Bold'
    )
    
    divider_style = ParagraphStyle(
        'Divider',
        parent=styles['Normal'],
        fontSize=6,
        textColor=black,
        alignment=TA_CENTER,
        spaceAfter=6,
        spaceBefore=6,
        fontName='Helvetica-Bold'
    )
    
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=6,
        textColor=black,
        alignment=TA_LEFT,
        spaceAfter=1,
        fontName='Helvetica-Bold'
    )
    
    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontSize=6,
        textColor=black,
        alignment=TA_LEFT,
        spaceAfter=1,
        fontName='Helvetica-Bold'
    )
    
    total_style = ParagraphStyle(
        'Total',
        parent=styles['Normal'],
        fontSize=9,
        textColor=black,
        alignment=TA_CENTER,
        spaceAfter=5,
        fontName='Helvetica-Bold'
    )
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=6,
        textColor=black,
        alignment=TA_CENTER,
        spaceAfter=2,
        fontName='Helvetica-Bold'
    )
    
    # Build the story (content)
    story = []
    
    # Company header with logo
    from reportlab.platypus import Image
    from reportlab.lib.units import mm
    
    # Add company logo
    try:
        logo_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'logo.png')
        if os.path.exists(logo_path):
            # Logo size: 18mm x 18mm (scaled proportionally)
            logo = Image(logo_path, width=18*mm, height=18*mm)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 4))
    except Exception as e:
        print(f"Warning: Could not load logo: {e}")
    
    # Company name and tagline
    story.append(Paragraph("ABZ HARDWARE", header_style))
    story.append(Paragraph("Quality Tools & Building Materials", tagline_style))
    
    # Contact information
    story.append(Paragraph("Phone: 0725000055 or 0711732341", contact_style))
    story.append(Paragraph("Email: info@abzhardware.co.ke", contact_style))
    story.append(Paragraph("Website: www.abzhardware.co.ke", contact_style))
    
    story.append(Spacer(1, 8))
    
    # Items table - clean and simple
    if quotation.items:
        # Simple table without borders for thermal printing
        table_data = []
        
        # Add table headers
        table_data.append([
            Paragraph("ITEM", label_style),
            Paragraph("QTY", label_style),
            Paragraph("PRICE", label_style),
            Paragraph("TOTAL", label_style)
        ])
        
        # Add items
        for item in quotation.items:
            product_name = item.product.name if item.product else 'N/A'
            quantity = item.quantity
            unit_price = item.unit_price
            total = item.unit_price * item.quantity
            
            # Create product name paragraph that can wrap to multiple lines
            # Use smaller font size for product names to fit more text
            product_style = ParagraphStyle(
                'ProductName',
                parent=value_style,
                fontSize=5,  # Smaller font size for product names
                spaceAfter=1,
                spaceBefore=1,
                leading=6  # Line spacing for multi-line text
            )
            
            table_data.append([
                Paragraph(product_name, product_style),
                Paragraph(str(quantity), value_style),
                Paragraph(f"{int(unit_price)}", value_style),
                Paragraph(f"{int(total)}", value_style)
            ])
        
        # Create table with optimized widths for 80mm
        # Available width: 80mm - 6mm margins = 74mm = 209.8 points
        # Give more space to product name column for multi-line text
        table = Table(table_data, colWidths=[100, 30, 45, 45])  # Total: 220 points
        
        # Clean table style for thermal printing
        table_style = TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),  # All text bold
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('TEXTCOLOR', (0, 0), (-1, -1), black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),    # Product name left
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),  # Quantity center
            ('ALIGN', (2, 0), (3, -1), 'RIGHT'),   # Prices right
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
        ])
        
        table.setStyle(table_style)
        story.append(table)
    
    story.append(Spacer(1, 8))
    
    # Divider line
    story.append(Paragraph("─" * 30, divider_style))
    
    # Total amount - prominent display (centered)
    total_centered_style = ParagraphStyle(
        'TotalCentered',
        parent=value_style,
        alignment=TA_CENTER,  # Center the total horizontally
        fontSize=9,  # Keep the larger font size for prominence
        spaceAfter=5,
        spaceBefore=5
    )
    story.append(Paragraph(f"TOTAL: KSh {int(quotation.total_amount)}", total_centered_style))
    
    story.append(Spacer(1, 8))
    
    # Divider line
    story.append(Paragraph("─" * 30, divider_style))
    
    # Quotation details - moved below the total price
    story.append(Paragraph(f"Quotation: {quotation.quotation_number}", label_style))
    story.append(Paragraph(f"Date: {quotation.created_at.strftime('%B %d, %Y')}", label_style))
    story.append(Paragraph(f"Branch: {quotation.branch.name}", label_style))
    
    story.append(Spacer(1, 6))
    
    # Footer
    story.append(Paragraph("Thank you for your interest in ABZ Hardware!", footer_style))
    story.append(Paragraph("For queries, contact us on 0725000055 or 0711732341", footer_style))
    story.append(Paragraph("or visit our branch", footer_style))
    
    # Build the PDF
    doc.build(story)
    
    return output_path 