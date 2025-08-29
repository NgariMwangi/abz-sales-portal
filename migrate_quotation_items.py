#!/usr/bin/env python3
"""
Migration script to add product_name field and make product_id nullable in quotationitems table.
This allows quotations to have manual items that are not in the product catalog.

Run this script to update your database schema.
"""

import sqlite3
import os
from datetime import datetime

def migrate_quotation_items():
    """Migrate the quotationitems table to support manual items"""
    
    # Database file path
    db_path = 'abz_sales_portal.db'
    
    if not os.path.exists(db_path):
        print(f"Error: Database file '{db_path}' not found!")
        print("Please run this script from the directory containing your database file.")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Starting quotation items migration...")
        print(f"Database: {db_path}")
        print(f"Timestamp: {datetime.now()}")
        print("-" * 50)
        
        # Check current table structure
        cursor.execute("PRAGMA table_info(quotationitems)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"Current columns: {column_names}")
        
        # Step 1: Add product_name column if it doesn't exist
        if 'product_name' not in column_names:
            print("Adding product_name column...")
            cursor.execute("ALTER TABLE quotationitems ADD COLUMN product_name VARCHAR(255)")
            print("✓ product_name column added")
        else:
            print("✓ product_name column already exists")
        
        # Step 2: Make product_id nullable (SQLite doesn't support ALTER COLUMN, so we need to recreate)
        # First, check if product_id is already nullable
        cursor.execute("PRAGMA table_info(quotationitems)")
        columns = cursor.fetchall()
        product_id_col = None
        for col in columns:
            if col[1] == 'product_id':
                product_id_col = col
                break
        
        if product_id_col and product_id_col[3] == 1:  # 1 means NOT NULL
            print("Making product_id nullable...")
            
            # Create temporary table with new structure
            cursor.execute("""
                CREATE TABLE quotationitems_new (
                    id INTEGER PRIMARY KEY,
                    quotation_id INTEGER NOT NULL,
                    product_id INTEGER,
                    product_name VARCHAR(255),
                    quantity INTEGER NOT NULL,
                    unit_price NUMERIC(10, 2) NOT NULL,
                    total_price NUMERIC(10, 2) NOT NULL,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (quotation_id) REFERENCES quotations(id),
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
            """)
            
            # Copy data from old table
            cursor.execute("""
                INSERT INTO quotationitems_new 
                (id, quotation_id, product_id, product_name, quantity, unit_price, total_price, notes, created_at)
                SELECT id, quotation_id, product_id, product_name, quantity, unit_price, total_price, notes, created_at
                FROM quotationitems
            """)
            
            # Drop old table and rename new one
            cursor.execute("DROP TABLE quotationitems")
            cursor.execute("ALTER TABLE quotationitems_new RENAME TO quotationitems")
            
            print("✓ product_id is now nullable")
        else:
            print("✓ product_id is already nullable")
        
        # Step 3: Populate product_name for existing items
        print("Populating product_name for existing items...")
        
        # Update items that have product_id to use product name from products table
        cursor.execute("""
            UPDATE quotationitems 
            SET product_name = (
                SELECT name 
                FROM products 
                WHERE products.id = quotationitems.product_id
            )
            WHERE product_id IS NOT NULL
        """)
        
        # Count updated items
        cursor.execute("SELECT COUNT(*) FROM quotationitems WHERE product_name IS NOT NULL")
        updated_count = cursor.fetchone()[0]
        print(f"✓ Updated {updated_count} existing items with product names")
        
        # Commit changes
        conn.commit()
        
        # Verify final structure
        cursor.execute("PRAGMA table_info(quotationitems)")
        final_columns = cursor.fetchall()
        final_column_names = [col[1] for col in final_columns]
        
        print("\nFinal table structure:")
        for col in final_columns:
            nullable = "NULL" if col[3] == 0 else "NOT NULL"
            print(f"  {col[1]} {col[2]} {nullable}")
        
        print("\n✓ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        print("Rolling back changes...")
        conn.rollback()
        return False
        
    finally:
        conn.close()

def rollback_migration():
    """Rollback the migration if needed"""
    
    db_path = 'abz_sales_portal.db'
    
    if not os.path.exists(db_path):
        print(f"Error: Database file '{db_path}' not found!")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Rolling back quotation items migration...")
        
        # Check if product_name column exists
        cursor.execute("PRAGMA table_info(quotationitems)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'product_name' in column_names:
            print("Removing product_name column...")
            
            # Create temporary table without product_name
            cursor.execute("""
                CREATE TABLE quotationitems_old (
                    id INTEGER PRIMARY KEY,
                    quotation_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price NUMERIC(10, 2) NOT NULL,
                    total_price NUMERIC(10, 2) NOT NULL,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (quotation_id) REFERENCES quotations(id),
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
            """)
            
            # Copy data (excluding product_name)
            cursor.execute("""
                INSERT INTO quotationitems_old 
                (id, quotation_id, product_id, quantity, unit_price, total_price, notes, created_at)
                SELECT id, quotation_id, product_id, quantity, unit_price, total_price, notes, created_at
                FROM quotationitems
            """)
            
            # Drop new table and rename old one
            cursor.execute("DROP TABLE quotationitems")
            cursor.execute("ALTER TABLE quotationitems_old RENAME TO quotationitems")
            
            print("✓ product_name column removed")
        
        # Make product_id NOT NULL again
        cursor.execute("""
            CREATE TABLE quotationitems_final (
                id INTEGER PRIMARY KEY,
                quotation_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price NUMERIC(10, 2) NOT NULL,
                total_price NUMERIC(10, 2) NOT NULL,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (quotation_id) REFERENCES quotations(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        
        cursor.execute("""
            INSERT INTO quotationitems_final 
            (id, quotation_id, product_id, quantity, unit_price, total_price, notes, created_at)
            SELECT id, quotation_id, product_id, quantity, unit_price, total_price, notes, created_at
            FROM quotationitems
        """)
        
        cursor.execute("DROP TABLE quotationitems")
        cursor.execute("ALTER TABLE quotationitems_final RENAME TO quotationitems")
        
        conn.commit()
        print("✓ product_id is NOT NULL again")
        print("✓ Rollback completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Rollback failed: {str(e)}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    print("Quotation Items Migration Script")
    print("=" * 40)
    print("This script will:")
    print("1. Add product_name column to quotationitems table")
    print("2. Make product_id nullable to support manual items")
    print("3. Populate product_name for existing items")
    print()
    
    while True:
        choice = input("Choose an option:\n1. Run migration\n2. Rollback migration\n3. Exit\nEnter choice (1-3): ").strip()
        
        if choice == '1':
            if migrate_quotation_items():
                print("\nMigration completed successfully!")
                print("You can now create quotations with manual items.")
            else:
                print("\nMigration failed. Please check the error messages above.")
            break
        elif choice == '2':
            if rollback_migration():
                print("\nRollback completed successfully!")
            else:
                print("\nRollback failed. Please check the error messages above.")
            break
        elif choice == '3':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
    
    print("\nGoodbye!")
