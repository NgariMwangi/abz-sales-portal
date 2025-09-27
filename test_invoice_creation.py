#!/usr/bin/env python3
"""
Test script to verify invoice creation is working
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app
from app.models import Order, Invoice, OrderItem, BranchProduct, OrderType, User
from app.utils import create_invoice_for_order
from app import db

def test_invoice_creation():
    """Test invoice creation for existing orders"""
    
    with app.app_context():
        try:
            print("Testing invoice creation...")
            
            # Get all orders
            orders = Order.query.all()
            print(f"Found {len(orders)} orders")
            
            for order in orders:
                print(f"\nChecking order {order.id}:")
                
                # Check if invoice exists
                invoice = Invoice.query.filter_by(orderid=order.id).first()
                if invoice:
                    print(f"  ✓ Invoice exists: {invoice.invoice_number}")
                else:
                    print(f"  ✗ No invoice found")
                    
                    # Calculate total amount
                    total_amount = 0
                    for item in order.order_items:
                        if item.final_price is not None:
                            item_price = float(item.final_price)
                        elif item.product.sellingprice is not None:
                            item_price = float(item.product.sellingprice)
                        else:
                            item_price = 0.0
                        total_amount += item.quantity * item_price
                    
                    print(f"  Total amount: {total_amount}")
                    
                    # Try to create invoice
                    try:
                        new_invoice = create_invoice_for_order(order, total_amount)
                        print(f"  ✓ Created invoice: {new_invoice.invoice_number}")
                    except Exception as e:
                        print(f"  ✗ Failed to create invoice: {str(e)}")
            
            # Summary
            total_orders = len(orders)
            orders_with_invoices = len([o for o in orders if Invoice.query.filter_by(orderid=o.id).first()])
            orders_without_invoices = total_orders - orders_with_invoices
            
            print(f"\nSummary:")
            print(f"  Total orders: {total_orders}")
            print(f"  Orders with invoices: {orders_with_invoices}")
            print(f"  Orders without invoices: {orders_without_invoices}")
            
        except Exception as e:
            print(f"Error during testing: {str(e)}")

if __name__ == '__main__':
    test_invoice_creation() 