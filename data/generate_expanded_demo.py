#!/usr/bin/env python3
"""
Generate expanded demo_sales.csv with at least 100 rows
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_expanded_demo_sales():
    """Generate expanded demo sales data matching original structure"""
    np.random.seed(42)
    random.seed(42)
    
    # Original structure: date,region,product,sales_amount,customer_email,phone
    regions = ['North', 'South', 'East', 'West', 'Central']
    products = ['Widget A', 'Widget B', 'Widget C', 'Widget D', 'Widget E']
    
    # Generate realistic names and domains
    first_names = ['John', 'Jane', 'Bob', 'Alice', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Henry',
                   'Ivy', 'Jack', 'Kate', 'Liam', 'Mia', 'Noah', 'Olivia', 'Paul', 'Quinn', 'Ruby',
                   'Sam', 'Tina', 'Uma', 'Victor', 'Wendy', 'Xavier', 'Yara', 'Zoe', 'Alex', 'Blake']
    
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez',
                  'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin',
                  'Lee', 'Perez', 'Thompson', 'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson']
    
    domains = ['email.com', 'gmail.com', 'yahoo.com', 'outlook.com', 'company.com', 'business.net', 'corp.org']
    
    data = []
    
    # Generate 150 rows to ensure we have well over 100
    start_date = datetime(2023, 1, 1)
    
    for i in range(150):
        # Generate date within the last year
        days_offset = random.randint(0, 365)
        transaction_date = start_date + timedelta(days=days_offset)
        
        # Random selections
        region = random.choice(regions)
        product = random.choice(products)
        
        # Generate realistic sales amounts with some variation by product
        base_amounts = {'Widget A': 1200, 'Widget B': 900, 'Widget C': 750, 'Widget D': 1100, 'Widget E': 850}
        base_amount = base_amounts[product]
        sales_amount = round(base_amount + random.normalvariate(0, 200), 2)
        sales_amount = max(100, sales_amount)  # Ensure minimum amount
        
        # Generate customer info
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        email = f"{first_name.lower()}.{last_name.lower()}@{random.choice(domains)}"
        
        # Generate phone number
        area_code = random.randint(200, 999)
        exchange = random.randint(200, 999)
        number = random.randint(1000, 9999)
        phone = f"{area_code}-{exchange:03d}-{number:04d}"
        
        data.append({
            'date': transaction_date.strftime('%Y-%m-%d'),
            'region': region,
            'product': product,
            'sales_amount': sales_amount,
            'customer_email': email,
            'phone': phone
        })
    
    return pd.DataFrame(data)

if __name__ == "__main__":
    print("Generating expanded demo sales data...")
    df = generate_expanded_demo_sales()
    df.to_csv('data/demo_sales.csv', index=False)
    print(f"Generated {len(df)} rows of demo sales data")
    print("Updated data/demo_sales.csv")