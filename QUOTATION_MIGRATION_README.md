# Quotation Items Migration

This migration adds support for manual items in quotations, allowing you to create quotations with custom items that are not in your product catalog.

## What This Migration Does

1. **Adds `product_name` field** to the `quotationitems` table
2. **Makes `product_id` nullable** to support manual items
3. **Populates existing data** with product names from the products table

## Prerequisites

- Python 3.6 or higher
- Access to your SQLite database file (`abz_sales_portal.db`)
- Backup of your database (recommended)

## How to Run the Migration

### Option 1: Interactive Script (Recommended)

1. **Navigate to your project directory**:
   ```bash
   cd /path/to/your/abz_sales_portal
   ```

2. **Run the migration script**:
   ```bash
   python migrate_quotation_items.py
   ```

3. **Choose option 1** to run the migration

4. **Follow the prompts** and wait for completion

### Option 2: Manual SQL Commands

If you prefer to run SQL commands manually:

1. **Connect to your database**:
   ```bash
   sqlite3 abz_sales_portal.db
   ```

2. **Add the product_name column**:
   ```sql
   ALTER TABLE quotationitems ADD COLUMN product_name VARCHAR(255);
   ```

3. **Make product_id nullable** (SQLite limitation requires table recreation):
   ```sql
   -- Create new table structure
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
   );
   
   -- Copy existing data
   INSERT INTO quotationitems_new 
   SELECT id, quotation_id, product_id, product_name, quantity, unit_price, total_price, notes, created_at
   FROM quotationitems;
   
   -- Drop old table and rename new one
   DROP TABLE quotationitems;
   ALTER TABLE quotationitems_new RENAME TO quotationitems;
   ```

4. **Populate product names for existing items**:
   ```sql
   UPDATE quotationitems 
   SET product_name = (
       SELECT name 
       FROM products 
       WHERE products.id = quotationitems.product_id
   )
   WHERE product_id IS NOT NULL;
   ```

## Verification

After running the migration, verify the changes:

```sql
-- Check table structure
PRAGMA table_info(quotationitems);

-- Check that product_name is populated
SELECT COUNT(*) FROM quotationitems WHERE product_name IS NOT NULL;

-- Check that manual items can be created
INSERT INTO quotationitems (quotation_id, product_name, quantity, unit_price, total_price, notes)
VALUES (1, 'Custom Service', 1, 100.00, 100.00, 'Manual item test');
```

## Rollback

If you need to rollback the migration:

1. **Run the migration script** and choose option 2
2. **Or manually reverse the changes**:
   ```sql
   -- Remove product_name column
   ALTER TABLE quotationitems DROP COLUMN product_name;
   
   -- Make product_id NOT NULL again (requires table recreation)
   ```

## What Happens After Migration

### Before Migration
- Quotations could only contain products from your catalog
- All quotation items required a valid `product_id`
- No support for custom services or one-time items

### After Migration
- Quotations can contain both regular products and manual items
- Manual items have `product_id = NULL` and `product_name` filled
- Regular items have `product_id` and `product_name` from products table
- Full backward compatibility maintained

## Benefits

1. **Flexibility**: Add custom services, installation fees, delivery charges
2. **Custom Pricing**: Set specific prices for special orders
3. **Service Packages**: Combine products with services
4. **One-time Items**: Handle items not worth adding to catalog
5. **Professional Quotations**: Include all costs in one document

## Troubleshooting

### Common Issues

1. **"Database file not found"**
   - Ensure you're running the script from the correct directory
   - Check that `abz_sales_portal.db` exists

2. **"Permission denied"**
   - Ensure you have write access to the database file
   - Try running as administrator if needed

3. **"Foreign key constraint failed"**
   - Check that all quotation_id values reference valid quotations
   - Verify that product_id values reference valid products

### Getting Help

If you encounter issues:

1. **Check the error messages** carefully
2. **Verify database file location** and permissions
3. **Ensure no other processes** are using the database
4. **Check available disk space** for temporary tables

## Support

For additional support or questions about this migration, please refer to your system documentation or contact your development team.

---

**Note**: Always backup your database before running migrations. This migration is designed to be safe and reversible, but it's good practice to have a backup.
