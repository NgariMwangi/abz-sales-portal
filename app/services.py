from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from app import db
from app.models import Order, Payment, Invoice, Receipt, StockTransaction, PasswordReset, User, Product, OrderItem, OrderType
from app.utils import create_invoice_for_order, create_receipt_for_payment
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
            if order.ordertype.name.lower() == 'online':
                if not item_branch_selections:
                    return False, 'Branch selections are required for online orders'
                
                # Validate that all items have branch selections
                for item in order.order_items:
                    if str(item.id) not in item_branch_selections:
                        return False, f'Branch selection required for {item.product.name}'
            
            # Update stock for each item
            for item in order.order_items:
                if order.ordertype.name.lower() == 'online' and item_branch_selections:
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
            return True, 'Order approved successfully!'
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
            is_walk_in = order_type.name.lower() == 'walk-in'
            
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
                negotiated_price = float(item_data.get('negotiated_price', original_price))
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
            
            # Update the negotiated price
            old_final_price = float(order_item.final_price) if order_item.final_price is not None else float(order_item.product.sellingprice)
            order_item.negotiated_price = float(new_price)
            order_item.final_price = float(new_price)
            order_item.negotiation_notes = notes
            order_item.updated_at = datetime.utcnow()
            
            # Recalculate order total
            order = order_item.order
            total_amount = sum(item.quantity * (float(item.final_price) if item.final_price is not None else float(item.product.sellingprice)) for item in order.order_items)
            
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
            
            # Calculate balance and create receipt
            try:
                # Calculate total order amount
                total_order_amount = sum(item.quantity * item.product.sellingprice for item in order.order_items)
                
                # Calculate previous balance (total amount minus previous payments)
                previous_payments = Payment.query.filter_by(
                    orderid=order.id, 
                    payment_status='completed'
                ).filter(Payment.id != payment.id).with_entities(db.func.sum(Payment.amount)).scalar() or 0
                
                previous_balance = float(total_order_amount) - float(previous_payments)
                remaining_balance = previous_balance - float(amount)
                
                # Create receipt
                create_receipt_for_payment(payment, previous_balance, remaining_balance)
                
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