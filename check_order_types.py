#!/usr/bin/env python3
"""
Script to check order types in the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app
from app.models import OrderType

def check_order_types():
    """Check what order types exist in the database"""
    
    with app.app_context():
        try:
            print("Checking order types in database...")
            
            order_types = OrderType.query.all()
            
            if not order_types:
                print("No order types found in database!")
                return
            
            print(f"Found {len(order_types)} order type(s):")
            for order_type in order_types:
                print(f"  ID: {order_type.id}, Name: '{order_type.name}'")
            
            # Check for walk-in variations
            walk_in_variations = ['walk-in', 'walkin', 'walk in', 'Walk-in', 'WalkIn', 'Walk In']
            for variation in walk_in_variations:
                found = OrderType.query.filter_by(name=variation).first()
                if found:
                    print(f"\nFound walk-in order type: ID {found.id}, Name '{found.name}'")
                    return found.id
            
            print("\nNo walk-in order type found. Available types:")
            for order_type in order_types:
                print(f"  - {order_type.name}")
            
        except Exception as e:
            print(f"Error checking order types: {str(e)}")

if __name__ == '__main__':
    check_order_types() 