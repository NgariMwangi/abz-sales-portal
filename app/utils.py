from datetime import datetime, timedelta
from app import db
from app.models import Invoice, Receipt


def generate_invoice_number():
    """Generate a unique invoice number in format INV-YYYYMMDD-XXXX"""
    today = datetime.utcnow().strftime('%Y%m%d')
    
    # Get the last invoice number for today
    last_invoice = Invoice.query.filter(
        Invoice.invoice_number.like(f'INV-{today}-%')
    ).order_by(Invoice.invoice_number.desc()).first()
    
    if last_invoice:
        # Extract the sequence number and increment
        last_sequence = int(last_invoice.invoice_number.split('-')[-1])
        new_sequence = last_sequence + 1
    else:
        new_sequence = 1
    
    return f'INV-{today}-{new_sequence:04d}'


def generate_receipt_number():
    """Generate a unique receipt number in format RCP-YYYYMMDD-XXXX"""
    today = datetime.utcnow().strftime('%Y%m%d')
    
    # Get the last receipt number for today
    last_receipt = Receipt.query.filter(
        Receipt.receipt_number.like(f'RCP-{today}-%')
    ).order_by(Receipt.receipt_number.desc()).first()
    
    if last_receipt:
        # Extract the sequence number and increment
        last_sequence = int(last_receipt.receipt_number.split('-')[-1])
        new_sequence = last_sequence + 1
    else:
        new_sequence = 1
    
    return f'RCP-{today}-{new_sequence:04d}'


def create_invoice_for_order(order, total_amount):
    """Create an invoice for a given order"""
    try:
        print(f"Creating invoice for order {order.id} with total amount {total_amount}")
        
        invoice_number = generate_invoice_number()
        print(f"Generated invoice number: {invoice_number}")
        
        invoice = Invoice(
            orderid=order.id,
            invoice_number=invoice_number,
            total_amount=total_amount,
            subtotal=total_amount,
            tax_amount=0.00,  # Can be calculated based on business rules
            discount_amount=0.00,  # Can be applied based on business rules
            status='pending',
            due_date=datetime.utcnow() + timedelta(days=30),  # 30 days from creation
            notes=f'Invoice generated for Order #{order.id}'
        )
        
        print(f"Created invoice object: {invoice.invoice_number}")
        db.session.add(invoice)
        db.session.commit()
        print(f"Successfully saved invoice {invoice.invoice_number} to database")
        
        return invoice
    except Exception as e:
        print(f"Error creating invoice for order {order.id}: {str(e)}")
        db.session.rollback()
        raise e


def create_receipt_for_payment(payment, previous_balance, remaining_balance):
    """Create a receipt for a given payment"""
    receipt_number = generate_receipt_number()
    
    receipt = Receipt(
        paymentid=payment.id,
        orderid=payment.orderid,
        receipt_number=receipt_number,
        payment_amount=payment.amount,
        previous_balance=previous_balance,
        remaining_balance=remaining_balance,
        payment_method=payment.payment_method,
        reference_number=payment.reference_number,
        transaction_id=payment.transaction_id,
        notes=f'Receipt for payment {payment.reference_number}'
    )
    
    db.session.add(receipt)
    db.session.commit()
    return receipt


def send_password_change_alert(user_email, user_name):
    """Send password change alert email to user"""
    try:
        from email_service import get_email_service
        email_service = get_email_service()
        
        if email_service:
            change_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            email_result = email_service.send_password_change_alert(
                to_email=user_email,
                user_name=user_name,
                change_time=change_time
            )
            
            if email_result['success']:
                print(f"✅ Password change alert sent to {user_email}")
                return True
            else:
                print(f"❌ Failed to send password change alert to {user_email}: {email_result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"⚠️ Email service not available for password change alert to {user_email}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending password change alert to {user_email}: {str(e)}")
        return False 