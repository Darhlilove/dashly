#!/usr/bin/env python3
"""
Demo data generation script for dashly CSV upload API.
Generates realistic sales data and loads it into DuckDB.
"""

import os
import csv
import random
import duckdb
from datetime import datetime, timedelta
from pathlib import Path


def create_directory_structure():
    """Create necessary directory structure if missing."""
    directories = ['data', 'scripts']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ Directory '{directory}' ready")


def generate_sales_data(num_rows=500):
    """Generate realistic sales data with 500 sample rows."""
    
    # Sample data for realistic generation
    products = [
        "Laptop Pro", "Wireless Mouse", "Mechanical Keyboard", "Monitor 27\"", 
        "USB-C Hub", "Webcam HD", "Headphones", "Tablet", "Smartphone", 
        "Smart Watch", "Bluetooth Speaker", "Gaming Chair", "Desk Lamp",
        "External SSD", "Power Bank", "Wireless Charger", "Cable Set",
        "Docking Station", "Printer", "Scanner"
    ]
    
    categories = [
        "Electronics", "Computers", "Accessories", "Mobile", "Audio", 
        "Furniture", "Storage", "Networking", "Office"
    ]
    
    regions = [
        "North America", "Europe", "Asia Pacific", "Latin America", 
        "Middle East", "Africa"
    ]
    
    # Generate data
    sales_data = []
    start_date = datetime.now() - timedelta(days=365)
    
    for i in range(1, num_rows + 1):
        # Generate random date within last year
        random_days = random.randint(0, 365)
        sale_date = start_date + timedelta(days=random_days)
        
        # Select random product and category
        product = random.choice(products)
        category = random.choice(categories)
        region = random.choice(regions)
        
        # Generate realistic sales amounts based on product type
        base_price = random.uniform(50, 2000)
        quantity = random.randint(1, 10)
        sales_amount = round(base_price * quantity, 2)
        
        # Generate customer ID
        customer_id = random.randint(1000, 9999)
        
        row = {
            'id': i,
            'date': sale_date.strftime('%Y-%m-%d'),
            'product_name': product,
            'category': category,
            'region': region,
            'sales_amount': sales_amount,
            'quantity': quantity,
            'customer_id': customer_id
        }
        
        sales_data.append(row)
    
    return sales_data


def save_to_csv(data, filepath):
    """Save generated data to CSV file."""
    fieldnames = ['id', 'date', 'product_name', 'category', 'region', 
                  'sales_amount', 'quantity', 'customer_id']
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✓ Generated {len(data)} rows saved to {filepath}")


def load_into_duckdb(csv_path, db_path):
    """Load demo data into DuckDB as sales table."""
    try:
        # Connect to DuckDB
        conn = duckdb.connect(db_path)
        
        # Drop table if exists and create new one
        conn.execute("DROP TABLE IF EXISTS sales")
        
        # Create table and load CSV data
        create_table_sql = """
        CREATE TABLE sales AS 
        SELECT * FROM read_csv_auto(?)
        """
        
        conn.execute(create_table_sql, [csv_path])
        
        # Verify data was loaded
        result = conn.execute("SELECT COUNT(*) FROM sales").fetchone()
        row_count = result[0]
        
        # Get sample of data to verify structure
        sample = conn.execute("SELECT * FROM sales LIMIT 3").fetchall()
        columns = [desc[0] for desc in conn.description]
        
        conn.close()
        
        print(f"✓ Loaded {row_count} rows into DuckDB table 'sales'")
        print(f"✓ Table columns: {', '.join(columns)}")
        print("✓ Sample data:")
        for row in sample:
            print(f"  {dict(zip(columns, row))}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error loading data into DuckDB: {e}")
        return False


def main():
    """Main execution function."""
    print("🚀 Starting demo data generation...")
    
    # Create directory structure
    create_directory_structure()
    
    # Define file paths
    csv_path = "data/sales.csv"
    db_path = "data/demo.duckdb"
    
    # Generate sales data
    print(f"📊 Generating 500 sample sales records...")
    sales_data = generate_sales_data(500)
    
    # Save to CSV
    save_to_csv(sales_data, csv_path)
    
    # Load into DuckDB
    print(f"🗄️  Loading data into DuckDB at {db_path}...")
    success = load_into_duckdb(csv_path, db_path)
    
    if success:
        print("✅ Demo data generation completed successfully!")
        print(f"📁 CSV file: {csv_path}")
        print(f"🗄️  Database: {db_path}")
        print("🎯 Ready for API testing!")
    else:
        print("❌ Demo data generation failed!")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())