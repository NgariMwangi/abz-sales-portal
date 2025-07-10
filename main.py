from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os

# Import app initialization and models
from app import init_app, db, login_manager
from app.models import *
from app.decorators import sales_required
from app.services import OrderService, PaymentService, StockService, AuthService
from app.utils import create_invoice_for_order, create_receipt_for_payment

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

# Forgot Password Routes
@app.route("/forgot-password", methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form.to_dict()
        email = data.get('email')
        
        if not email:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Email is required'})
            flash('Email is required', 'danger')
            return redirect(url_for('forgot_password'))
        
        try:
            success, user, token = AuthService.send_password_reset(email)
            
            if success:
                reset_url = url_for('reset_password', token=token, _external=True)
                email_service = get_email_service()
                
                if email_service:
                    email_result = email_service.send_password_reset_email(
                        to_email=email,
                        reset_url=reset_url,
                        user_name=f"{user.firstname} {user.lastname}"
                    )
                    
                    if email_result['success']:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return jsonify({
                                'success': True, 
                                'message': f'Password reset link sent to {email}'
                            })
                        
                        flash(f'Password reset link sent to {email}', 'success')
                        return redirect(url_for('login'))
                    else:
                        # Email failed, but still show the link for testing
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return jsonify({
                                'success': True, 
                                'message': f'Password reset link sent to {email}. For testing, use this link: {reset_url}'
                            })
                        
                        flash(f'Password reset link sent to {email}. For testing, use this link: {reset_url}', 'success')
                        return redirect(url_for('login'))
                else:
                    # Email service not available, show link for testing
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({
                            'success': True, 
                            'message': f'Password reset link sent to {email}. For testing, use this link: {reset_url}'
                        })
                    
                    flash(f'Password reset link sent to {email}. For testing, use this link: {reset_url}', 'success')
                    return redirect(url_for('login'))
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': user})
                flash(user, 'danger')
                return redirect(url_for('forgot_password'))
                
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': f'Error: {str(e)}'})
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('forgot_password'))
    
    return render_template('forgot_password.html')

