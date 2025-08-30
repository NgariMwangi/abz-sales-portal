from flask import Flask, jsonify, request, render_template, redirect, url_for, flash, send_file, Response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
import json
import os
from datetime import datetime

# Import app initialization and models
from app import init_app, db, login_manager
from app.models import *
from app.decorators import sales_required
from app.services import OrderService, StockService, AuthService, QuotationService

# Import email service and config
from email_service import get_email_service
from config import config

app = Flask(__name__)

# Load configuration
config_name = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[config_name])

# Initialize app extensions
init_app(app)

with app.app_context():
    db.create_all()
    print("✅ All tables created successfully in PostgreSQL.")

# Authentication routes
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        user = User.query.filter_by(email=data['email']).first()
        if user and check_password_hash(user.password, data['password']):
            # Check if user has sales role
            if user.role != 'sales':
                return jsonify({'success': False, 'message': 'Access denied. Only sales staff can log in to this portal.'})
            
            login_user(user)
            return jsonify({'success': True, 'user': {
                'id': user.id,
                'email': user.email,
                'firstname': user.firstname,
                'lastname': user.lastname,
                'role': user.role
            }})
        return jsonify({'success': False, 'message': 'Invalid credentials'})
    return render_template('login.html')

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.')
    return redirect(url_for('login'))

# Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    # Get summary statistics for walk-in orders only
    
    # Get all walk-in orders created by current user
    walk_in_orders = Order.query.join(OrderType).filter(
        OrderType.name.ilike('%walk%'),  # Match any order type containing 'walk'
        Order.userid == current_user.id
    ).all()
    
    # Calculate total revenue from APPROVED walk-in orders only
    total_revenue = 0
    for order in walk_in_orders:
        if order.approvalstatus:  # Only count approved orders
            for item in order.order_items:
                if item.final_price is not None:
                    total_revenue += item.quantity * float(item.final_price)
                elif item.product.sellingprice is not None:
                    total_revenue += item.quantity * float(item.product.sellingprice)
    
    stats = {
        'total_orders': len(walk_in_orders),
        'pending_orders': len([o for o in walk_in_orders if not o.approvalstatus]),
        'total_revenue': total_revenue,
        'completed_orders': len([o for o in walk_in_orders if o.approvalstatus])
    }
    
    # Get recent walk-in orders
    recent_orders = walk_in_orders[:5]  # Get first 5 orders
    recent_orders_data = []
    for order in recent_orders:
        # Calculate total amount for this order
        total_amount = 0
        for item in order.order_items:
            if item.final_price is not None:
                total_amount += item.quantity * float(item.final_price)
            elif item.product.sellingprice is not None:
                total_amount += item.quantity * float(item.product.sellingprice)
        
        recent_orders_data.append({
            'id': order.id,
            'customer_name': f"{order.user.firstname} {order.user.lastname}",
            'status': 'Approved' if order.approvalstatus else 'Pending',
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
            'total_amount': total_amount
        })
    
    return render_template('dashboard.html', 
                         user=current_user, 
                         stats=stats, 
                         recent_orders=recent_orders_data)

# Order Management Routes
@app.route("/orders")
@login_required
def orders_page():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    per_page = 20

    # Only show walk-in orders for the current user
    query = Order.query.join(OrderType).filter(
        OrderType.name.ilike('%walk%'),
        Order.userid == current_user.id
    )
    
    # Apply status filters - be explicit about which table we're filtering
    if status == 'pending':
        query = query.filter(Order.approvalstatus == False)
    elif status == 'approved':
        query = query.filter(Order.approvalstatus == True)
    
    # Manual pagination for walk-in orders
    total = query.count()
    pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    orders_list = query.order_by(Order.created_at.desc()).offset(start).limit(per_page).all()
    
    class Pagination:
        def __init__(self, items, page, per_page, total, pages):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = pages
            self.has_prev = page > 1
            self.has_next = page < pages
            self.prev_num = page - 1
            self.next_num = page + 1
        def iter_pages(self):
            return range(1, self.pages + 1)
    
    orders = Pagination(orders_list, page, per_page, total, pages)

    orders_data = []
    for order in orders_list:
        order_items = []
        for item in order.order_items:
            # Get product name - use product_name field if available, otherwise fall back to product.name
            if item.product_name:
                product_name = item.product_name
            elif item.productid and item.product:
                product_name = item.product.name
            else:
                product_name = "Manual Item"
            
            # Get product price - use original_price if available, otherwise fall back to product.sellingprice
            if item.original_price is not None:
                product_price = item.original_price
            elif item.productid and item.product and item.product.sellingprice is not None:
                product_price = item.product.sellingprice
            else:
                product_price = 0.0
            
            order_items.append({
                'id': item.id,
                'product_name': product_name,
                'quantity': item.quantity,
                'price': product_price
            })
        orders_data.append({
            'id': order.id,
            'customer_name': f"{order.user.firstname} {order.user.lastname}",
            'order_type': order.ordertype.name,
            'branch': order.branch.name,
            'status': 'Approved' if order.approvalstatus else 'Pending',
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
            'approved_at': order.approved_at.strftime('%Y-%m-%d %H:%M') if order.approved_at else None,
            'items': order_items,
            'created_by_me': order.userid == current_user.id
        })

    # Get filter options
    order_types = OrderType.query.filter(OrderType.name.ilike('%walk%')).all()
    branches = Branch.query.all()

    return render_template('orders.html',
                         user=current_user,
                         orders=orders_data,
                         pagination=orders,
                         order_types=order_types,
                         branches=branches,
                         current_status=status)

