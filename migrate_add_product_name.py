#!/usr/bin/env python3
"""
Database Migration Script: Add product_name field to OrderItem model

This script adds a new 'product_name' field to the orderitems table to support
both regular products and manual items in orders.

Run this script after updating the models.py file.
"""

import sqlite3
import os
from datetime import datetime

def migrate_database():
    """Add product_name field to orderitems table"""
    
    # Database file path (adjust if your database is elsewhere)
    db_path = 'app.db'  # or 'instance/app.db' depending on your setup
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        print("Please check the database path and run this script from the correct directory.")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"🔗 Connected to database: {db_path}")
        
        # Check if product_name column already exists
        cursor.execute("PRAGMA table_info(orderitems)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'product_name' in columns:
            print("✅ product_name column already exists in orderitems table")
            return True
        
        print("📝 Adding product_name column to orderitems table...")
        
        # Add the new column
        cursor.execute("""
            ALTER TABLE orderitems 
            ADD COLUMN product_name VARCHAR(255)
        """)
        
        # Update existing records to populate product_name
        print("🔄 Updating existing order items with product names...")
        
        # For items with productid, get the name from products table
        cursor.execute("""
            UPDATE orderitems 
            SET product_name = (
                SELECT name 
                FROM products 
                WHERE products.id = orderitems.productid
            )
            WHERE productid IS NOT NULL
        """)
        
        # For items without productid (manual items), set a default name
        cursor.execute("""
            UPDATE orderitems 
            SET product_name = 'Manual Item'
            WHERE productid IS NULL AND product_name IS NULL
        "")
        
        # Commit changes
        conn.commit()
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(orderitems)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'product_name' in columns:
            print("✅ Successfully added product_name column to orderitems table")
            
            # Show some statistics
            cursor.execute("SELECT COUNT(*) FROM orderitems")
            total_items = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM orderitems WHERE productid IS NOT NULL")
            regular_items = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM orderitems WHERE productid IS NULL")
            manual_items = cursor.fetchone()[0]
            
            print(f"📊 Migration Summary:")
            print(f"   Total order items: {total_items}")
            print(f"   Regular products: {regular_items}")
            print(f"   Manual items: {manual_items}")
            
            return True
        else:
            print("❌ Failed to add product_name column")
            return False
            
    except sqlite3.Error as e:
        print(f"❌ SQLite error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        if conn:
            conn.close()
            print("🔌 Database connection closed")

def rollback_migration():
    """Rollback the migration by removing the product_name column"""
    
    db_path = 'app.db'  # or 'instance/app.db' depending on your setup
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Rolling back migration...")
        
        # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
        # This is a simplified rollback - in production you'd want a more sophisticated approach
        
        # Get current table structure
        cursor.execute("PRAGMA table_info(orderitems)")
        columns = cursor.fetchall()
        
        # Create new table without product_name
        new_columns = []
        for col in columns:
            if col[1] != 'product_name':  # Skip the product_name column
                new_columns.append(f"{col[1]} {col[2]}")
        
        # Create new table
        cursor.execute(f"""
            CREATE TABLE orderitems_new (
                {', '.join(new_columns)}
            )
        """)
        
        # Copy data (excluding product_name)
        old_columns = [col[1] for col in columns if col[1] != 'product_name']
        cursor.execute(f"""
            INSERT INTO orderitems_new ({', '.join(old_columns)})
            SELECT {', '.join(old_columns)} FROM orderitems
        """)
        
        # Drop old table and rename new one
        cursor.execute("DROP TABLE orderitems")
        cursor.execute("ALTER TABLE orderitems_new RENAME TO orderitems")
        
        conn.commit()
        print("✅ Rollback completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Database Migration: Add product_name to OrderItem")
    print("=" * 50)
    
    # Check if user wants to rollback
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        print("🔄 Rollback mode selected")
        success = rollback_migration()
    else:
        print("📝 Migration mode selected")
        success = migrate_database()
    
    if success:
        print("\n🎉 Operation completed successfully!")
        print("\nNext steps:")
        print("1. Restart your Flask application")
        print("2. Test creating orders with manual items")
        print("3. Verify that product names are properly stored")
    else:
        print("\n❌ Operation failed!")
        print("Please check the error messages above and try again.")
    
    print("\n" + "=" * 50)
