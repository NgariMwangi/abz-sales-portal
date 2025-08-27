# 🗄️ Database Migration: Add product_name to OrderItem

This migration adds a new `product_name` field to the `orderitems` table to support both regular products and manual items in orders.

## 🎯 **What This Migration Does**

1. **Adds `product_name` field** to the `orderitems` table
2. **Populates existing records** with appropriate product names
3. **Enables manual items** to store custom product names
4. **Maintains backward compatibility** with existing orders

## 📋 **Prerequisites**

- ✅ Updated `app/models.py` with the new `product_name` field
- ✅ Updated `app/services.py` to use the new field
- ✅ Database file accessible (usually `app.db` or `instance/app.db`)
- ✅ Python 3.6+ installed

## 🚀 **Running the Migration**

### **Step 1: Backup Your Database (Recommended)**
```bash
cp app.db app.db.backup
# or
cp instance/app.db instance/app.db.backup
```

### **Step 2: Run the Migration Script**
```bash
python migrate_add_product_name.py
```

### **Step 3: Verify the Migration**
The script will show:
- ✅ Connection status
- ✅ Column addition confirmation
- ✅ Data population summary
- ✅ Migration statistics

## 🔄 **Rollback (If Needed)**

If you need to undo the migration:
```bash
python migrate_add_product_name.py --rollback
```

**⚠️ Warning:** Rollback will remove the `product_name` field and all data in it!

## 📊 **What Happens During Migration**

1. **Column Addition**: Adds `product_name VARCHAR(255)` to `orderitems` table
2. **Data Population**: 
   - Regular products: Gets name from `products` table
   - Manual items: Sets default name "Manual Item"
3. **Verification**: Confirms the column was added successfully

## 🎯 **After Migration**

1. **Restart your Flask application**
2. **Test creating orders** with both regular and manual items
3. **Verify product names** are properly stored and displayed
4. **Check existing orders** still display correctly

## 🔍 **Verification Commands**

You can verify the migration worked by checking your database:

```sql
-- Check if the column exists
PRAGMA table_info(orderitems);

-- See some sample data
SELECT id, productid, product_name, quantity FROM orderitems LIMIT 10;

-- Check manual items
SELECT * FROM orderitems WHERE productid IS NULL;
```

## ❌ **Troubleshooting**

### **Database Not Found**
- Check if you're in the correct directory
- Verify the database file path in the migration script
- Common paths: `app.db`, `instance/app.db`, or `database.db`

### **Permission Errors**
- Ensure you have read/write access to the database file
- Try running with appropriate permissions

### **SQLite Errors**
- Check if the database file is corrupted
- Verify SQLite version compatibility
- Try opening the database with a SQLite browser

## 📝 **Manual Migration (Alternative)**

If the script doesn't work, you can run the SQL commands manually:

```sql
-- Add the column
ALTER TABLE orderitems ADD COLUMN product_name VARCHAR(255);

-- Update existing regular products
UPDATE orderitems 
SET product_name = (
    SELECT name 
    FROM products 
    WHERE products.id = orderitems.productid
)
WHERE productid IS NOT NULL;

-- Set default for manual items
UPDATE orderitems 
SET product_name = 'Manual Item'
WHERE productid IS NULL AND product_name IS NULL;
```

## 🎉 **Success Indicators**

The migration is successful when:
- ✅ Script runs without errors
- ✅ `product_name` column appears in table structure
- ✅ Existing orders still display correctly
- ✅ New orders can be created with manual items
- ✅ Product names are properly stored and retrieved

## 🆘 **Need Help?**

If you encounter issues:
1. Check the error messages carefully
2. Verify your database file path
3. Ensure you have the latest code changes
4. Try the manual SQL approach
5. Check the Flask application logs

---

**Migration completed successfully! 🎉**

Your system now supports both regular products and manual items with proper product name storage.
