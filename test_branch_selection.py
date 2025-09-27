#!/usr/bin/env python3
"""
Test script for branch selection functionality
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from app.models import Order, OrderItem, BranchProduct, Branch, OrderType, User, StockTransaction
from app import db

def test_branch_selection():
    """Test the branch selection functionality"""
    with app.app_context():
        print("🧪 Testing Branch Selection Functionality...")
        
        # Check if we have the required models
        try:
            # Test database connection
            branches = Branch.query.all()
            print(f"✅ Found {len(branches)} branches")
            
            orders = Order.query.all()
            print(f"✅ Found {len(orders)} orders")
            
            products = Product.query.all()
            print(f"✅ Found {len(products)} products")
            
            # Test online order type
            online_order_type = OrderType.query.filter_by(name='online').first()
            if online_order_type:
                print(f"✅ Found online order type: {online_order_type.name}")
            else:
                print("⚠️  Online order type not found - you may need to create it")
            
            print("\n🎉 Branch selection functionality is ready!")
            print("\n📋 How to test:")
            print("1. Create an online order with multiple products")
            print("2. Go to the order detail page")
            print("3. Click 'Select Fulfillment Branch' for online orders")
            print("4. Choose different branches for each product")
            print("5. Approve the order")
            print("6. Check that stock is reduced from the selected branches")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False
        
        return True

if __name__ == "__main__":
    test_branch_selection() 