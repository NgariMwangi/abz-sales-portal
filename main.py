from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import json

db = SQLAlchemy()
from models import Branch, Category, User, Product, OrderType, Order, OrderItem, StockTransaction, Payment, Invoice, Receipt

app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:deno0707@localhost:5432/abz'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:#Deno0707@69.197.187.23:5432/abz'


app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this to a secure secret key

# Initialize SQLAlchemy with the app
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Role-based access control decorator
def sales_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if current_user.role != 'sales':
            flash('Access denied. Sales role required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Utility functions for invoice and receipt generation
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
    invoice_number = generate_invoice_number()
    
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
    
    db.session.add(invoice)
    db.session.commit()
    return invoice

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
    # Get summary statistics
    stats = {
        'total_orders': Order.query.count(),
        'pending_orders': Order.query.filter_by(approvalstatus=False).count(),
        'total_products': Product.query.count(),
        'low_stock_products': Product.query.filter(Product.stock < 10).count(),
        'total_payments': Payment.query.count(),
        'total_revenue': float(Payment.query.filter_by(payment_status='completed').with_entities(db.func.sum(Payment.amount)).scalar() or 0),
        'pending_payments': Payment.query.filter_by(payment_status='pending').count(),
        'total_invoices': Invoice.query.count(),
        'total_receipts': Receipt.query.count()
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
    
    # Get low stock products
    low_stock_products = Product.query.filter(Product.stock < 10).limit(5).all()
    low_stock_data = []
    for product in low_stock_products:
        low_stock_data.append({
            'id': product.id,
            'name': product.name,
            'stock': product.stock
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
                         low_stock_products=low_stock_data,
                         recent_payments=recent_payments_data)

# Order Management Routes
@app.route("/orders")
@login_required
def orders_page():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    order_type = request.args.get('order_type', '')
    
    query = Order.query
    
    if status == 'pending':
        query = query.filter_by(approvalstatus=False)
    elif status == 'approved':
        query = query.filter_by(approvalstatus=True)
    
    if order_type:
        query = query.join(OrderType).filter(OrderType.name == order_type)
    
    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    orders_data = []
    for order in orders.items:
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
            'items': order_items
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
        'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
        'approved_at': order.approved_at.strftime('%Y-%m-%d %H:%M') if order.approved_at else None,
        'order_items': []
    }
    
    total_amount = 0
    for item in order.order_items:
        item_total = item.quantity * item.product.sellingprice
        total_amount += item_total
        order_data['order_items'].append({
            'id': item.id,
            'product_name': item.product.name,
            'quantity': item.quantity,
            'price': item.product.sellingprice,
            'total': item_total
        })
    
    order_data['total_amount'] = total_amount
    
    return render_template('order_detail.html', 
                         user=current_user, 
                         order=order_data)

@app.route("/orders/<int:order_id>/approve", methods=['POST'])
@login_required
def approve_order(order_id):
    order = Order.query.get_or_404(order_id)
    if not order.approvalstatus:
        order.approvalstatus = True
        order.approved_at = datetime.utcnow()
        
        # Update stock for each item
        for item in order.order_items:
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
        flash('Order approved successfully!', 'success')
    else:
        flash('Order is already approved.', 'info')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Order approved successfully'})
    return redirect(url_for('orders_page'))

@app.route("/orders/<int:order_id>/reject", methods=['POST'])
@login_required
def reject_order(order_id):
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    flash('Order rejected and deleted.', 'success')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Order rejected and deleted'})
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
            
            # Create order
            order = Order(
                userid=current_user.id,  # Sales person creating the order
                ordertypeid=int(data['order_type_id']),
                branchid=int(data['branch_id'])
            )
            db.session.add(order)
            db.session.flush()  # Get the order ID
            
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
                
                order_item = OrderItem(
                    orderid=order.id,
                    productid=product.id,
                    quantity=quantity
                )
                db.session.add(order_item)
                total_amount += product.sellingprice * quantity
            
            db.session.commit()
            
            # Create invoice for the order
            try:
                create_invoice_for_order(order, total_amount)
            except Exception as e:
                print(f"Warning: Could not create invoice for order {order.id}: {str(e)}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'order_id': order.id,
                    'total_amount': total_amount,
                    'message': 'Order created successfully'
                })
            
            flash(f'Order created successfully! Order ID: {order.id}', 'success')
            return redirect(url_for('order_detail', order_id=order.id))
            
        except ValueError as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': str(e)})
            flash(f'Validation error: {str(e)}', 'danger')
            return redirect(url_for('create_order'))
        except Exception as e:
            db.session.rollback()
            print(f"Error creating order: {str(e)}")  # For debugging
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': f'Error creating order: {str(e)}'})
            flash(f'Error creating order: {str(e)}', 'danger')
            return redirect(url_for('create_order'))
    
    # GET request - show form
    order_types = OrderType.query.all()
    branches = Branch.query.all()
    products = Product.query.filter_by(display=True).all()
    categories = Category.query.all()
    
    return render_template('create_order.html',
                         user=current_user,
                         order_types=order_types,
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
        
        product = Product.query.get_or_404(int(data['product_id']))
        quantity = int(data['quantity'])
        
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
            notes=data.get('notes', 'Stock added via web form')
        )
        
        db.session.add(stock_transaction)
        db.session.commit()
        
        message = f'Added {quantity} units to stock. New stock: {new_stock}'
        
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
        
        product = Product.query.get_or_404(int(data['product_id']))
        quantity = int(data['quantity'])
        
        if product.stock < quantity:
            message = 'Insufficient stock'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': message})
            flash(message, 'danger')
            return redirect(url_for('stock_page'))
        
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
            notes=data.get('notes', 'Stock removed via web form')
        )
        
        db.session.add(stock_transaction)
        db.session.commit()
        
        message = f'Removed {quantity} units from stock. New stock: {new_stock}'
        
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
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'payment_id': payment.id,
                    'reference_number': reference_number,
                    'message': 'Payment processed successfully'
                })
            
            flash(f'Payment processed successfully! Reference: {reference_number}', 'success')
            return redirect(url_for('order_detail', order_id=order_id))
            
        except Exception as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': str(e)})
            flash(f'Error processing payment: {str(e)}', 'danger')
            return redirect(url_for('process_payment', order_id=order_id))
    
    # GET request - show payment form
    # Calculate total amount
    total_amount = sum(item.quantity * item.product.sellingprice for item in order.order_items)
    
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
        item_total = item.quantity * item.product.sellingprice
        invoice_data['order_items'].append({
            'product_name': item.product.name,
            'quantity': item.quantity,
            'price': item.product.sellingprice,
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

if __name__ == '__main__':
    app.run(debug=True)