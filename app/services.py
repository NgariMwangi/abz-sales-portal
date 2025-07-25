from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from app import db
from app.models import Order, Payment, Invoice, Receipt, StockTransaction, PasswordReset, User, Product, OrderItem, OrderType
from app.utils import create_invoice_for_order, create_receipt_for_payment
from app.pdf_utils import generate_invoice_pdf
from email_service import get_email_service


class OrderService:
    """Service class for order-related operations"""
    
    @staticmethod
    def approve_order(order_id, current_user, item_branch_selections=None):
        """Approve an order and update stock"""
        order = Order.query.get_or_404(order_id)
        if not order.approvalstatus:
            order.approvalstatus = True
            order.approved_at = datetime.utcnow()
            
            # For online orders, require branch selections for each item
            if 'online' in order.ordertype.name.lower():
                if not item_branch_selections:
                    return False, 'Branch selections are required for online orders'
                
                # Validate that all items have branch selections
                for item in order.order_items:
                    if str(item.id) not in item_branch_selections:
                        return False, f'Branch selection required for {item.product.name}'
            
            # Update stock for each item
            for item in order.order_items:
                if 'online' in order.ordertype.name.lower() and item_branch_selections:
                    # For online orders, reduce stock from the selected branch for this item
                    selected_branch_id = item_branch_selections.get(str(item.id))
                    if not selected_branch_id:
                        return False, f'Branch selection required for {item.product.name}'
                    
                    # Find the product in the selected branch
                    product_in_branch = Product.query.filter_by(
                        productcode=item.product.productcode,
                        branchid=selected_branch_id
                    ).first()
                    
                    if not product_in_branch:
                        return False, f'Product {item.product.name} not available in selected branch'
                    
                    if product_in_branch.stock < item.quantity:
                        return False, f'Insufficient stock for {item.product.name} in selected branch (required: {item.quantity}, available: {product_in_branch.stock})'
                    
                    # Update stock from the selected branch
                    previous_stock = product_in_branch.stock
                    product_in_branch.stock -= item.quantity
                    new_stock = product_in_branch.stock
                    
                    # Create stock transaction record for the selected branch product
                    stock_transaction = StockTransaction(
                        productid=product_in_branch.id,
                        userid=current_user.id,
                        transaction_type='remove',
                        quantity=item.quantity,
                        previous_stock=previous_stock,
                        new_stock=new_stock,
                        notes=f'Order #{order.id} approved - {item.product.name} fulfilled from branch {product_in_branch.branch.name}'
                    )
                    db.session.add(stock_transaction)
                else:
                    # For non-online orders, reduce stock from the original product
                    product = item.product
                    previous_stock = product.stock
                    product.stock -= item.quantity
                    new_stock = product.stock
                    
                    # Create stock transaction record
                    stock_transaction = StockTransaction(
                        productid=product.id,
                        userid=current_user.id,
                        transaction_type='remove',
                        quantity=item.quantity,
                        previous_stock=previous_stock,
                        new_stock=new_stock,
                        notes=f'Order #{order.id} approved'
                    )
                    db.session.add(stock_transaction)
            
            db.session.commit()
            
            # Generate and send PDF invoice
            try:
                # Check if invoice exists, if not create one
                invoice = Invoice.query.filter_by(orderid=order.id).first()
                if not invoice:
                    # Calculate total amount for the order
                    total_amount = 0
                    for item in order.order_items:
                        if item.final_price is not None:
                            item_price = float(item.final_price)
                        elif item.product.sellingprice is not None:
                            item_price = float(item.product.sellingprice)
                        else:
                            item_price = 0.0
                        total_amount += item.quantity * item_price
                    
                    # Create invoice for the order
                    invoice = create_invoice_for_order(order, total_amount)
                    print(f"Created invoice {invoice.invoice_number} for order {order.id}")
                
                # Generate PDF and send email
                pdf_data = generate_invoice_pdf(invoice.id)
                email_service = get_email_service()
                if email_service:
                    email_result = email_service.send_invoice_email(
                        to_email=order.user.email,
                        user_name=f"{order.user.firstname} {order.user.lastname}",
                        order_id=order.id,
                        invoice_number=invoice.invoice_number,
                        pdf_attachment=pdf_data.getvalue()
                    )
                    if not email_result['success']:
                        print(f"Warning: Could not send invoice PDF to {order.user.email}: {email_result.get('error', 'Unknown error')}")
                else:
                    print(f"Warning: Email service not available for sending invoice PDF to {order.user.email}")
            except Exception as e:
                print(f"Warning: Could not generate or send invoice PDF for order {order.id}: {str(e)}")

            return True, 'Order approved successfully! Invoice has been generated and sent to your email.'
        return False, 'Order is already approved.'
    
    @staticmethod
    def reject_order(order_id):
        """Reject and delete an order"""
        order = Order.query.get_or_404(order_id)
        db.session.delete(order)
        db.session.commit()
        return True, 'Order rejected and deleted.'
    
    @staticmethod
    def create_order(data, current_user):
        """Create a new order with items"""
        try:
            # Create order
            order = Order(
                userid=current_user.id,
                ordertypeid=int(data['order_type_id']),
                branchid=int(data['branch_id'])
            )
            db.session.add(order)
            db.session.flush()
            
            # Get order type to determine if it's walk-in
            order_type = OrderType.query.get(order.ordertypeid)
            is_walk_in = 'walk' in order_type.name.lower()
            
            # Add order items
            total_amount = 0
            items_data = data.get('items', [])
            
            for item_data in items_data:
                if not item_data.get('product_id') or not item_data.get('quantity'):
                    raise ValueError('Product ID and quantity are required for each item')
                
                product = Product.query.get_or_404(int(item_data['product_id']))
                quantity = int(item_data['quantity'])
                
                if quantity <= 0:
                    raise ValueError(f'Invalid quantity for product {product.name}')
                
                # For walk-in orders, use buying price as original price
                # For online orders, use selling price as original price
                if is_walk_in:
                    if product.buyingprice is not None and product.buyingprice > 0:
                        original_price = float(product.buyingprice)
                    elif product.sellingprice is not None and product.sellingprice > 0:
                        original_price = float(product.sellingprice)
                    else:
                        raise ValueError(f'Product {product.name} has no valid price (buying or selling price is missing or zero)')
                else:
                    if product.sellingprice is not None and product.sellingprice > 0:
                        original_price = float(product.sellingprice)
                    else:
                        raise ValueError(f'Product {product.name} has no valid selling price')
                
                # Handle negotiated price if provided
                negotiated_price_raw = item_data.get('negotiated_price')
                if negotiated_price_raw is not None:
                    negotiated_price = float(negotiated_price_raw)
                else:
                    negotiated_price = original_price
                final_price = negotiated_price if negotiated_price != original_price else original_price
                negotiation_notes = item_data.get('negotiation_notes', None)
                
                order_item = OrderItem(
                    orderid=order.id,
                    productid=product.id,
                    quantity=quantity,
                    buying_price=float(product.buyingprice) if product.buyingprice is not None and product.buyingprice > 0 else None,
                    original_price=original_price,
                    negotiated_price=negotiated_price if negotiated_price != original_price else None,
                    final_price=final_price,
                    negotiation_notes=negotiation_notes or ''
                )
                db.session.add(order_item)
                total_amount += final_price * quantity
            
            db.session.commit()
            
            # Create invoice for the order
            try:
                create_invoice_for_order(order, total_amount)
            except Exception as e:
                print(f"Warning: Could not create invoice for order {order.id}: {str(e)}")
            
            return True, order.id, total_amount
            
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def negotiate_price(order_item_id, new_price, notes, current_user):
        """Negotiate price for a specific order item"""
        try:
            order_item = OrderItem.query.get_or_404(order_item_id)
            
            # Check if order is still pending (can't negotiate approved orders)
            if order_item.order.approvalstatus:
                return False, 'Cannot negotiate prices for approved orders'
            
            # Check if there are any actual changes
            if order_item.final_price is not None:
                current_price = float(order_item.final_price)
            elif order_item.product.sellingprice is not None:
                current_price = float(order_item.product.sellingprice)
            else:
                return False, 'Product has no valid selling price'
            current_notes = order_item.negotiation_notes or ''
            
            # Check if price or notes have actually changed
            price_changed = abs(float(new_price) - current_price) > 0.01  # Allow for small floating point differences
            notes_changed = notes.strip() != current_notes.strip()
            
            if not price_changed and not notes_changed:
                return True, 'No changes made to this item'
            
            # Update the negotiated price
            order_item.negotiated_price = float(new_price)
            order_item.final_price = float(new_price)
            order_item.negotiation_notes = notes
            order_item.updated_at = datetime.utcnow()
            
            # Recalculate order total
            order = order_item.order
            total_amount = 0
            for item in order.order_items:
                if item.final_price is not None:
                    item_price = float(item.final_price)
                elif item.product.sellingprice is not None:
                    item_price = float(item.product.sellingprice)
                else:
                    item_price = 0.0
                total_amount += item.quantity * item_price
            
            db.session.commit()
            
            return True, f'Price negotiated successfully. New total: KSh{total_amount:.2f}'
            
        except Exception as e:
            db.session.rollback()
            raise e


