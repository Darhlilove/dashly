#!/usr/bin/env python3
"""
Generate demo CSV data and create DuckDB database for Dashly
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import duckdb
import os

def generate_sales_data():
    """Generate sample sales data"""
    np.random.seed(42)
    
    # Date range for last 12 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    dates = pd.date_range(start_date, end_date, freq='D')
    
    regions = ['North', 'South', 'East', 'West', 'Central']
    products = ['Product A', 'Product B', 'Product C', 'Product D', 'Product E']
    
    data = []
    for date in dates:
        for region in regions:
            for product in products:
                # Generate realistic sales data with some seasonality
                base_sales = np.random.normal(1000, 200)
                seasonal_factor = 1 + 0.3 * np.sin(2 * np.pi * date.timetuple().tm_yday / 365)
                sales = max(0, base_sales * seasonal_factor)
                
                data.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'region': region,
                    'product': product,
                    'revenue': round(sales, 2),
                    'units_sold': int(sales / 50),
                    'customer_count': int(sales / 100)
                })
    
    return pd.DataFrame(data)

def generate_customer_data():
    """Generate sample customer data"""
    np.random.seed(123)
    
    customer_segments = ['Enterprise', 'SMB', 'Startup', 'Individual']
    industries = ['Technology', 'Healthcare', 'Finance', 'Retail', 'Manufacturing']
    
    data = []
    for i in range(1000):
        data.append({
            'customer_id': f'CUST_{i+1:04d}',
            'segment': np.random.choice(customer_segments),
            'industry': np.random.choice(industries),
            'signup_date': (datetime.now() - timedelta(days=np.random.randint(1, 730))).strftime('%Y-%m-%d'),
            'monthly_spend': round(np.random.lognormal(6, 1), 2),
            'satisfaction_score': round(np.random.normal(4.2, 0.8), 1)
        })
    
    return pd.DataFrame(data)

def create_database():
    """Create DuckDB database and load CSV data"""
    os.makedirs('data', exist_ok=True)
    
    # Generate and save CSV files
    print("Generating sales data...")
    sales_df = generate_sales_data()
    sales_df.to_csv('data/sales_data.csv', index=False)
    
    print("Generating customer data...")
    customer_df = generate_customer_data()
    customer_df.to_csv('data/customer_data.csv', index=False)
    
    # Create DuckDB database
    print("Creating DuckDB database...")
    conn = duckdb.connect('data/dashly.db')
    
    # Load CSV files into DuckDB
    conn.execute("CREATE TABLE sales_data AS SELECT * FROM read_csv_auto('data/sales_data.csv')")
    conn.execute("CREATE TABLE customer_data AS SELECT * FROM read_csv_auto('data/customer_data.csv')")
    
    # Create some useful views
    conn.execute("""
        CREATE VIEW monthly_revenue AS 
        SELECT 
            strftime(date, '%Y-%m') as month,
            region,
            SUM(revenue) as total_revenue,
            SUM(units_sold) as total_units
        FROM sales_data 
        GROUP BY strftime(date, '%Y-%m'), region
        ORDER BY month, region
    """)
    
    conn.execute("""
        CREATE VIEW customer_metrics AS
        SELECT 
            segment,
            industry,
            COUNT(*) as customer_count,
            AVG(monthly_spend) as avg_monthly_spend,
            AVG(satisfaction_score) as avg_satisfaction
        FROM customer_data
        GROUP BY segment, industry
    """)
    
    conn.close()
    print("Database created successfully!")
    print("Tables created: sales_data, customer_data")
    print("Views created: monthly_revenue, customer_metrics")

if __name__ == "__main__":
    create_database()