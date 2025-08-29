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
        # Use final_price for calculations (includes negotiated prices)
        if item.final_price is not None:
            final_price = float(item.final_price)
        elif item.productid and item.product and item.product.sellingprice is not None:
            final_price = float(item.product.sellingprice)
        else:
            final_price = 0.0
        
        item_total = item.quantity * final_price
        invoice_data['subtotal'] += item_total
        
        # Get product name - use product_name field if available, otherwise fall back to product.name
        if item.product_name:
            product_name = item.product_name
        elif item.productid and item.product:
            product_name = item.product.name
        else:
            product_name = "Manual Item"
        
        invoice_data['order_items'].append({
            'product_name': product_name,
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
            # Get product name - use product_name field if available, otherwise fall back to product.name
            if hasattr(item, 'product_name') and item.product_name:
                product_name = item.product_name
            elif item.product and hasattr(item.product, 'name'):
                product_name = item.product.name
            else:
                product_name = 'N/A'
            
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

def create_quotation_pdf_a4(quotation, user_data, output_path):
    """
    Create a professional quotation PDF (A4 size)
    output_path can be a file path (string) or BytesIO object
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from datetime import datetime
    import pytz
    
    # Set timezone to East Africa Time
    EAT = pytz.timezone('Africa/Nairobi')
    
    # Create PDF buffer
    if isinstance(output_path, str):
        # If output_path is a string, create a file
        doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=18)
    else:
        # If output_path is BytesIO, use it directly
        doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # Center alignment
        textColor=colors.HexColor('#2c3e50')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=20,
        textColor=colors.HexColor('#34495e')
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=12
    )
    
    # Recreate the ABZ Hardware letterhead manually
    
    # Try to load the logo for the left side
    try:
        logo_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'logo.png')
        if os.path.exists(logo_path):
            logo_image = Image(logo_path, width=1.5*inch, height=1*inch)
            logo_cell = logo_image
        else:
            # Fallback to text if logo not found
            logo_cell = Paragraph('''
            <para align=left>
            <b><font size=24 color="#1a365d">🔧ABZ</font></b><br/>
            <b><font size=16 color="#f4b942">HARDWARE</font></b><br/>
            <b><font size=14 color="#1a365d">LIMITED</font></b>
            </para>
            ''', normal_style)
    except Exception as e:
        print(f"Error loading logo: {e}")
        # Fallback to text if logo fails to load
        logo_cell = Paragraph('''
        <para align=left>
        <b><font size=24 color="#1a365d">🔧ABZ</font></b><br/>
        <b><font size=16 color="#f4b942">HARDWARE</font></b><br/>
        <b><font size=14 color="#1a365d">LIMITED</font></b>
        </para>
        ''', normal_style)
    
    # Create the letterhead table for proper layout
    letterhead_data = [[
        # Left side - Logo Image
        logo_cell,
        
        # Right side - Contact Information
        Paragraph('''
        <para align=right>
        <b><font size=11 color="#1a365d">Kombo Munyiri Road,</font></b><br/>
        <b><font size=11 color="#1a365d">Gikomba, Nairobi, Kenya</font></b><br/>
        <font size=9 color="#666666">0711 732 341 or 0725 000 055</font><br/>
        <font size=9 color="#666666">info@abzhardware.co.ke</font><br/>
        <font size=9 color="#666666">www.abzhardware.co.ke</font>
        </para>
        ''', normal_style)
    ]]
    
    # Create letterhead table
    letterhead_table = Table(letterhead_data, colWidths=[3.5*inch, 3.5*inch])
    letterhead_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),
    ]))
    
    elements.append(letterhead_table)
    elements.append(Spacer(1, 10))
    
    # Add the colored line separator (yellow and dark blue)
    separator_data = [[""]]
    separator_table = Table(separator_data, colWidths=[7*inch], rowHeights=[0.05*inch])
    separator_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f4b942')),  # Yellow color
    ]))
    
    elements.append(separator_table)
    elements.append(Spacer(1, 30))
    
    # Quotation Title
    elements.append(Paragraph(f"QUOTATION", title_style))
    elements.append(Spacer(1, 30))
    
    # Quotation Details Section
    customer_info = ""
    if quotation.customer_name and quotation.customer_name.strip() != "*" and quotation.customer_name.strip():
        customer_info = f"<b>Customer:</b> {quotation.customer_name}<br/>"
    
    valid_until_info = ""
    if quotation.valid_until:
        valid_until_info = f"<b>Valid Until:</b> {quotation.valid_until.strftime('%B %d, %Y')}<br/>"
    
    quotation_details = f"""
    <b>Quotation Number:</b> {quotation.quotation_number}<br/>
    <b>Date:</b> {quotation.created_at.strftime('%B %d, %Y') if quotation.created_at else 'N/A'}<br/>
    {customer_info}<b>Branch:</b> {quotation.branch.name if quotation.branch else 'N/A'}<br/>
    {valid_until_info}
    """
    elements.append(Paragraph(quotation_details, normal_style))
    elements.append(Spacer(1, 30))
    
    # Items Table
    if quotation.items:
        elements.append(Paragraph("ITEMS QUOTED", heading_style))
        
        # Table data - Product Name, Quantity, Unit Price, Total Price
        data = [['Product Name', 'Quantity', 'Unit Price', 'Total Price']]
        
        for item in quotation.items:
            # Get product name - use product_name field if available, otherwise fall back to product.name
            if hasattr(item, 'product_name') and item.product_name:
                product_name = item.product_name
            elif item.product and hasattr(item.product, 'name'):
                product_name = item.product.name
            else:
                product_name = 'N/A'
            
            quantity = item.quantity
            unit_price = item.unit_price
            total_price = item.unit_price * item.quantity
            
            data.append([
                (product_name or 'N/A').upper(),
                str(quantity) if quantity else '0',
                f"KSh {unit_price:,.2f}" if unit_price else 'N/A',
                f"KSh {total_price:,.2f}" if total_price else 'N/A'
            ])
        
        # Create table with 4 columns
        table = Table(data, colWidths=[3.5*inch, 1*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#4a5568')),
            
            # Alternating row colors
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f7fafc'), colors.white]),
            
            # Alignment adjustments
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),    # Product Name left
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # Quantity center
            ('ALIGN', (2, 1), (3, -1), 'RIGHT'),   # Prices right
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 30))
    else:
        elements.append(Paragraph("No items in this quotation.", normal_style))
        elements.append(Spacer(1, 30))
    
    # Total Amount
    if quotation.total_amount:
        total_data = [['Total Amount:', f"KSh {quotation.total_amount:,.2f}"]]
        
        total_table = Table(total_data, colWidths=[2*inch, 2*inch])
        total_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#4a5568')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e2e8f0')),
        ]))
        
        elements.append(total_table)
        elements.append(Spacer(1, 30))
    
    # Notes section
    if quotation.notes:
        elements.append(Paragraph("NOTES", heading_style))
        elements.append(Paragraph(quotation.notes, normal_style))
        elements.append(Spacer(1, 20))
    
    # Footer
    footer_text = f"""
    <para align=center>
    <font size=8 color="#95a5a6">
    Generated on {datetime.now(EAT).strftime('%B %d, %Y at %I:%M %p')} by {user_data.firstname} {user_data.lastname}<br/>
    This is a computer-generated document and does not require a signature.
    </font>
    </para>
    """
    elements.append(Spacer(1, 50))
    elements.append(Paragraph(footer_text, normal_style))
    
    # Build PDF
    doc.build(elements)
    
    return output_path 

def create_invoice_pdf_a4(invoice_data, user_data, output_path):
    """
    Create a professional invoice PDF (A4 size) that looks exactly like the quotation
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from datetime import datetime
    import pytz
    
    # Set timezone to East Africa Time
    EAT = pytz.timezone('Africa/Nairobi')
    
    # Create PDF buffer
    if isinstance(output_path, str):
        doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=18)
    else:
        doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # Center alignment
        textColor=colors.HexColor('#2c3e50')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=20,
        textColor=colors.HexColor('#34495e')
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=12
    )
    
    # Try to load the logo
    try:
        logo_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'logo.png')
        if os.path.exists(logo_path):
            logo_image = Image(logo_path, width=1.5*inch, height=1*inch)
            logo_cell = logo_image
        else:
            logo_cell = Paragraph('''
            <para align=left>
            <b><font size=24 color="#1a365d">🔧ABZ</font></b><br/>
            <b><font size=16 color="#f4b942">HARDWARE</font></b><br/>
            <b><font size=14 color="#1a365d">LIMITED</font></b>
            </para>
            ''', normal_style)
    except:
        logo_cell = Paragraph('''
        <para align=left>
        <b><font size=24 color="#1a365d">🔧ABZ</font></b><br/>
        <b><font size=16 color="#f4b942">HARDWARE</font></b><br/>
        <b><font size=14 color="#1a365d">LIMITED</font></b>
        </para>
        ''', normal_style)
    
    # Create letterhead table
    letterhead_data = [[
        logo_cell,
        Paragraph('''
        <para align=right>
        <b><font size=11 color="#1a365d">Kombo Munyiri Road,</font></b><br/>
        <b><font size=11 color="#1a365d">Gikomba, Nairobi, Kenya</font></b><br/>
        <font size=9 color="#666666">0711 732 341 or 0725 000 055</font><br/>
        <font size=9 color="#666666">info@abzhardware.co.ke</font><br/>
        <font size=9 color="#666666">www.abzhardware.co.ke</font>
        </para>
        ''', normal_style)
    ]]
    
    letterhead_table = Table(letterhead_data, colWidths=[3.5*inch, 3.5*inch])
    letterhead_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),
    ]))
    
    elements.append(letterhead_table)
    elements.append(Spacer(1, 10))
    
    # Add colored line separator
    separator_data = [[""]]
    separator_table = Table(separator_data, colWidths=[7*inch], rowHeights=[0.05*inch])
    separator_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f4b942')),
    ]))
    
    elements.append(separator_table)
    elements.append(Spacer(1, 30))
    
    # Invoice Title
    elements.append(Paragraph("INVOICE", title_style))
    elements.append(Spacer(1, 30))
    
    # Invoice Details
    invoice_details = f"""
    <b>Invoice Number:</b> {invoice_data.get('invoice_number', 'N/A')}<br/>
    <b>Order Number:</b> {invoice_data.get('order_id', 'N/A')}<br/>
    <b>Date & Time:</b> {invoice_data.get('order_date', 'N/A')} at {invoice_data.get('order_time', 'N/A')}<br/>
    <b>Branch:</b> {invoice_data.get('branch', 'N/A')}<br/>
    """
    elements.append(Paragraph(invoice_details, normal_style))
    elements.append(Spacer(1, 30))
    
    # Items Table
    if invoice_data.get('order_items'):
        elements.append(Paragraph("ITEMS INVOICED", heading_style))
        
        data = [['Product Name', 'Quantity', 'Unit Price', 'Total Price']]
        
        for item in invoice_data['order_items']:
            product_name = item.get('product_name', 'N/A')
            quantity = item.get('quantity', 0)
            unit_price = item.get('unit_price', 0)
            total_price = item.get('total', 0)
            
            data.append([
                (product_name or 'N/A').upper(),
                str(quantity) if quantity else '0',
                f"KSh {unit_price:,.2f}" if unit_price else 'N/A',
                f"KSh {total_price:,.2f}" if total_price else 'N/A'
            ])
        
        table = Table(data, colWidths=[3.5*inch, 1*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#4a5568')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f7fafc'), colors.white]),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (3, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 30))
    
    # Total Amount
    if invoice_data.get('subtotal'):
        total_data = [['Total Amount:', f"KSh {invoice_data['subtotal']:,.2f}"]]
        total_table = Table(total_data, colWidths=[2*inch, 2*inch])
        total_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#4a5568')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e2e8f0')),
        ]))
        
        elements.append(total_table)
        elements.append(Spacer(1, 30))
    
    # Payment Methods Section
    elements.append(Paragraph("PAYMENT METHODS", heading_style))
    payment_methods = """
    <b>Send Money:</b> 0710460525
    """
    elements.append(Paragraph(payment_methods, normal_style))
    elements.append(Spacer(1, 30))
    
    # Footer
    footer_text = f"""
    <para align=center>
    <font size=8 color="#95a5a6">
    Generated on {datetime.now(EAT).strftime('%B %d, %Y at %I:%M %p')} by {user_data.get('firstname', 'N/A')} {user_data.get('lastname', 'N/A')}<br/>
    This is a computer-generated document and does not require a signature.
    </font>
    </para>
    """
    elements.append(Spacer(1, 50))
    elements.append(Paragraph(footer_text, normal_style))
    
    # Build PDF
    doc.build(elements)
    return output_path