@app.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Only allow access to walk-in orders created by current user
    if not order.ordertype.name.lower().startswith('walk') or order.userid != current_user.id:
        flash('Access denied. You can only view your own walk-in orders.', 'danger')
        return redirect(url_for('orders_page'))
    
    order_data = {
        'id': order.id,
        'customer_name': f"{order.user.firstname} {order.user.lastname}",
        'customer_email': order.user.email,
        'order_type': order.ordertype.name,
        'branch': order.branch.name,
        'status': 'Approved' if order.approvalstatus else 'Pending',
        'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
        'approved_at': order.approved_at.strftime('%Y-%m-%d %H:%M') if order.approved_at else None,
        'order_items': []
    }
    
    total_amount = 0
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
        
        # Handle original price
        if item.original_price is not None:
            original_price = float(item.original_price)
        elif item.product.sellingprice is not None:
            original_price = float(item.product.sellingprice)
        else:
            original_price = 0.0
        
        # Handle final price for display
        if item.final_price is not None:
            display_final_price = float(item.final_price)
        elif item.productid and item.product and item.product.sellingprice is not None:
            display_final_price = float(item.product.sellingprice)
        else:
            display_final_price = 0.0
        
        # Get product name - use product_name field if available, otherwise fall back to product.name
        if item.product_name:
            product_name = item.product_name
        elif item.productid and item.product:
            product_name = item.product.name
        else:
            product_name = "Manual Item"
        
        order_data['order_items'].append({
            'id': item.id,
            'product_name': product_name,
            'quantity': item.quantity,
            'original_price': original_price,
            'negotiated_price': float(item.negotiated_price) if item.negotiated_price else None,
            'final_price': display_final_price,
            'total': item_total
        })
    
    order_data['total_amount'] = total_amount
    
    return render_template('order_detail.html', 
                          user=current_user, 
                          order=order_data)

@app.route("/orders/<int:order_id>/invoice")
@login_required
def view_order_invoice(order_id):
    """Generate PDF invoice for a specific order"""
    from app.pdf_utils import create_receipt_pdf, generate_receipt_filename
    from datetime import datetime
    import tempfile
    import os
    
    order = Order.query.get_or_404(order_id)
    
    # Only allow access to walk-in orders created by current user
    if not order.ordertype.name.lower().startswith('walk') or order.userid != current_user.id:
        flash('Access denied. You can only view invoices for your own walk-in orders.', 'danger')
        return redirect(url_for('orders_page'))
    
    # Prepare invoice data
    invoice_data = {
        'invoice_number': f"INV-{order.id:06d}",
        'order_id': order.id,
        'customer_name': f"{order.user.firstname} {order.user.lastname}",
        'customer_email': order.user.email,
        'customer_phone': order.user.phone if hasattr(order.user, 'phone') else 'N/A',
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
        'firstname': current_user.firstname,
        'lastname': current_user.lastname,
        'email': current_user.email
    }
    
    try:
        # Create temporary file for PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf_path = tmp_file.name
        
        # Generate PDF using dedicated invoice function
        from app.pdf_utils import create_invoice_pdf_a4
        
        create_invoice_pdf_a4(invoice_data, user_data, pdf_path)
        
        # Return PDF file
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"invoice_INV-{order.id:06d}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'danger')
        return redirect(url_for('orders_page'))
    
    finally:
        # Clean up temporary file
        if 'pdf_path' in locals() and os.path.exists(pdf_path):
            try:
                os.unlink(pdf_path)
            except:
                pass