class PaymentService:
    """Service class for payment-related operations"""
    
    @staticmethod
    def process_payment(order_id, data, current_user):
        """Process a payment for an order"""
        try:
            order = Order.query.get_or_404(order_id)
            
            amount = float(data['amount'])
            payment_method = data['payment_method']
            
            # Generate reference number
            reference_number = f"PAY-{order_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # Create payment record
            payment = Payment(
                orderid=order.id,
                userid=current_user.id,
                amount=amount,
                payment_method=payment_method,
                payment_status='completed',
                reference_number=reference_number,
                transaction_id=data.get('transaction_id'),
                notes=data.get('notes'),
                payment_date=datetime.utcnow()
            )
            
            db.session.add(payment)
            
            # Update order payment status
            order.payment_status = 'paid'
            
            db.session.commit()
            
            # Calculate balance and create receipt (keep this synchronous for immediate feedback)
            try:
                # Calculate total order amount
                total_order_amount = 0
                for item in order.order_items:
                    if item.final_price is not None:
                        item_price = float(item.final_price)
                    elif item.product.sellingprice is not None:
                        item_price = float(item.product.sellingprice)
                    else:
                        item_price = 0.0
                    total_order_amount += item.quantity * item_price
                
                # Calculate previous balance (total amount minus previous payments)
                previous_payments = Payment.query.filter_by(
                    orderid=order.id, 
                    payment_status='completed'
                ).filter(Payment.id != payment.id).with_entities(db.func.sum(Payment.amount)).scalar() or 0
                
                previous_balance = float(total_order_amount) - float(previous_payments)
                remaining_balance = previous_balance - float(amount)
                
                # Create receipt
                receipt = create_receipt_for_payment(payment, previous_balance, remaining_balance)
                
                # Send email asynchronously (don't wait for it)
                import threading
                def send_receipt_email_async():
                    try:
                        from app.pdf_utils import generate_receipt_pdf
                        from email_service import get_email_service
                        
                        pdf_buffer = generate_receipt_pdf(receipt.id)
                        email_service = get_email_service()
                        
                        if email_service:
                            email_result = email_service.send_receipt_email(
                                to_email=order.user.email,
                                user_name=f"{order.user.firstname} {order.user.lastname}",
                                order_id=order.id,
                                receipt_number=receipt.receipt_number,
                                payment_amount=float(receipt.payment_amount),
                                pdf_attachment=pdf_buffer.getvalue()
                            )
                            if not email_result['success']:
                                print(f"Warning: Could not send receipt PDF to {order.user.email}: {email_result.get('error', 'Unknown error')}")
                        else:
                            print(f"Warning: Email service not available for sending receipt PDF to {order.user.email}")
                            
                    except Exception as e:
                        print(f"Warning: Could not send receipt email for payment {payment.id}: {str(e)}")
                
                # Start email sending in background thread
                email_thread = threading.Thread(target=send_receipt_email_async)
                email_thread.daemon = True
                email_thread.start()
                
            except Exception as e:
                print(f"Warning: Could not create receipt for payment {payment.id}: {str(e)}")
            
            return True, payment.id, reference_number
            
        except Exception as e:
            db.session.rollback()
            raise e