@app.route("/reset-password/<token>", methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form.to_dict()
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        if not new_password or not confirm_password:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Both password fields are required'})
            flash('Both password fields are required', 'danger')
            return redirect(url_for('reset_password', token=token))
        
        if new_password != confirm_password:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Passwords do not match'})
            flash('Passwords do not match', 'danger')
            return redirect(url_for('reset_password', token=token))
        
        if len(new_password) < 6:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Password must be at least 6 characters long'})
            flash('Password must be at least 6 characters long', 'danger')
            return redirect(url_for('reset_password', token=token))
        
        try:
            success, message = AuthService.reset_password(token, new_password)
            
            if success:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': True, 'message': f'{message}. A confirmation email has been sent to your email address.'})
                
                flash(f'{message}. A confirmation email has been sent to your email address.', 'success')
                return redirect(url_for('login'))
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': message})
                flash(message, 'danger')
                return redirect(url_for('reset_password', token=token))
                
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': f'Error resetting password: {str(e)}'})
            flash(f'Error resetting password: {str(e)}', 'danger')
            return redirect(url_for('reset_password', token=token))
    
    return render_template('reset_password.html', token=token)

# Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    # Get summary statistics
    
    # Calculate revenue from walk-in orders created by current user
    # Get all walk-in orders created by current user
    walk_in_orders = Order.query.join(OrderType).filter(
        OrderType.name.ilike('%walk%'),  # Match any order type containing 'walk'
        Order.userid == current_user.id
    ).all()
    
    # Get all completed payments for these orders
    walk_in_order_ids = [order.id for order in walk_in_orders]
    total_revenue = 0
    if walk_in_order_ids:
        # Use the raw decimal sum without converting to float to avoid rounding issues
        revenue_sum = Payment.query.filter(
            Payment.orderid.in_(walk_in_order_ids),
            Payment.payment_status == 'completed'
        ).with_entities(db.func.sum(Payment.amount)).scalar()
        
        # Convert to float only for display, but keep the precision
        total_revenue = float(revenue_sum) if revenue_sum is not None else 0.0
    
    stats = {
        'total_orders': Order.query.count(),
        'pending_orders': Order.query.filter_by(approvalstatus=False).count(),
        'total_revenue': total_revenue,
        'pending_payments': Payment.query.filter_by(payment_status='pending').count()
    }
    
    # Get recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    recent_orders_data = []
    for order in recent_orders:
        recent_orders_data.append({
            'id': order.id,
            'customer_name': f"{order.user.firstname} {order.user.lastname}",
            'status': 'Approved' if order.approvalstatus else 'Pending',
            'payment_status': order.payment_status,
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    # Get recent payments
    recent_payments = Payment.query.order_by(Payment.created_at.desc()).limit(5).all()
    recent_payments_data = []
    for payment in recent_payments:
        recent_payments_data.append({
            'id': payment.id,
            'order_id': payment.orderid,
            'customer_name': f"{payment.user.firstname} {payment.user.lastname}",
            'amount': float(payment.amount),
            'payment_method': payment.payment_method,
            'status': payment.payment_status,
            'created_at': payment.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    return render_template('dashboard.html', 
                         user=current_user, 
                         stats=stats, 
                         recent_orders=recent_orders_data,
                         recent_payments=recent_payments_data)

# Order Management Routes
@app.route("/orders")
@login_required
def orders_page():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    order_type = request.args.get('order_type', '')
    per_page = 20

    # Debug: Print the order_type value
    print(f"DEBUG: order_type = '{order_type}'")

    # Filtering logic
    if order_type and order_type.strip():  # Check if order_type is not empty or just whitespace
        # Apply status filter first, then join with OrderType
        query = Order.query
        if status == 'pending':
            query = query.filter_by(approvalstatus=False)
        elif status == 'approved':
            query = query.filter_by(approvalstatus=True)
        
        # Then join with OrderType and filter by order type
        query = query.join(OrderType).filter(OrderType.name == order_type)
        
        # For walk-in orders, only show orders created by current user
        if order_type.lower() == 'walk-in':
            query = query.filter(Order.userid == current_user.id)
        
        orders = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        orders_list = orders.items
        total = orders.total
        pages = orders.pages
    else:
        # No filter: show all online orders + current user's walk-in orders
        # Create separate queries for online and walk-in orders
        online_query = Order.query
        walk_in_query = Order.query
        
        # Apply status filters to both queries
        if status == 'pending':
            online_query = online_query.filter_by(approvalstatus=False)
            walk_in_query = walk_in_query.filter_by(approvalstatus=False)
        elif status == 'approved':
            online_query = online_query.filter_by(approvalstatus=True)
            walk_in_query = walk_in_query.filter_by(approvalstatus=True)
        
        # Get online orders
        online_orders = online_query.join(OrderType).filter(OrderType.name == 'online').all()
        
        # Get walk-in orders for current user
        walk_in_orders = walk_in_query.join(OrderType).filter(
            OrderType.name == 'walk-in', 
            Order.userid == current_user.id
        ).all()
        
        # Debug: Print counts
        print(f"DEBUG: online_orders count = {len(online_orders)}")
        print(f"DEBUG: walk_in_orders count = {len(walk_in_orders)}")
        
        combined_orders = online_orders + walk_in_orders
        # Remove duplicates (in case of any overlap)
        combined_orders = list({o.id: o for o in combined_orders}.values())
        # Sort by created_at desc
        combined_orders.sort(key=lambda o: o.created_at, reverse=True)
        # Manual pagination
        total = len(combined_orders)
        pages = (total + per_page - 1) // per_page
        start = (page - 1) * per_page
        end = start + per_page
        orders_list = combined_orders[start:end]
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
            order_items.append({
                'id': item.id,
                'product_name': item.product.name,
                'quantity': item.quantity,
                'price': item.product.sellingprice
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
    order_types = OrderType.query.all()
    branches = Branch.query.all()

    return render_template('orders.html',
                         user=current_user,
                         orders=orders_data,
                         pagination=orders,
                         order_types=order_types,
                         branches=branches,
                         current_status=status,
                         current_order_type=order_type)

@app.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    order_data = {
        'id': order.id,
        'customer_name': f"{order.user.firstname} {order.user.lastname}",
        'customer_email': order.user.email,
        'order_type': order.ordertype.name,
        'branch': order.branch.name,
        'status': 'Approved' if order.approvalstatus else 'Pending',
        'payment_status': order.payment_status,
        'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
        'approved_at': order.approved_at.strftime('%Y-%m-%d %H:%M') if order.approved_at else None,
        'order_items': []
    }
    
    total_amount = 0
    for item in order.order_items:
        # Use final_price for calculations (includes negotiated prices)
        final_price = float(item.final_price) if item.final_price is not None else float(item.product.sellingprice)
        item_total = item.quantity * final_price
        total_amount += item_total
        
        # For online orders, get the fulfillment branch information from stock transactions
        fulfillment_branch = None
        if order.ordertype.name.lower() == 'online' and order.approvalstatus:
            # Find the stock transaction for this item to see which branch was used
            stock_transaction = StockTransaction.query.filter(
                StockTransaction.notes.like(f'Order #{order.id} approved%'),
                StockTransaction.quantity == item.quantity
            ).first()
            
            if stock_transaction:
                product_used = Product.query.get(stock_transaction.productid)
                if product_used:
                    fulfillment_branch = product_used.branch.name
        
        order_data['order_items'].append({
            'id': item.id,
            'product_name': item.product.name,
            'quantity': item.quantity,
            'original_price': float(item.original_price) if item.original_price is not None else float(item.product.sellingprice),
            'negotiated_price': float(item.negotiated_price) if item.negotiated_price else None,
            'final_price': float(item.final_price) if item.final_price is not None else float(item.product.sellingprice),
            'total': item_total,
            'fulfillment_branch': fulfillment_branch
        })
    
    order_data['total_amount'] = total_amount
    
    return render_template('order_detail.html', 
                         user=current_user, 
                         order=order_data)

@app.route("/orders/<int:order_id>/select-branch", methods=['GET'])
@login_required
def select_fulfillment_branch(order_id):
    """Show branch selection page for online order approval"""
    order = Order.query.get_or_404(order_id)
    
    # Only allow branch selection for online orders that are not yet approved
    if order.ordertype.name.lower() != 'online' or order.approvalstatus:
        flash('Branch selection is only available for pending online orders', 'warning')
        return redirect(url_for('order_detail', order_id=order_id))
    
    # Get all branches
    branches = Branch.query.all()
    
    # For each order item, get stock information from all branches
    order_items_with_branches = []
    
    for item in order.order_items:
        item_branches = []
        
        for branch in branches:
            # Check if this product exists in this branch
            product_in_branch = Product.query.filter_by(
                productcode=item.product.productcode,
                branchid=branch.id
            ).first()
            
            if product_in_branch:
                available_stock = product_in_branch.stock
                is_sufficient = available_stock >= item.quantity
            else:
                available_stock = 0
                is_sufficient = False
            
            item_branches.append({
                'branch': branch,
                'available_stock': available_stock,
                'is_sufficient': is_sufficient,
                'product_in_branch': product_in_branch
            })
        
        order_items_with_branches.append({
            'item': item,
            'branches': item_branches
        })
    
    return render_template('select_branch.html',
                         user=current_user,
                         order=order,
                         order_items_with_branches=order_items_with_branches)

@app.route("/orders/<int:order_id>/approve", methods=['POST'])
@login_required
def approve_order(order_id):
    try:
        # Get the branch selections from the request
        data = request.get_json() if request.is_json else request.form.to_dict()
        item_branch_selections = data.get('item_branch_selections', {})
        
        success, message = OrderService.approve_order(order_id, current_user, item_branch_selections)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': success, 'message': message})
        
        flash(message, 'success' if success else 'info')
        return redirect(url_for('orders_page'))
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('orders_page'))

@app.route("/orders/<int:order_id>/reject", methods=['POST'])
@login_required
def reject_order(order_id):
    try:
        success, message = OrderService.reject_order(order_id)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': success, 'message': message})
        
        flash(message, 'success')
        return redirect(url_for('orders_page'))
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('orders_page'))

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
    # Get walk-in order type ID
    walk_in_order_type = OrderType.query.filter_by(name='Walk-in').first()
    if not walk_in_order_type:
        flash('Walk-in order type not found. Please contact administrator.', 'danger')
        return redirect(url_for('orders_page'))
    
    branches = Branch.query.all()
    products = Product.query.filter_by(display=True).all()
    categories = Category.query.all()
    
    return render_template('create_order.html',
                         user=current_user,
                         walk_in_order_type_id=walk_in_order_type.id,
                         branches=branches,
                         products=products,
                         categories=categories)

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
        query = query.join(Category).filter(Category.name == category)
    if branch:
        query = query.join(Branch).filter(Branch.name == branch)
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    
    products = query.paginate(page=page, per_page=20, error_out=False)
    
    products_data = []
    for product in products.items:
        products_data.append({
            'id': product.id,
            'name': product.name,
            'category': product.category.name,
            'branch': product.branch.name,
            'buying_price': product.buyingprice,
            'selling_price': product.sellingprice,
            'stock': product.stock,
            'product_code': product.productcode,
            'display': product.display,
            'image_url': product.image_url
        })
    
    # Get filter options
    categories = Category.query.all()
    branches = Branch.query.all()
    
    return render_template('products.html', 
                         user=current_user, 
                         products=products_data,
                         pagination=products,
                         categories=categories,
                         branches=branches,
                         current_category=category,
                         current_branch=branch,
                         current_search=search)

@app.route("/products/<int:product_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        try:
            product.name = request.form['name']
            product.categoryid = int(request.form['category_id'])
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
    
    categories = Category.query.all()
    branches = Branch.query.all()
    
    return render_template('edit_product.html',
                         user=current_user,
                         product=product,
                         categories=categories,
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
    category_id = request.args.get('category_id', type=int)
    branch_id = request.args.get('branch_id', type=int)
    
    query = Product.query.filter_by(display=True)
    
    if category_id:
        query = query.filter_by(categoryid=category_id)
    if branch_id:
        query = query.filter_by(branchid=branch_id)
    
    products = query.all()
    
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'selling_price': p.sellingprice,
        'stock': p.stock,
        'product_code': p.productcode
    } for p in products])

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

@app.route("/test")
def test():
    return render_template('test.html', test_data={'items': [1, 2, 3]})

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Payment Management Routes
@app.route("/payments")
@login_required
def payments_page():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    payment_method = request.args.get('payment_method', '')
    
    query = Payment.query
    
    if status:
        query = query.filter_by(payment_status=status)
    if payment_method:
        query = query.filter_by(payment_method=payment_method)
    
    payments = query.order_by(Payment.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    payments_data = []
    for payment in payments.items:
        payments_data.append({
            'id': payment.id,
            'order_id': payment.orderid,
            'customer_name': f"{payment.user.firstname} {payment.user.lastname}",
            'amount': float(payment.amount),
            'payment_method': payment.payment_method,
            'payment_status': payment.payment_status,
            'reference_number': payment.reference_number,
            'transaction_id': payment.transaction_id,
            'payment_date': payment.payment_date.strftime('%Y-%m-%d %H:%M') if payment.payment_date else None,
            'created_at': payment.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    return render_template('payments.html',
                         user=current_user,
                         payments=payments_data,
                         pagination=payments,
                         current_status=status,
                         current_payment_method=payment_method)

@app.route("/orders/<int:order_id>/payment", methods=['GET', 'POST'])
@login_required
def process_payment(order_id):
    order = Order.query.get_or_404(order_id)
    
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form.to_dict()
            
            # Validate required fields
            if not data.get('amount') or not data.get('payment_method'):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Amount and payment method are required'})
                flash('Amount and payment method are required', 'danger')
                return redirect(url_for('process_payment', order_id=order_id))
            
            success, payment_id, reference_number = PaymentService.process_payment(order_id, data, current_user)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'payment_id': payment_id,
                    'reference_number': reference_number,
                    'message': 'Payment processed successfully'
                })
            
            flash(f'Payment processed successfully! Reference: {reference_number}', 'success')
            return redirect(url_for('order_detail', order_id=order_id))
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': str(e)})
            flash(f'Error processing payment: {str(e)}', 'danger')
            return redirect(url_for('process_payment', order_id=order_id))
    
    # GET request - show payment form
    # Calculate total amount
    total_amount = sum(item.quantity * float(item.final_price) for item in order.order_items)
    
    # Get payment history for this order
    payment_history = Payment.query.filter_by(orderid=order.id).order_by(Payment.created_at.desc()).all()
    
    return render_template('process_payment.html',
                         user=current_user,
                         order=order,
                         total_amount=total_amount,
                         payment_history=payment_history)

@app.route("/payments/<int:payment_id>")
@login_required
def payment_detail(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    
    payment_data = {
        'id': payment.id,
        'order_id': payment.orderid,
        'customer_name': f"{payment.user.firstname} {payment.user.lastname}",
        'amount': float(payment.amount),
        'payment_method': payment.payment_method,
        'payment_status': payment.payment_status,
        'reference_number': payment.reference_number,
        'transaction_id': payment.transaction_id,
        'notes': payment.notes,
        'payment_date': payment.payment_date.strftime('%Y-%m-%d %H:%M') if payment.payment_date else None,
        'created_at': payment.created_at.strftime('%Y-%m-%d %H:%M')
    }
    
    return render_template('payment_detail.html',
                         user=current_user,
                         payment=payment_data)

@app.route("/payments/<int:payment_id>/refund", methods=['POST'])
@login_required
def refund_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    
    if payment.payment_status != 'completed':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Only completed payments can be refunded'})
        flash('Only completed payments can be refunded', 'danger')
        return redirect(url_for('payment_detail', payment_id=payment_id))
    
    try:
        # Update payment status
        payment.payment_status = 'refunded'
        payment.updated_at = datetime.utcnow()
        
        # Update order payment status
        order = payment.order
        order.payment_status = 'refunded'
        
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Payment refunded successfully'})
        
        flash('Payment refunded successfully', 'success')
        return redirect(url_for('payment_detail', payment_id=payment_id))
        
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error refunding payment: {str(e)}', 'danger')
        return redirect(url_for('payment_detail', payment_id=payment_id))

# API Routes for payments
@app.route("/api/payment-methods")
@login_required
def get_payment_methods():
    payment_methods = [
        {'id': 'cash', 'name': 'Cash'},
        {'id': 'card', 'name': 'Credit/Debit Card'},
        {'id': 'mobile_money', 'name': 'Mobile Money'},
        {'id': 'bank_transfer', 'name': 'Bank Transfer'}
    ]
    return jsonify(payment_methods)

# Invoice and Receipt Routes
@app.route("/invoices")
@login_required
def invoices_page():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    query = Invoice.query
    
    if status:
        query = query.filter_by(status=status)
    
    invoices = query.order_by(Invoice.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    invoices_data = []
    for invoice in invoices.items:
        invoices_data.append({
            'id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'order_id': invoice.orderid,
            'customer_name': f"{invoice.order.user.firstname} {invoice.order.user.lastname}",
            'total_amount': float(invoice.total_amount),
            'status': invoice.status,
            'due_date': invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else None,
            'created_at': invoice.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    return render_template('invoices.html',
                         user=current_user,
                         invoices=invoices_data,
                         pagination=invoices,
                         current_status=status)

@app.route("/invoices/<int:invoice_id>")
@login_required
def invoice_detail(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    
    invoice_data = {
        'id': invoice.id,
        'invoice_number': invoice.invoice_number,
        'order_id': invoice.orderid,
        'customer_name': f"{invoice.order.user.firstname} {invoice.order.user.lastname}",
        'customer_email': invoice.order.user.email,
        'total_amount': float(invoice.total_amount),
        'subtotal': float(invoice.subtotal),
        'tax_amount': float(invoice.tax_amount),
        'discount_amount': float(invoice.discount_amount),
        'status': invoice.status,
        'due_date': invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else None,
        'notes': invoice.notes,
        'created_at': invoice.created_at.strftime('%Y-%m-%d %H:%M'),
        'order_items': []
    }
    
    # Get order items
    for item in invoice.order.order_items:
        item_total = item.quantity * float(item.final_price)
        invoice_data['order_items'].append({
            'product_name': item.product.name,
            'quantity': item.quantity,
            'price': float(item.final_price),
            'total': item_total
        })
    
    return render_template('invoice_detail.html',
                         user=current_user,
                         invoice=invoice_data)

@app.route("/receipts")
@login_required
def receipts_page():
    page = request.args.get('page', 1, type=int)
    
    receipts = Receipt.query.order_by(Receipt.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    receipts_data = []
    for receipt in receipts.items:
        receipts_data.append({
            'id': receipt.id,
            'receipt_number': receipt.receipt_number,
            'order_id': receipt.orderid,
            'customer_name': f"{receipt.order.user.firstname} {receipt.order.user.lastname}",
            'payment_amount': float(receipt.payment_amount),
            'previous_balance': float(receipt.previous_balance),
            'remaining_balance': float(receipt.remaining_balance),
            'payment_method': receipt.payment_method,
            'reference_number': receipt.reference_number,
            'created_at': receipt.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    return render_template('receipts.html',
                         user=current_user,
                         receipts=receipts_data,
                         pagination=receipts)

@app.route("/receipts/<int:receipt_id>")
@login_required
def receipt_detail(receipt_id):
    receipt = Receipt.query.get_or_404(receipt_id)
    
    receipt_data = {
        'id': receipt.id,
        'receipt_number': receipt.receipt_number,
        'order_id': receipt.orderid,
        'customer_name': f"{receipt.order.user.firstname} {receipt.order.user.lastname}",
        'customer_email': receipt.order.user.email,
        'payment_amount': float(receipt.payment_amount),
        'previous_balance': float(receipt.previous_balance),
        'remaining_balance': float(receipt.remaining_balance),
        'payment_method': receipt.payment_method,
        'reference_number': receipt.reference_number,
        'transaction_id': receipt.transaction_id,
        'notes': receipt.notes,
        'created_at': receipt.created_at.strftime('%Y-%m-%d %H:%M')
    }
    
    return render_template('receipt_detail.html',
                         user=current_user,
                         receipt=receipt_data)

@app.route("/test-email")
def test_email():
    """Test route to verify email functionality"""
    try:
        from email_service import get_email_service
        email_service = get_email_service()
        
        if email_service:
            # Test password change alert
            change_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            result = email_service.send_password_change_alert(
                to_email="test@example.com",
                user_name="Test User",
                change_time=change_time
            )
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': 'Test email sent successfully!',
                    'message_id': result.get('message_id')
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'Failed to send test email: {result.get("error", "Unknown error")}'
                })
        else:
            return jsonify({
                'success': False,
                'message': 'Email service not available. Check your Brevo API key configuration.'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error testing email: {str(e)}'
        })

@app.route("/debug/order-types")
@login_required
def debug_order_types():
    """Debug route to check order types in database"""
    order_types = OrderType.query.all()
    orders = Order.query.join(OrderType).all()
    
    debug_info = {
        'order_types': [{'id': ot.id, 'name': ot.name} for ot in order_types],
        'orders': [{'id': o.id, 'order_type': o.ordertype.name, 'user_id': o.userid} for o in orders]
    }
    
    return jsonify(debug_info)

@app.route("/orders/<int:order_id>/negotiate", methods=['GET', 'POST'])
@login_required
def negotiate_order_prices(order_id):
    """Show price negotiation page for an order"""
    order = Order.query.get_or_404(order_id)
    
    # Only allow negotiation for pending orders
    if order.approvalstatus:
        flash('Cannot negotiate prices for approved orders', 'warning')
        return redirect(url_for('order_detail', order_id=order_id))
    
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form.to_dict()
            negotiations = data.get('negotiations', [])
            
            total_updated = 0
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
                        total_updated += 1
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
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
        original_price = float(item.original_price) if item.original_price is not None else float(item.product.sellingprice)
        negotiated_price = float(item.negotiated_price) if item.negotiated_price is not None else None
        final_price = float(item.final_price) if item.final_price is not None else original_price
        
        order_items_data.append({
            'id': item.id,
            'product_name': item.product.name,
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

# Delivery Routes
@app.route("/deliveries")
@login_required
def deliveries_page():
    """List all deliveries with pagination"""
    page = request.args.get('page', 1, type=int)
    delivery_status = request.args.get('delivery_status', '')
    payment_status = request.args.get('payment_status', '')
    
    query = Delivery.query.join(Order).order_by(Delivery.created_at.desc())
    
    if delivery_status:
        query = query.filter(Delivery.delivery_status == delivery_status)
    
    if payment_status:
        query = query.filter(Delivery.payment_status == payment_status)
    
    deliveries = query.paginate(page=page, per_page=20, error_out=False)
    
    return render_template('deliveries.html',
                         user=current_user,
                         deliveries=deliveries.items,
                         pagination=deliveries,
                         current_delivery_status=delivery_status,
                         current_payment_status=payment_status)

@app.route("/deliveries/create", methods=['GET', 'POST'])
@login_required
def create_delivery():
    """Create a new delivery for an order"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form.to_dict()
            order_id = data.get('order_id')
            delivery_amount = data.get('delivery_amount')
            delivery_location = data.get('delivery_location')
            customer_phone = data.get('customer_phone')
            agreed_delivery_time = data.get('agreed_delivery_time')
            notes = data.get('notes', '')

            # Get available orders for dropdown (use 'userid' instead of 'user_id')
            available_orders = Order.query.filter_by(userid=current_user.id).all()

            # Build form dict from submitted data
            form = {
                'delivery_amount': delivery_amount or '',
                'customer_phone': customer_phone or '',
                'agreed_delivery_time': agreed_delivery_time or '',
                'location': delivery_location or '',
                'delivery_status': data.get('delivery_status', 'pending'),
                'payment_status': data.get('payment_status', 'pending')
            }

            # Validate required fields
            if not all([order_id, delivery_amount, delivery_location, customer_phone]):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'All required fields must be filled'})
                flash('All required fields must be filled', 'danger')
                return render_template('create_delivery.html',
                                      user=current_user,
                                      order=None,
                                      available_orders=available_orders,
                                      form=form,
                                      selected_order_id=order_id)

            # Check if order exists
            order = Order.query.get(order_id)
            if not order:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Order not found'})
                flash('Order not found', 'danger')
                return render_template('create_delivery.html',
                                      user=current_user,
                                      order=None,
                                      available_orders=available_orders,
                                      form=form,
                                      selected_order_id=order_id)

            # Check if delivery already exists for this order
            existing_delivery = Delivery.query.filter_by(order_id=order_id).first()
            if existing_delivery:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Delivery already exists for this order'})
                flash('Delivery already exists for this order', 'warning')
                return redirect(url_for('delivery_detail', delivery_id=existing_delivery.id))

            # Create delivery
            delivery = Delivery(
                order_id=order_id,
                delivery_amount=delivery_amount,
                delivery_location=delivery_location,
                customer_phone=customer_phone,
                agreed_delivery_time=datetime.strptime(agreed_delivery_time, '%Y-%m-%dT%H:%M') if agreed_delivery_time else None,
                notes=notes
            )

            db.session.add(delivery)
            db.session.commit()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True, 
                    'message': 'Delivery created successfully',
                    'delivery_id': delivery.id
                })

            flash('Delivery created successfully', 'success')
            return redirect(url_for('delivery_detail', delivery_id=delivery.id))

        except Exception as e:
            db.session.rollback()
            # Get available orders for dropdown (use 'userid' instead of 'user_id')
            available_orders = Order.query.filter_by(userid=current_user.id).all()
            # Build form dict from submitted data
            form = {
                'delivery_amount': request.form.get('delivery_amount', ''),
                'customer_phone': request.form.get('customer_phone', ''),
                'agreed_delivery_time': request.form.get('agreed_delivery_time', ''),
                'location': request.form.get('delivery_location', ''),
                'delivery_status': request.form.get('delivery_status', 'pending'),
                'payment_status': request.form.get('payment_status', 'pending')
            }
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': f'Error creating delivery: {str(e)}'})
            flash(f'Error creating delivery: {str(e)}', 'danger')
            return render_template('create_delivery.html',
                                  user=current_user,
                                  order=None,
                                  available_orders=available_orders,
                                  form=form,
                                  selected_order_id=request.form.get('order_id'))

    # GET request - show create delivery form
    order_id = request.args.get('order_id')
    order = None
    if order_id:
        order = Order.query.get(order_id)

    # Get available orders for dropdown (use 'userid' instead of 'user_id')
    available_orders = Order.query.filter_by(userid=current_user.id).all()

    # Initialize form data
    form = {
        'delivery_amount': '',
        'customer_phone': '',
        'agreed_delivery_time': '',
        'location': '',
        'delivery_status': 'pending',
        'payment_status': 'pending'
    }

    return render_template('create_delivery.html',
                         user=current_user,
                         order=order,
                         available_orders=available_orders,
                         form=form,
                         selected_order_id=order_id)

@app.route("/deliveries/<int:delivery_id>")
@login_required
def delivery_detail(delivery_id):
    """View delivery details"""
    delivery = Delivery.query.get_or_404(delivery_id)
    
    # Calculate order total
    order_total = sum(float(item.final_price) * item.quantity for item in delivery.order.order_items)
    
    return render_template('delivery_detail.html',
                         user=current_user,
                         delivery=delivery,
                         order_total=order_total)

@app.route("/deliveries/<int:delivery_id>/update-status", methods=['POST'])
@login_required
def update_delivery_status(delivery_id):
    """Update delivery status"""
    delivery = Delivery.query.get_or_404(delivery_id)
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'success': False, 'message': 'Status is required'})
        
        valid_statuses = ['pending', 'in_transit', 'delivered', 'cancelled', 'failed']
        if new_status not in valid_statuses:
            return jsonify({'success': False, 'message': 'Invalid status'})
        
        delivery.delivery_status = new_status
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Delivery status updated to {new_status}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating status: {str(e)}'})



@app.route("/orders/<int:order_id>/delivery")
@login_required
def order_delivery(order_id):
    """View delivery for a specific order"""
    order = Order.query.get_or_404(order_id)
    delivery = Delivery.query.filter_by(order_id=order_id).first()
    
    if not delivery:
        flash('No delivery found for this order', 'info')
        return redirect(url_for('create_delivery', order_id=order_id))
    
    delivery_data = {
        'id': delivery.id,
        'order_id': delivery.order_id,
        'customer_name': f"{delivery.order.user.firstname} {delivery.order.user.lastname}",
        'customer_email': delivery.order.user.email,
        'customer_phone': delivery.customer_phone,
        'delivery_location': delivery.delivery_location,
        'delivery_amount': float(delivery.delivery_amount),
        'delivery_status': delivery.delivery_status,
        'payment_status': delivery.payment_status,
        'agreed_delivery_time': delivery.agreed_delivery_time.strftime('%Y-%m-%d %H:%M') if delivery.agreed_delivery_time else None,
        'notes': delivery.notes,
        'created_at': delivery.created_at.strftime('%Y-%m-%d %H:%M'),
        'updated_at': delivery.updated_at.strftime('%Y-%m-%d %H:%M')
    }
    
    return render_template('order_delivery.html',
                         user=current_user,
                         order=order,
                         delivery=delivery_data)

@app.route("/api/orders/<int:order_id>")
@login_required
def api_order_detail(order_id):
    """Get order details by ID for API calls"""
    order = Order.query.get_or_404(order_id)
    
    # Check if user has permission to view this order
    if order.userid != current_user.id:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    # Calculate total amount from order items
    total_amount = sum(float(item.final_price) * item.quantity for item in order.order_items)
    
    order_data = {
        'id': order.id,
        'customer_name': f"{order.user.firstname} {order.user.lastname}",
        'order_type': order.ordertype.name,
        'branch': order.branch.name,
        'status': 'Approved' if order.approvalstatus else 'Pending',
        'total_amount': total_amount,
        'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
        'customer_phone': getattr(order.user, 'phone', None)  # In case phone doesn't exist
    }
    
    return jsonify({'success': True, 'order': order_data})

# Delivery Payment Routes
@app.route("/delivery-payments")
@login_required
def delivery_payments_page():
    """List all delivery payments with pagination"""
    page = request.args.get('page', 1, type=int)
    payment_status = request.args.get('payment_status', '')
    
    query = DeliveryPayment.query.join(Delivery).join(Order).order_by(DeliveryPayment.created_at.desc())
    
    if payment_status:
        query = query.filter(DeliveryPayment.payment_status == payment_status)
    
    payments = query.paginate(page=page, per_page=20, error_out=False)
    
    return render_template('delivery_payments.html',
                         user=current_user,
                         payments=payments.items,
                         pagination=payments,
                         current_payment_status=payment_status)

@app.route("/delivery-payments/<int:payment_id>")
@login_required
def delivery_payment_detail(payment_id):
    """View delivery payment details"""
    payment = DeliveryPayment.query.get_or_404(payment_id)
    
    return render_template('delivery_payment_detail.html',
                         user=current_user,
                         payment=payment)

@app.route("/deliveries/<int:delivery_id>/process-payment", methods=['GET', 'POST'])
@login_required
def process_delivery_payment_new(delivery_id):
    """Process payment for delivery with new DeliveryPayment model"""
    delivery = Delivery.query.get_or_404(delivery_id)
    
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form.to_dict()
            
            payment_method = data.get('payment_method')
            amount = data.get('amount')
            notes = data.get('notes', '')
            
            if not all([payment_method, amount]):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Payment method and amount are required'})
                flash('Payment method and amount are required', 'danger')
                return redirect(url_for('process_delivery_payment_new', delivery_id=delivery_id))
            
            # Validate amount
            if float(amount) != float(delivery.delivery_amount):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Payment amount must match delivery amount'})
                flash('Payment amount must match delivery amount', 'danger')
                return redirect(url_for('process_delivery_payment_new', delivery_id=delivery_id))
            
            # Create delivery payment
            delivery_payment = DeliveryPayment(
                delivery_id=delivery_id,
                user_id=current_user.id,
                amount=amount,
                payment_method=payment_method,
                payment_status='completed',
                notes=notes,
                payment_date=datetime.utcnow()
            )
            
            # Update delivery payment status
            delivery.payment_status = 'paid'
            
            db.session.add(delivery_payment)
            db.session.commit()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True, 
                    'message': 'Delivery payment processed successfully',
                    'payment_id': delivery_payment.id
                })
            
            flash('Delivery payment processed successfully', 'success')
            return redirect(url_for('delivery_payment_detail', payment_id=delivery_payment.id))
            
        except Exception as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': f'Error processing payment: {str(e)}'})
            flash(f'Error processing payment: {str(e)}', 'danger')
            return redirect(url_for('process_delivery_payment_new', delivery_id=delivery_id))
    
    # GET request - show payment form
    return render_template('process_delivery_payment.html',
                         user=current_user,
                         delivery=delivery)

@app.route("/delivery-payments/<int:payment_id>/refund", methods=['POST'])
@login_required
def refund_delivery_payment(payment_id):
    """Refund a delivery payment"""
    payment = DeliveryPayment.query.get_or_404(payment_id)
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        refund_reason = data.get('refund_reason', '')
        
        # Update payment status
        payment.payment_status = 'refunded'
        payment.notes = f"Refunded: {refund_reason}" if refund_reason else "Payment refunded"
        
        # Update delivery payment status
        delivery = payment.delivery
        delivery.payment_status = 'pending'
        
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True, 
                'message': 'Delivery payment refunded successfully'
            })
        
        flash('Delivery payment refunded successfully', 'success')
        return redirect(url_for('delivery_payment_detail', payment_id=payment_id))
        
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': f'Error refunding payment: {str(e)}'})
        flash(f'Error refunding payment: {str(e)}', 'danger')
        return redirect(url_for('delivery_payment_detail', payment_id=payment_id))

if __name__ == '__main__':
    app.run(debug=False)