@app.route("/orders/<int:order_id>/invoice/view")
@login_required
def view_order_invoice_browser(order_id):
    """View PDF invoice in browser for a specific order"""
    from app.pdf_utils import create_receipt_pdf
    import tempfile
    import os
    
    order = Order.query.get_or_404(order_id)
    
    # Only allow access to walk-in orders created by current user
    if not order.ordertype.name.lower().startswith('walk') or order.userid != current_user.id:
        flash('Access denied. You can only view invoices for your own walk-in orders.', 'danger')
        return redirect(url_for('orders_page'))
    
    # Prepare invoice data
    invoice_data = {
        'invoice_number': f"INV-{order.id:06d}",
        'order_id': order.id,
        'customer_name': f"{order.user.firstname} {order.user.lastname}",
        'customer_email': order.user.email,
        'customer_phone': order.user.phone if hasattr(order.user, 'phone') else 'N/A',
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
        elif item.original_price is not None:
            final_price = float(item.original_price)
        elif item.product and item.product.sellingprice is not None:
            final_price = float(item.product.sellingprice)
        else:
            final_price = 0.0
        
        item_total = item.quantity * final_price
        invoice_data['subtotal'] += item_total
        
        invoice_data['order_items'].append({
            'product_name': item.product_name if item.product_name else (item.product.name if item.product else 'Manual Item'),
            'quantity': item.quantity,
            'unit_price': final_price,
            'total': item_total
        })
    
    # Prepare user data
    user_data = {
        'firstname': current_user.firstname,
        'lastname': current_user.lastname,
        'email': current_user.email
    }
    
    try:
        # Create temporary file for PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf_path = tmp_file.name
        
        # Generate PDF using dedicated invoice function
        from app.pdf_utils import create_invoice_pdf_a4
        
        create_invoice_pdf_a4(invoice_data, user_data, pdf_path)
        
        # Return PDF file for browser viewing
        return send_file(
            pdf_path,
            as_attachment=False,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'danger')
        return redirect(url_for('orders_page'))
    
    finally:
        # Clean up temporary file
        if 'pdf_path' in locals() and os.path.exists(pdf_path):
            try:
                os.unlink(pdf_path)
            except:
                pass

# Order Creation
@app.route("/orders/create", methods=['GET', 'POST'])
@login_required
def create_order():
    if request.method == 'POST':
        try:
            # Handle both JSON and form data
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()
                # Convert items from string to list if it's form data
                if 'items' in data and isinstance(data['items'], str):
                    try:
                        data['items'] = json.loads(data['items'])
                    except json.JSONDecodeError:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return jsonify({'success': False, 'message': 'Invalid items data format'})
                        flash('Invalid items data format', 'danger')
                        return redirect(url_for('create_order'))
            
            # Validate required fields
            if not data.get('order_type_id') or not data.get('branch_id'):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Order type and branch are required'})
                flash('Order type and branch are required', 'danger')
                return redirect(url_for('create_order'))
            
            if not data.get('items') or len(data['items']) == 0:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'At least one item is required'})
                flash('At least one item is required', 'danger')
                return redirect(url_for('create_order'))
            
            success, order_id, total_amount = OrderService.create_order(data, current_user)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'order_id': order_id,
                    'total_amount': total_amount,
                    'message': 'Order created successfully'
                })
            
            flash(f'Order created successfully! Order ID: {order_id}', 'success')
            return redirect(url_for('order_detail', order_id=order_id))
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': str(e)})
            flash(f'Error creating order: {str(e)}', 'danger')
            return redirect(url_for('create_order'))
    
    # GET request - show form
    # Get walk-in order type ID (case-insensitive)
    walk_in_order_type = OrderType.query.filter(OrderType.name.ilike('%walk%')).first()
    if not walk_in_order_type:
        flash('Walk-in order type not found. Please contact administrator.', 'danger')
        return redirect(url_for('orders_page'))
    
    branches = Branch.query.all()
    products = Product.query.filter_by(display=True).all()
    subcategories = SubCategory.query.all()
    
    return render_template('create_order.html',
                         user=current_user,
                         walk_in_order_type_id=walk_in_order_type.id,
                         branches=branches,
                         products=products,
                         subcategories=subcategories)