class StockService:
    """Service class for stock-related operations"""
    
    @staticmethod
    def add_stock(product_id, quantity, current_user, notes=None):
        """Add stock to a product"""
        try:
            product = Product.query.get_or_404(product_id)
            
            previous_stock = product.stock
            product.stock += quantity
            new_stock = product.stock
            
            stock_transaction = StockTransaction(
                productid=product.id,
                userid=current_user.id,
                transaction_type='add',
                quantity=quantity,
                previous_stock=previous_stock,
                new_stock=new_stock,
                notes=notes or 'Stock added via web form'
            )
            
            db.session.add(stock_transaction)
            db.session.commit()
            
            return True, new_stock
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def remove_stock(product_id, quantity, current_user, notes=None):
        """Remove stock from a product"""
        try:
            product = Product.query.get_or_404(product_id)
            
            if product.stock < quantity:
                raise ValueError('Insufficient stock')
            
            previous_stock = product.stock
            product.stock -= quantity
            new_stock = product.stock
            
            stock_transaction = StockTransaction(
                productid=product.id,
                userid=current_user.id,
                transaction_type='remove',
                quantity=quantity,
                previous_stock=previous_stock,
                new_stock=new_stock,
                notes=notes or 'Stock removed via web form'
            )
            
            db.session.add(stock_transaction)
            db.session.commit()
            
            return True, new_stock
            
        except Exception as e:
            db.session.rollback()
            raise e


