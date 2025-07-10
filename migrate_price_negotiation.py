#!/usr/bin/env python3
"""
Database migration script to add price negotiation fields to orderitems table.
This script will:
1. Add new columns to the orderitems table
2. Update existing order items with original prices
3. Set final_price to original_price for existing items
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app
from app.models import OrderItem, Product
from app import db
from sqlalchemy import text

def migrate_price_negotiation():
    """Migrate existing order items to include price negotiation fields"""
    
    with app.app_context():
        try:
            print("Starting price negotiation migration...")
            
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('orderitems')]
            
            if 'original_price' in existing_columns:
                print("Migration already completed. Columns exist.")
                return
            
            # Add new columns
            print("Adding new columns to orderitems table...")
            
            # Add original_price column
            db.session.execute(text("""
                ALTER TABLE orderitems 
                ADD COLUMN original_price DECIMAL(10,2) NOT NULL DEFAULT 0.00
            """))
            
            # Add negotiated_price column
            db.session.execute(text("""
                ALTER TABLE orderitems 
                ADD COLUMN negotiated_price DECIMAL(10,2) NULL
            """))
            
            # Add final_price column
            db.session.execute(text("""
                ALTER TABLE orderitems 
                ADD COLUMN final_price DECIMAL(10,2) NOT NULL DEFAULT 0.00
            """))
            
            # Add negotiation_notes column
            db.session.execute(text("""
                ALTER TABLE orderitems 
                ADD COLUMN negotiation_notes TEXT NULL
            """))
            
            db.session.commit()
            print("Columns added successfully.")
            
            # Update existing order items with original prices
            print("Updating existing order items...")
            
            # Get all order items that need updating
            order_items = OrderItem.query.all()
            
            updated_count = 0
            for item in order_items:
                try:
                    # Get the product's selling price
                    product = Product.query.get(item.productid)
                    if product and product.sellingprice:
                        original_price = float(product.sellingprice)
                        final_price = original_price
                        
                        # Update the order item
                        item.original_price = original_price
                        item.final_price = final_price
                        item.negotiated_price = None  # No negotiation for existing items
                        item.negotiation_notes = None
                        
                        updated_count += 1
                    else:
                        print(f"Warning: Product not found or no selling price for order item {item.id}")
                        
                except Exception as e:
                    print(f"Error updating order item {item.id}: {str(e)}")
            
            # Commit the changes
            db.session.commit()
            
            print(f"Migration completed successfully!")
            print(f"Updated {updated_count} order items with original prices.")
            
        except Exception as e:
            print(f"Migration failed: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate_price_negotiation() 