@app.route("/orders/<int:order_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_order(order_id):
    """Edit an order that is not yet approved"""
    order = Order.query.get_or_404(order_id)
    
    # Only allow editing of pending walk-in orders created by current user
    if not order.ordertype.name.lower().startswith('walk') or order.userid != current_user.id:
        flash('Access denied. You can only edit your own pending walk-in orders.', 'danger')
        return redirect(url_for('orders_page'))
    
    if order.approvalstatus:
        flash('Cannot edit approved orders', 'warning')
        return redirect(url_for('order_detail', order_id=order_id))
    
    if request.method == 'POST':
        try:
            # Handle both JSON and form data
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()
                # Convert items from string to list if it's form data
                if 'items' in data and isinstance(data['items'], str):
                    try:
                        data['items'] = json.loads(data['items'])
                    except json.JSONDecodeError:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return jsonify({'success': False, 'message': 'Invalid items data format'})
                        flash('Invalid items data format', 'danger')
                        return redirect(url_for('edit_order', order_id=order_id))
            
            # Validate required fields
            if not data.get('branch_id'):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Branch is required'})
                flash('Branch is required', 'danger')
                return redirect(url_for('edit_order', order_id=order_id))
            
            if not data.get('items') or len(data['items']) == 0:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'At least one item is required'})
                flash('At least one item is required', 'danger')
                return redirect(url_for('edit_order', order_id=order_id))
            
            success, message = OrderService.edit_order(order_id, data, current_user)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': success, 'message': message})
            
            flash(message, 'success' if success else 'danger')
            return redirect(url_for('order_detail', order_id=order_id))
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': str(e)})
            flash(f'Error editing order: {str(e)}', 'danger')
            return redirect(url_for('edit_order', order_id=order_id))
    
    # GET request - show edit form
    # Get current order data
    order_data = {
        'id': order.id,
        'branch_id': order.branchid,
        'order_items': []
    }
    
    for item in order.order_items:
        # Get product name - use product_name field if available, otherwise fall back to product.name
        if item.product_name:
            product_name = item.product_name
        elif item.productid and item.product:
            product_name = item.product.name
        else:
            product_name = "Manual Item"
        
        # Get product price - use original_price if available, otherwise fall back to product.sellingprice
        if item.original_price is not None:
            product_price = item.original_price
        elif item.productid and item.product and item.product.sellingprice is not None:
            product_price = item.product.sellingprice
        else:
            product_price = 0.0
        
        order_data['order_items'].append({
            'id': item.id,
            'product_id': item.productid,
            'product_name': product_name,
            'quantity': item.quantity,
            'price': product_price,
            'buying_price': float(item.buying_price) if item.buying_price else None,
            'negotiated_price': float(item.negotiated_price) if item.negotiated_price else None,
            'negotiation_notes': item.negotiation_notes
        })
    
    branches = Branch.query.all()
    products = Product.query.filter_by(display=True).all()
    subcategories = SubCategory.query.all()
    
    return render_template('edit_order.html',
                         user=current_user,
                         order=order_data,
                         branches=branches,
                         products=products,
                         subcategories=subcategories)

@app.route("/orders/<int:order_id>/delete", methods=['POST'])
@login_required
def delete_order(order_id):
    """Delete a pending order that is not yet approved"""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Only allow deletion of pending walk-in orders created by current user
        if not order.ordertype.name.lower().startswith('walk') or order.userid != current_user.id:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Access denied. You can only delete your own pending walk-in orders.'})
            flash('Access denied. You can only delete your own pending walk-in orders.', 'danger')
            return redirect(url_for('orders_page'))
        
        if order.approvalstatus:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Cannot delete approved orders'})
            flash('Cannot delete approved orders', 'warning')
            return redirect(url_for('order_detail', order_id=order_id))
        
        # Delete order logic (implemented directly to avoid service issues)
        try:
            # Delete related invoices first
            from app.models import Invoice
            invoices = Invoice.query.filter_by(orderid=order.id).all()
            for invoice in invoices:
                db.session.delete(invoice)
            
            # Delete all order items first
            for item in order.order_items:
                db.session.delete(item)
            
            # Delete the order
            db.session.delete(order)
            db.session.commit()
            
            message = f'Order #{order_id} deleted successfully'
            success = True
            
        except Exception as e:
            db.session.rollback()
            message = f'Error deleting order: {str(e)}'
            success = False
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': success, 'message': message})
        
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('orders_page'))
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error deleting order: {str(e)}', 'danger')
        return redirect(url_for('orders_page'))

# Product Management Routes
@app.route("/products")
@login_required
def products_page():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    branch = request.args.get('branch', '')
    search = request.args.get('search', '')
    
    query = Product.query
    
    if category:
        query = query.join(SubCategory).join(Category).filter(Category.name == category)
    if branch:
        query = query.join(Branch).filter(Branch.name == branch)
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    
    products = query.paginate(page=page, per_page=20, error_out=False)
    
    products_data = []
    for product in products.items:
        # Get category name through subcategory relationship
        category_name = product.sub_category.category.name if product.sub_category and product.sub_category.category else 'Uncategorized'
        
        products_data.append({
            'id': product.id,
            'name': product.name,
            'category': category_name,
            'branch': product.branch.name,
            'buying_price': product.buyingprice,
            'selling_price': product.sellingprice,
            'stock': product.stock,
            'product_code': product.productcode,
            'display': product.display,
            'image_url': product.image_url
        })
    
    # Get filter options
    subcategories = SubCategory.query.all()
    branches = Branch.query.all()
    
    return render_template('products.html', 
                         user=current_user, 
                         products=products_data,
                         pagination=products,
                         subcategories=subcategories,
                         branches=branches,
                         current_category=category,
                         current_branch=branch,
                         current_search=search)