class AuthService:
    """Service class for authentication-related operations"""
    
    @staticmethod
    def send_password_reset(email):
        """Send password reset email"""
        try:
            user = User.query.filter_by(email=email).first()
            
            if not user or user.role != 'sales':
                return False, 'Email not found or user is not a sales staff'
            
            # Generate reset token
            token = PasswordReset.generate_token()
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            # Create password reset record
            password_reset = PasswordReset(
                user_id=user.id,
                token=token,
                expires_at=expires_at
            )
            
            # Delete any existing unused tokens for this user
            PasswordReset.query.filter_by(user_id=user.id, used=False).delete()
            
            db.session.add(password_reset)
            db.session.commit()
            
            return True, user, token
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def reset_password(token, new_password):
        """Reset password using token"""
        try:
            # Find the password reset record
            password_reset = PasswordReset.query.filter_by(token=token, used=False).first()
            
            if not password_reset:
                return False, 'Invalid or expired reset token'
            
            if password_reset.is_expired():
                return False, 'Reset token has expired'
            
            # Update user password
            user = password_reset.user
            user.password = generate_password_hash(new_password)
            
            # Mark token as used
            password_reset.used = True
            
            db.session.commit()
            
            # Send password change alert email
            try:
                email_service = get_email_service()
                if email_service:
                    change_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                    email_result = email_service.send_password_change_alert(
                        to_email=user.email,
                        user_name=f"{user.firstname} {user.lastname}",
                        change_time=change_time
                    )
                    
                    if not email_result['success']:
                        print(f"Warning: Could not send password change alert to {user.email}: {email_result.get('error', 'Unknown error')}")
                else:
                    print(f"Warning: Email service not available for password change alert to {user.email}")
            except Exception as e:
                print(f"Warning: Error sending password change alert to {user.email}: {str(e)}")
            
            return True, 'Password reset successfully'
            
        except Exception as e:
            db.session.rollback()
            raise e 

class QuotationService:
    """Service class for quotation-related operations"""
    
    @staticmethod
    def generate_quotation_number():
        """Generate a unique quotation number"""
        import random
        import string
        
        while True:
            # Generate a random 6-digit number
            number = ''.join(random.choices(string.digits, k=6))
            quotation_number = f"QT-{number}"
            
            # Check if it already exists
            from app.models import Quotation
            existing = Quotation.query.filter_by(quotation_number=quotation_number).first()
            if not existing:
                return quotation_number
    
    @staticmethod
    def create_quotation(data, current_user):
        """Create a new quotation"""
        try:
            from app.models import Quotation, QuotationItem, Product
            
            # Generate quotation number
            quotation_number = QuotationService.generate_quotation_number()
            
            # Create quotation
            quotation = Quotation(
                quotation_number=quotation_number,
                customer_name=data['customer_name'],
                customer_email=data.get('customer_email'),
                customer_phone=data.get('customer_phone'),
                created_by=current_user.id,
                branch_id=int(data['branch_id']),
                valid_until=datetime.strptime(data['valid_until'], '%Y-%m-%d') if data.get('valid_until') else None,
                notes=data.get('notes', ''),
                subtotal=0.00,
                total_amount=0.00
            )
            
            db.session.add(quotation)
            db.session.flush()
            
            # Add quotation items
            total_amount = 0
            items_data = data.get('items', [])
            
            for item_data in items_data:
                if not item_data.get('product_id') or not item_data.get('quantity'):
                    raise ValueError('Product ID and quantity are required for each item')
                
                product = Product.query.get_or_404(int(item_data['product_id']))
                quantity = int(item_data['quantity'])
                unit_price = float(item_data.get('unit_price', product.sellingprice or 0))
                
                if quantity <= 0:
                    raise ValueError(f'Invalid quantity for product {product.name}')
                
                item_total = quantity * unit_price
                total_amount += item_total
                
                quotation_item = QuotationItem(
                    quotation_id=quotation.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=item_total,
                    notes=item_data.get('notes', '')
                )
                db.session.add(quotation_item)
            
            # Update quotation totals
            quotation.subtotal = total_amount
            quotation.total_amount = total_amount
            
            db.session.commit()
            
            return True, quotation.id, total_amount
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def update_quotation_status(quotation_id, status):
        """Update quotation status"""
        try:
            from app.models import Quotation
            quotation = Quotation.query.get_or_404(quotation_id)
            quotation.status = status
            quotation.updated_at = datetime.utcnow()
            db.session.commit()
            return True, f'Quotation status updated to {status}'
        except Exception as e:
            db.session.rollback()
            raise e 