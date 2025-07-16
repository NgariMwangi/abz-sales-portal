from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime
import os
from app.models import Order, Invoice, OrderItem
from app import db


def generate_invoice_pdf(invoice_id):
    """
    Generate a PDF invoice for the given invoice ID (80mm format like receipt)
    
    Args:
        invoice_id: ID of the invoice to generate PDF for
        
    Returns:
        BytesIO object containing the PDF data
    """
    # Get invoice and related data
    invoice = Invoice.query.get_or_404(invoice_id)
    order = invoice.order
    user = order.user
    
    # Create PDF buffer with 80mm width (approximately 226 points)
    buffer = BytesIO()
    page_width = 226  # 80mm in points
    page_height = 800  # Auto-height
    doc = SimpleDocTemplate(buffer, pagesize=(page_width, page_height), 
                           rightMargin=10, leftMargin=10, topMargin=10, bottomMargin=10)
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Create custom styles for 80mm invoice (matching receipt)
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=6,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'InvoiceSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'InvoiceNormal',
        parent=styles['Normal'],
        fontSize=8,
        spaceAfter=2,
        alignment=TA_LEFT,
        textColor=colors.black,
        fontName='Helvetica'
    )
    
    center_style = ParagraphStyle(
        'InvoiceCenter',
        parent=styles['Normal'],
        fontSize=8,
        spaceAfter=2,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Helvetica'
    )
    
    # Build PDF content
    story = []
    
    # Add logo if available
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'logo.png')
    if os.path.exists(logo_path):
        try:
            # Add logo at the top, centered
            logo = Image(logo_path, width=60, height=40, kind='proportional')
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 4))
        except Exception as e:
            print(f"Error loading logo: {str(e)}")
    
    # Header
    story.append(Paragraph("ABZ HARDWARE", title_style))
    story.append(Paragraph("INVOICE", subtitle_style))
    story.append(Spacer(1, 8))
    
    # Invoice details
    story.append(Paragraph(f"Invoice #: {invoice.invoice_number}", normal_style))
    story.append(Paragraph(f"Date: {invoice.created_at.strftime('%Y-%m-%d %H:%M')}", normal_style))
    story.append(Paragraph(f"Order #: {order.id}", normal_style))
    story.append(Paragraph(f"Due: {invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else 'N/A'}", normal_style))
    story.append(Spacer(1, 6))
    
    # Customer information
    # Check if it's a walk-in order
    if order.ordertype.name.lower() == 'walk-in':
        story.append(Paragraph("Served by:", subtitle_style))
        story.append(Paragraph(f"{user.firstname} {user.lastname}", normal_style))
    else:
        story.append(Paragraph("CUSTOMER INFO", subtitle_style))
        story.append(Paragraph(f"Name: {user.firstname} {user.lastname}", normal_style))
        story.append(Paragraph(f"Email: {user.email}", normal_style))
        if hasattr(user, 'phone') and user.phone:
            story.append(Paragraph(f"Phone: {user.phone}", normal_style))
    
    story.append(Spacer(1, 6))
    
    # Order items
    story.append(Paragraph("ORDER ITEMS", subtitle_style))
    
    # Calculate totals
    total_amount = 0
    order_items_data = []
    
    for item in order.order_items:
        # Use final_price for calculations (includes negotiated prices)
        if item.final_price is not None:
            final_price = float(item.final_price)
        elif item.product.sellingprice is not None:
            final_price = float(item.product.sellingprice)
        else:
            final_price = 0.0  # Fallback to zero if no price available
        item_total = item.quantity * final_price
        total_amount += item_total
        
        order_items_data.append([
            item.product.name,
            str(item.quantity),
            f"{final_price:.2f}",
            f"{item_total:.2f}"
        ])
    
    # Create compact table for 80mm width
    table_data = []
    
    # Add header row
    table_data.append(['Product', 'Qty', 'Price', 'Total'])
    
    for item in order_items_data:
        # Truncate product name if too long
        product_name = item[0][:20] + "..." if len(item[0]) > 20 else item[0]
        table_data.append([product_name, item[1], item[2], item[3]])
    
    # Add totals rows (no tax or discount)
    table_data.append(['', '', 'Subtotal:', f"{total_amount:.2f}"])
    table_data.append(['', '', 'TOTAL:', f"KSh{float(invoice.total_amount):.2f}"])
    
    # Create table with better spacing for 80mm width
    # Total width: 206 points (226 - 20 margin)
    # Column widths: Product(90) + Qty(25) + Price(45) + Total(46) = 206
    col_widths = [90, 25, 45, 46]
    invoice_table = Table(table_data, colWidths=col_widths)
    invoice_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),      # Product name left-aligned
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),    # Quantity center-aligned
        ('ALIGN', (2, 0), (3, -1), 'RIGHT'),     # Prices right-aligned
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header row bold
        ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'), # Totals rows bold
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),  # Header line
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),  # Header bottom line
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Header background
    ]))
    
    story.append(invoice_table)
    story.append(Spacer(1, 8))
    
    # Payment information
    story.append(Paragraph("PAYMENT INFO", subtitle_style))
    story.append(Paragraph(f"Status: {order.payment_status.title()}", normal_style))
    story.append(Paragraph(f"Amount: KSh{float(invoice.total_amount):.2f}", normal_style))
    
    # Add payment history if any
    if order.payments:
        story.append(Spacer(1, 4))
        story.append(Paragraph("Payment History:", normal_style))
        for payment in order.payments:
            story.append(Paragraph(f"  {payment.payment_date.strftime('%Y-%m-%d %H:%M')} - KSh{float(payment.amount):.2f} ({payment.payment_method})", normal_style))
    
    story.append(Spacer(1, 8))
    
    # Footer
    story.append(Paragraph("Thank you for your business!", center_style))
    story.append(Paragraph("ABZ Hardware", center_style))
    story.append(Paragraph("Quality Hardware Solutions", center_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


def save_invoice_pdf(invoice_id, filepath):
    """
    Generate and save PDF invoice to a file
    
    Args:
        invoice_id: ID of the invoice to generate PDF for
        filepath: Path where to save the PDF file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        pdf_buffer = generate_invoice_pdf(invoice_id)
        
        with open(filepath, 'wb') as f:
            f.write(pdf_buffer.getvalue())
        
        return True
    except Exception as e:
        print(f"Error generating PDF invoice: {str(e)}")
        return False


def generate_receipt_pdf(receipt_id):
    """
    Generate professional 80mm receipt PDF
    
    Args:
        receipt_id: ID of the receipt to generate PDF for
        
    Returns:
        BytesIO: PDF buffer
    """
    from app.models import Receipt, Order, User
    
    # Get receipt and related data
    receipt = Receipt.query.get_or_404(receipt_id)
    order = receipt.order
    user = order.user
    payment = receipt.payment
    
    # Create PDF buffer with 80mm width (approximately 226 points)
    buffer = BytesIO()
    page_width = 226  # 80mm in points
    page_height = 800  # Auto-height
    doc = SimpleDocTemplate(buffer, pagesize=(page_width, page_height), 
                           rightMargin=10, leftMargin=10, topMargin=10, bottomMargin=10)
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Create custom styles for 80mm receipt
    title_style = ParagraphStyle(
        'ReceiptTitle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=6,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'ReceiptSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'ReceiptNormal',
        parent=styles['Normal'],
        fontSize=8,
        spaceAfter=2,
        alignment=TA_LEFT,
        textColor=colors.black,
        fontName='Helvetica'
    )
    
    center_style = ParagraphStyle(
        'ReceiptCenter',
        parent=styles['Normal'],
        fontSize=8,
        spaceAfter=2,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Helvetica'
    )
    
    # Build PDF content
    story = []
    
    # Add logo if available
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'logo.png')
    if os.path.exists(logo_path):
        try:
            # Add logo at the top, centered
            logo = Image(logo_path, width=60, height=40, kind='proportional')
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 4))
        except Exception as e:
            print(f"Error loading logo: {str(e)}")
    
    # Header
    story.append(Paragraph("ABZ HARDWARE", title_style))
    story.append(Paragraph("Sales Receipt", subtitle_style))
    story.append(Spacer(1, 8))
    
    # Receipt details
    story.append(Paragraph(f"Receipt #: {receipt.receipt_number}", normal_style))
    story.append(Paragraph(f"Date: {receipt.created_at.strftime('%Y-%m-%d %H:%M')}", normal_style))
    story.append(Paragraph(f"Order #: {order.id}", normal_style))
    story.append(Spacer(1, 6))
    
    # Payment information
    story.append(Paragraph("PAYMENT DETAILS", subtitle_style))
    story.append(Paragraph(f"Method: {payment.payment_method.replace('_', ' ').title()}", normal_style))
    story.append(Paragraph(f"Amount: KSh{float(receipt.payment_amount):.2f}", normal_style))
    
    if receipt.reference_number:
        story.append(Paragraph(f"Ref: {receipt.reference_number}", normal_style))
    
    if receipt.transaction_id:
        story.append(Paragraph(f"Txn: {receipt.transaction_id}", normal_style))
    
    story.append(Spacer(1, 6))
    
    # Order items
    story.append(Paragraph("ORDER ITEMS", subtitle_style))
    
    # Calculate order total
    total_amount = 0
    order_items_data = []
    
    for item in order.order_items:
        # Use final_price for calculations (includes negotiated prices)
        if item.final_price is not None:
            final_price = float(item.final_price)
        elif item.product.sellingprice is not None:
            final_price = float(item.product.sellingprice)
        else:
            final_price = 0.0
        item_total = item.quantity * final_price
        total_amount += item_total
        
        order_items_data.append([
            item.product.name,
            str(item.quantity),
            f"{final_price:.2f}",
            f"{item_total:.2f}"
        ])
    
    # Create compact table for 80mm width
    table_data = []
    
    # Add header row
    table_data.append(['Product', 'Qty', 'Price', 'Total'])
    
    for item in order_items_data:
        # Truncate product name if too long
        product_name = item[0][:20] + "..." if len(item[0]) > 20 else item[0]
        table_data.append([product_name, item[1], item[2], item[3]])
    
    # Add total row (no tax or discount rows)
    table_data.append(['', '', 'TOTAL:', f"KSh{total_amount:.2f}"])
    
    # Create table with better spacing for 80mm width
    # Total width: 206 points (226 - 20 margin)
    # Column widths: Product(90) + Qty(25) + Price(45) + Total(46) = 206
    col_widths = [90, 25, 45, 46]
    receipt_table = Table(table_data, colWidths=col_widths)
    receipt_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),      # Product name left-aligned
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),    # Quantity center-aligned
        ('ALIGN', (2, 0), (3, -1), 'RIGHT'),     # Prices right-aligned
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header row bold
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'), # Total row bold
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),  # Header line
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),  # Header bottom line
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Header background
    ]))
    
    story.append(receipt_table)
    story.append(Spacer(1, 8))
    
    # Footer
    story.append(Paragraph("Thank you for your business!", center_style))
    story.append(Paragraph("ABZ Hardware", center_style))
    story.append(Paragraph("Quality Hardware Solutions", center_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


def save_receipt_pdf(receipt_id, filepath):
    """
    Generate and save PDF receipt to a file
    
    Args:
        receipt_id: ID of the receipt to generate PDF for
        filepath: Path where to save the PDF file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        pdf_buffer = generate_receipt_pdf(receipt_id)
        
        with open(filepath, 'wb') as f:
            f.write(pdf_buffer.getvalue())
        
        return True
    except Exception as e:
        print(f"Error generating PDF receipt: {str(e)}")
        return False 


def generate_quotation_pdf(quotation_id):
    """
    Generate a PDF quotation for the given quotation ID (80mm format like receipt)
    
    Args:
        quotation_id: ID of the quotation to generate PDF for
        
    Returns:
        BytesIO object containing the PDF data
    """
    from app.models import Quotation
    
    # Get quotation and related data
    quotation = Quotation.query.get_or_404(quotation_id)
    
    # Create PDF buffer with 80mm width (approximately 226 points)
    buffer = BytesIO()
    page_width = 226  # 80mm in points
    page_height = 800  # Auto-height
    doc = SimpleDocTemplate(buffer, pagesize=(page_width, page_height), 
                           rightMargin=10, leftMargin=10, topMargin=10, bottomMargin=10)
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Create custom styles for 80mm quotation (matching receipt)
    title_style = ParagraphStyle(
        'QuotationTitle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=6,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'QuotationSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'QuotationNormal',
        parent=styles['Normal'],
        fontSize=8,
        spaceAfter=2,
        alignment=TA_LEFT,
        textColor=colors.black,
        fontName='Helvetica'
    )
    
    center_style = ParagraphStyle(
        'QuotationCenter',
        parent=styles['Normal'],
        fontSize=8,
        spaceAfter=2,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Helvetica'
    )
    
    # Build PDF content
    story = []
    
    # Add logo if available
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'logo.png')
    if os.path.exists(logo_path):
        try:
            # Add logo at the top, centered
            logo = Image(logo_path, width=60, height=40, kind='proportional')
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 4))
        except Exception as e:
            print(f"Error loading logo: {str(e)}")
    
    # Header
    story.append(Paragraph("ABZ HARDWARE", title_style))
    story.append(Paragraph("QUOTATION", subtitle_style))
    story.append(Spacer(1, 8))
    
    # Quotation details
    story.append(Paragraph(f"Quotation #: {quotation.quotation_number}", normal_style))
    story.append(Paragraph(f"Date: {quotation.created_at.strftime('%Y-%m-%d %H:%M')}", normal_style))
    if quotation.valid_until:
        story.append(Paragraph(f"Valid until: {quotation.valid_until.strftime('%Y-%m-%d')}", normal_style))
    story.append(Paragraph(f"Status: {quotation.status.title()}", normal_style))
    story.append(Spacer(1, 6))
    
    # Customer information
    story.append(Paragraph("CUSTOMER INFO", subtitle_style))
    story.append(Paragraph(f"Name: {quotation.customer_name}", normal_style))
    if quotation.customer_email:
        story.append(Paragraph(f"Email: {quotation.customer_email}", normal_style))
    if quotation.customer_phone:
        story.append(Paragraph(f"Phone: {quotation.customer_phone}", normal_style))
    story.append(Spacer(1, 6))
    
    # Quotation items
    story.append(Paragraph("QUOTATION ITEMS", subtitle_style))
    
    # Calculate totals
    total_amount = 0
    quotation_items_data = []
    
    for item in quotation.items:
        unit_price = float(item.unit_price)
        item_total = item.quantity * unit_price
        total_amount += item_total
        
        quotation_items_data.append([
            item.product.name,
            str(item.quantity),
            f"{unit_price:.2f}",
            f"{item_total:.2f}"
        ])
    
    # Create compact table for 80mm width
    table_data = []
    
    # Add header row
    table_data.append(['Product', 'Qty', 'Price', 'Total'])
    
    for item in quotation_items_data:
        # Truncate product name if too long
        product_name = item[0][:20] + "..." if len(item[0]) > 20 else item[0]
        table_data.append([product_name, item[1], item[2], item[3]])
    
    # Add totals rows
    table_data.append(['', '', 'Subtotal:', f"{total_amount:.2f}"])
    table_data.append(['', '', 'TOTAL:', f"KSh{float(quotation.total_amount):.2f}"])
    
    # Create table with better spacing for 80mm width
    # Total width: 206 points (226 - 20 margin)
    # Column widths: Product(90) + Qty(25) + Price(45) + Total(46) = 206
    col_widths = [90, 25, 45, 46]
    quotation_table = Table(table_data, colWidths=col_widths)
    quotation_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),      # Product name left-aligned
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),    # Quantity center-aligned
        ('ALIGN', (2, 0), (3, -1), 'RIGHT'),     # Prices right-aligned
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header row bold
        ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'), # Totals rows bold
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),  # Header line
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),  # Header bottom line
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Header background
    ]))
    
    story.append(quotation_table)
    story.append(Spacer(1, 8))
    
    # Notes if any
    if quotation.notes:
        story.append(Paragraph("NOTES", subtitle_style))
        story.append(Paragraph(quotation.notes, normal_style))
        story.append(Spacer(1, 8))
    
    # Footer
    story.append(Paragraph("Thank you for your interest!", center_style))
    story.append(Paragraph("ABZ Hardware", center_style))
    story.append(Paragraph("Quality Hardware Solutions", center_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


def save_quotation_pdf(quotation_id, filepath):
    """
    Generate and save PDF quotation to a file
    
    Args:
        quotation_id: ID of the quotation to generate PDF for
        filepath: Path where to save the PDF file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        pdf_buffer = generate_quotation_pdf(quotation_id)
        
        with open(filepath, 'wb') as f:
            f.write(pdf_buffer.getvalue())
        
        return True
    except Exception as e:
        print(f"Error generating PDF quotation: {str(e)}")
        return False 