@app.route("/products/export")
@login_required
def export_products():
    """Export products to CSV"""
    import csv
    from io import StringIO
    
    # Get filter parameters
    category = request.args.get('category', '')
    branch = request.args.get('branch', '')
    search = request.args.get('search', '')
    
    # Build query with same filters as products page
    query = Product.query
    
    if category:
        query = query.join(SubCategory).join(Category).filter(Category.name == category)
    if branch:
        query = query.join(Branch).filter(Branch.name == branch)
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    
    # Get all products (no pagination for export)
    products = query.all()
    
    # Create CSV data
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['ID', 'Name', 'Product Code', 'Category', 'Branch', 'Buying Price', 'Selling Price', 'Stock', 'Status'])
    
    # Write data rows
    for product in products:
        category_name = product.sub_category.category.name if product.sub_category and product.sub_category.category else 'Uncategorized'
        status = 'Active' if product.display else 'Hidden'
        
        writer.writerow([
            product.id,
            product.name,
            product.productcode or '',
            category_name,
            product.branch.name,
            product.buyingprice or 0,
            product.sellingprice or 0,
            product.stock or 0,
            status
        ])
    
    # Prepare response
    output.seek(0)
    
    # Generate filename with timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"products_export_{timestamp}.csv"
    
    # Create temporary file
    import tempfile
    import os
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='utf-8') as tmp_file:
            tmp_file.write(output.getvalue())
            tmp_file_path = tmp_file.name
        
        return send_file(
            tmp_file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv'
        )
    finally:
        # Clean up temporary file after sending
        if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except:
                pass

@app.route("/products/<int:product_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        try:
            product.name = request.form['name']
            product.subcategory_id = int(request.form['category_id'])
            product.branchid = int(request.form['branch_id'])
            product.buyingprice = int(request.form['buying_price'])
            product.sellingprice = int(request.form['selling_price'])
            product.stock = int(request.form['stock'])
            product.productcode = request.form['product_code']
            product.display = 'display' in request.form
            product.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('products_page'))
            
        except Exception as e:
            flash(f'Error updating product: {str(e)}', 'danger')
    
    subcategories = SubCategory.query.all()
    branches = Branch.query.all()
    
    return render_template('edit_product.html',
                         user=current_user,
                         product=product,
                         subcategories=subcategories,
                         branches=branches)

# Stock Management Routes
@app.route("/stock")
@login_required
def stock_page():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Product.query
    
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    
    products = query.paginate(page=page, per_page=20, error_out=False)
    
    return render_template('stock.html', 
                         user=current_user, 
                         products=products.items,
                         pagination=products,
                         current_search=search)

@app.route("/stock/add", methods=['POST'])
@login_required
def add_stock():
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        success, new_stock = StockService.add_stock(
            int(data['product_id']),
            int(data['quantity']),
            current_user,
            data.get('notes')
        )
        
        message = f'Added {data["quantity"]} units to stock. New stock: {new_stock}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': message,
                'new_stock': new_stock
            })
        
        flash(message, 'success')
        return redirect(url_for('stock_page'))
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error adding stock: {str(e)}', 'danger')
        return redirect(url_for('stock_page'))

@app.route("/stock/remove", methods=['POST'])
@login_required
def remove_stock():
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        success, new_stock = StockService.remove_stock(
            int(data['product_id']),
            int(data['quantity']),
            current_user,
            data.get('notes')
        )
        
        message = f'Removed {data["quantity"]} units from stock. New stock: {new_stock}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': message,
                'new_stock': new_stock
            })
        
        flash(message, 'success')
        return redirect(url_for('stock_page'))
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error removing stock: {str(e)}', 'danger')
        return redirect(url_for('stock_page'))

# API Routes for AJAX
@app.route("/api/products")
@login_required
def api_products():
    try:
        category_id = request.args.get('category_id', type=int)
        branch_id = request.args.get('branch_id', type=int)
        search = request.args.get('search', '').strip()
    
        # Start with base query
        query = Product.query.filter_by(display=True)
    
        # Apply filters
        if category_id:
            query = query.filter_by(subcategory_id=category_id)
        if branch_id:
            query = query.filter_by(branchid=branch_id)
    
        # Apply search if provided
        if search:
            from sqlalchemy import or_
            # More flexible search across multiple columns
            search_filter = or_(
                Product.name.ilike(f'%{search}%'),
                Product.productcode.ilike(f'%{search}%'),
                Product.buyingprice.cast(db.String).ilike(f'%{search}%'),
                Product.sellingprice.cast(db.String).ilike(f'%{search}%'),
                Product.stock.cast(db.String).ilike(f'%{search}%')
            )
            query = query.filter(search_filter)
        
        # Execute query
        products = query.all()
    
        # Convert to JSON-serializable format
        result = []
        for p in products:
            result.append({
                'id': p.id,
                'name': p.name or '',
                'selling_price': float(p.sellingprice) if p.sellingprice else 0.0,
                'buyingprice': float(p.buyingprice) if p.buyingprice else 0.0,
                'stock': int(p.stock) if p.stock else 0,
                'product_code': p.productcode or ''
            })
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error in api_products: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Utility Routes
@app.route("/categories")
@login_required
def get_categories():
    categories = Category.query.all()
    return jsonify([{
        'id': cat.id,
        'name': cat.name,
        'description': cat.description
    } for cat in categories])

@app.route("/branches")
@login_required
def get_branches():
    branches = Branch.query.all()
    return jsonify([{
        'id': branch.id,
        'name': branch.name,
        'location': branch.location
    } for branch in branches])

@app.route("/order-types")
@login_required
def get_order_types():
    order_types = OrderType.query.all()
    return jsonify([{
        'id': ot.id,
        'name': ot.name
    } for ot in order_types])

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Quotation Management Routes
@app.route("/quotations")
@login_required
def quotations_page():
    """List all quotations"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    search = request.args.get('search', '')
    
    query = Quotation.query
    
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(Quotation.customer_name.ilike(f'%{search}%'))
    
    # For non-admin users, show only their quotations
    if current_user.role != 'admin':
        query = query.filter_by(created_by=current_user.id)
    
    quotations = query.order_by(Quotation.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('quotations.html',
                         user=current_user,
                         quotations=quotations.items,
                         pagination=quotations,
                         current_status=status,
                         current_search=search)

@app.route("/quotations/create", methods=['GET', 'POST'])
@login_required
def create_quotation():
    """Create a new quotation"""
    if request.method == 'POST':
        try:
            # Handle both JSON and form data
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()
                # Convert items from string to list if it's form data
                if 'items' in data and isinstance(data['items'], str):
                    try:
                        data['items'] = json.loads(data['items'])
                    except json.JSONDecodeError:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return jsonify({'success': False, 'message': 'Invalid items data format'})
                        flash('Invalid items data format', 'danger')
                        return redirect(url_for('create_quotation'))
            
            # Validate required fields
            if not data.get('customer_name') or not data.get('branch_id'):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Customer name and branch are required'})
                flash('Customer name and branch are required', 'danger')
                return redirect(url_for('create_quotation'))
            
            if not data.get('items') or len(data['items']) == 0:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'At least one item is required'})
                flash('At least one item is required', 'danger')
                return redirect(url_for('create_quotation'))
            
            success, quotation_id, total_amount = QuotationService.create_quotation(data, current_user)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'quotation_id': quotation_id,
                    'total_amount': total_amount,
                    'message': 'Quotation created successfully'
                })
            
            flash(f'Quotation created successfully! Quotation ID: {quotation_id}', 'success')
            return redirect(url_for('quotation_detail', quotation_id=quotation_id))
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': str(e)})
            flash(f'Error creating quotation: {str(e)}', 'danger')
            return redirect(url_for('create_quotation'))
    
    # GET request - show form
    branches = Branch.query.all()
    products = Product.query.filter_by(display=True).all()
    subcategories = SubCategory.query.all()
    
    return render_template('create_quotation.html',
                         user=current_user,
                         branches=branches,
                         products=products,
                         subcategories=subcategories)

@app.route("/quotations/<int:quotation_id>")
@login_required
def quotation_detail(quotation_id):
    """View quotation details"""
    quotation = Quotation.query.get_or_404(quotation_id)
    
    # Check if user has access to this quotation
    if current_user.role != 'admin' and quotation.created_by != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('quotations_page'))
    
    return render_template('quotation_detail.html',
                         user=current_user,
                         quotation=quotation)

@app.route("/quotations/<int:quotation_id>/pdf")
@login_required
def view_quotation_pdf(quotation_id):
    """View quotation PDF in browser"""
    quotation = Quotation.query.get_or_404(quotation_id)
    
    # Check if user has access to this quotation
    if current_user.role != 'admin' and quotation.created_by != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('quotations_page'))
    
    # Generate PDF for quotation
    from app.pdf_utils import create_quotation_pdf_a4
    import tempfile
    import os
    
    try:
        # Create temporary file for PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf_path = tmp_file.name
        
        # Generate PDF
        create_quotation_pdf_a4(quotation, current_user, pdf_path)
        
        # Return PDF file for browser viewing
        return send_file(
            pdf_path,
            as_attachment=False,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'danger')
        return redirect(url_for('quotation_detail', quotation_id=quotation_id))
    
    finally:
        # Clean up temporary file
        if 'pdf_path' in locals() and os.path.exists(pdf_path):
            try:
                os.unlink(pdf_path)
            except:
                pass

@app.route("/quotations/<int:quotation_id>/pdf/download")
@login_required
def download_quotation_pdf(quotation_id):
    """Download quotation PDF"""
    quotation = Quotation.query.get_or_404(quotation_id)
    
    # Check if user has access to this quotation
    if current_user.role != 'admin' and quotation.created_by != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('quotations_page'))
    
    # Generate PDF for quotation
    from app.pdf_utils import create_quotation_pdf_a4
    import tempfile
    import os
    
    try:
        # Create temporary file for PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf_path = tmp_file.name
        
        # Generate PDF
        create_quotation_pdf_a4(quotation, current_user, pdf_path)
        
        # Return PDF file for download
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"quotation_{quotation.quotation_number}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'danger')
        return redirect(url_for('quotation_detail', quotation_id=quotation_id))
    
    finally:
        # Clean up temporary file
        if 'pdf_path' in locals() and os.path.exists(pdf_path):
            try:
                os.unlink(pdf_path)
            except:
                pass

@app.route("/quotations/<int:quotation_id>/status", methods=['POST'])
@login_required
def update_quotation_status(quotation_id):
    """Update quotation status"""
    quotation = Quotation.query.get_or_404(quotation_id)
    
    # Check if user has access to this quotation
    if current_user.role != 'admin' and quotation.created_by != current_user.id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['pending', 'accepted', 'rejected', 'expired']:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400
        
        # Update status
        quotation.status = new_status
        quotation.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Status updated to {new_status.title()}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route("/quotations/<int:quotation_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_quotation(quotation_id):
    """Edit quotation"""
    quotation = Quotation.query.get_or_404(quotation_id)
    
    # Check if user has access to this quotation
    if current_user.role != 'admin' and quotation.created_by != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('quotations_page'))
    
    if request.method == 'POST':
        try:
            # Update quotation details
            quotation.customer_name = request.form.get('customer_name')
            quotation.customer_email = request.form.get('customer_email')
            quotation.customer_phone = request.form.get('customer_phone')
            quotation.notes = request.form.get('notes')
            quotation.valid_until = datetime.strptime(request.form.get('valid_until'), '%Y-%m-%d') if request.form.get('valid_until') else None
            quotation.updated_at = datetime.utcnow()
            
            # Update items
            item_ids = request.form.getlist('item_id[]')
            item_names = request.form.getlist('item_name[]')
            quantities = request.form.getlist('quantity[]')
            unit_prices = request.form.getlist('unit_price[]')
            notes = request.form.getlist('notes[]')
            
            # Debug logging
            print(f"DEBUG: item_ids: {item_ids}")
            print(f"DEBUG: item_names: {item_names}")
            print(f"DEBUG: quantities: {quantities}")
            print(f"DEBUG: unit_prices: {unit_prices}")
            print(f"DEBUG: notes: {notes}")
            
            # Check if arrays are properly aligned
            if len(item_ids) != len(quantities) or len(item_names) != len(quantities):
                print(f"WARNING: Array length mismatch detected!")
                print(f"All arrays should have the same length as quantities: {len(quantities)}")
                print(f"item_ids length: {len(item_ids)}")
                print(f"item_names length: {len(item_names)}")
                print(f"notes length: {len(notes)}")
            
            # Also check the raw form data to see what's actually being sent
            print(f"DEBUG: Raw form data keys: {list(request.form.keys())}")
            print(f"DEBUG: All item_id[] values: {request.form.getlist('item_id[]')}")
            print(f"DEBUG: All item_name[] values: {request.form.getlist('item_name[]')}")
            print(f"DEBUG: All quantity[] values: {request.form.getlist('quantity[]')}")
            print(f"DEBUG: All unit_price[] values: {request.form.getlist('unit_price[]')}")
            print(f"DEBUG: All notes[] values: {request.form.getlist('notes[]')}")
            
            # Clear existing items
            for item in quotation.items:
                db.session.delete(item)
            
            # Add updated items
            subtotal = 0
            
            # Create a more robust approach by processing each item individually
            # and finding the corresponding data from the form arrays
            for i in range(len(quantities)):
                if quantities[i] and unit_prices[i]:
                    quantity = int(quantities[i])
                    unit_price = float(unit_prices[i])
                    total_price = quantity * unit_price
                    subtotal += total_price
                    
                    # Safely get values with bounds checking
                    item_id = item_ids[i] if i < len(item_ids) else ''
                    item_name = item_names[i] if i < len(item_names) else ''
                    note = notes[i] if i < len(notes) else ''
                    
                    # Debug logging for each item
                    print(f"DEBUG Item {i}: item_id='{item_id}', item_name='{item_name}', quantity='{quantity}', unit_price='{unit_price}'")
                    
                    # Check if it's a regular product or manual item
                    if item_id and item_id.strip() and item_id != '':  # Regular product
                        print(f"DEBUG: Creating REGULAR PRODUCT with product_id={item_id}")
                        item = QuotationItem(
                            quotation_id=quotation.id,
                            product_id=int(item_id),
                            product_name=None,  # Will get name from product relationship
                            quantity=quantity,
                            unit_price=unit_price,
                            total_price=total_price,
                            notes=note if note else None
                        )
                    else:  # Manual item
                        print(f"DEBUG: Processing MANUAL ITEM at index {i}")
                        print(f"DEBUG: item_name from form: '{item_name}'")
                        print(f"DEBUG: item_name type: {type(item_name)}")
                        print(f"DEBUG: item_name length: {len(item_name) if item_name else 'None'}")
                        
                        # Use the item_name if available, otherwise fallback to 'Manual Item'
                        manual_item_name = item_name if item_name and item_name.strip() else 'Manual Item'
                        print(f"DEBUG: Creating MANUAL ITEM with product_name='{manual_item_name}' (original item_name='{item_name}')")
                        
                        # Additional check: if item_name is empty or just whitespace, try to find it from the form
                        if not manual_item_name or manual_item_name.strip() == '':
                            print(f"WARNING: item_name is empty for manual item at index {i}")
                            print(f"Available item_names: {item_names}")
                            # Try to find a non-empty item_name in the array
                            for j, name in enumerate(item_names):
                                if name and name.strip() and name.strip() != '':
                                    print(f"Found non-empty item_name at index {j}: '{name}'")
                                    manual_item_name = name.strip()
                                    break
                        
                        item = QuotationItem(
                            quotation_id=quotation.id,
                            product_id=None,  # No product ID for manual items
                            product_name=manual_item_name,
                            quantity=quantity,
                            unit_price=unit_price,
                            total_price=total_price,
                            notes=note if note else None
                        )
                    
                    db.session.add(item)
            
            quotation.subtotal = subtotal
            quotation.total_amount = subtotal
            
            db.session.commit()
            flash('Quotation updated successfully!', 'success')
            return redirect(url_for('quotation_detail', quotation_id=quotation.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating quotation: {str(e)}', 'danger')
    
    # GET request - show edit form
    branches = Branch.query.all()
    products = Product.query.filter_by(display=True).all()
    subcategories = SubCategory.query.all()
    
    return render_template('edit_quotation.html',
                         user=current_user,
                         quotation=quotation,
                         branches=branches,
                         products=products,
                         subcategories=subcategories)

@app.route("/quotations/<int:quotation_id>/delete", methods=['POST'])
@login_required
def delete_quotation(quotation_id):
    """Delete quotation"""
    quotation = Quotation.query.get_or_404(quotation_id)
    
    # Check if user has access to this quotation
    if current_user.role != 'admin' and quotation.created_by != current_user.id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        # Delete all quotation items first
        for item in quotation.items:
            db.session.delete(item)
        
        # Delete the quotation
        db.session.delete(quotation)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Quotation deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route("/orders/<int:order_id>/negotiate", methods=['GET', 'POST'])
@login_required
def negotiate_order_prices(order_id):
    """Show price negotiation page for an order"""
    order = Order.query.get_or_404(order_id)
    
    # Only allow negotiation for pending walk-in orders created by current user
    if not order.ordertype.name.lower().startswith('walk') or order.userid != current_user.id:
        flash('Access denied. You can only negotiate prices for your own pending walk-in orders.', 'danger')
        return redirect(url_for('orders_page'))
    
    if order.approvalstatus:
        flash('Cannot negotiate prices for approved orders', 'warning')
        return redirect(url_for('order_detail', order_id=order_id))
    
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form.to_dict()
            negotiations = data.get('negotiations', [])
            
            total_updated = 0
            total_processed = 0
            for negotiation in negotiations:
                order_item_id = negotiation.get('order_item_id')
                new_price = negotiation.get('new_price')
                notes = negotiation.get('notes', '')
                
                if order_item_id and new_price:
                    success, message = OrderService.negotiate_price(
                        int(order_item_id), 
                        float(new_price), 
                        notes, 
                        current_user
                    )
                    if success:
                        # Check if the message indicates no changes were made
                        if 'No changes made' in message:
                            total_processed += 1
                        else:
                            total_updated += 1
                            total_processed += 1
                    else:
                        total_processed += 1
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if total_updated == 0 and total_processed > 0:
                    return jsonify({
                        'success': True, 
                        'message': 'No changes were made to prices or notes'
                    })
                else:
                    return jsonify({
                        'success': True, 
                        'message': f'{total_updated} items updated successfully'
                    })
            
            flash(f'{total_updated} items updated successfully', 'success')
            return redirect(url_for('order_detail', order_id=order_id))
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': str(e)})
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('negotiate_order_prices', order_id=order_id))
    
    # GET request - show negotiation form
    order_items_data = []
    for item in order.order_items:
        # Handle None values for price fields
        if item.original_price is not None:
            original_price = float(item.original_price)
        elif item.productid and item.product and item.product.sellingprice is not None:
            original_price = float(item.product.sellingprice)
        else:
            original_price = 0.0
        
        negotiated_price = float(item.negotiated_price) if item.negotiated_price is not None else None
        
        if item.final_price is not None:
            final_price = float(item.final_price)
        else:
            final_price = original_price
        
        # Get product name - use product_name field if available, otherwise fall back to product.name
        if item.product_name:
            product_name = item.product_name
        elif item.productid and item.product:
            product_name = item.product.name
        else:
            product_name = "Manual Item"
        
        order_items_data.append({
            'id': item.id,
            'product_name': product_name,
            'quantity': item.quantity,
            'original_price': original_price,
            'negotiated_price': negotiated_price,
            'final_price': final_price,
            'negotiation_notes': item.negotiation_notes,
            'total': final_price * item.quantity
        })
    
    return render_template('negotiate_prices.html',
                         user=current_user,
                         order=order,
                         order_items=order_items_data)

if __name__ == '__main__':
    app.run(debug=False)
