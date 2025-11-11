"""
Spending Analyzer
Analyzes transaction data and generates insights
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re


# Category mapping based on keywords
CATEGORY_KEYWORDS = {
    'Food & Dining': [
        'swiggy', 'zomato', 'uber eats', 'food', 'restaurant', 'cafe', 'pizza',
        'burger', 'dominos', 'mcdonald', 'kfc', 'starbucks', 'coffee', 'tea',
        'bakery', 'grocery', 'bigbasket', 'grofers', 'dunzo', 'zepto'
    ],
    'Transport': [
        'uber', 'ola', 'rapido', 'metro', 'bus', 'train', 'railway', 'flight',
        'airline', 'taxi', 'cab', 'fuel', 'petrol', 'diesel', 'parking', 'toll'
    ],
    'Shopping': [
        'amazon', 'flipkart', 'myntra', 'nykaa', 'shopping', 'store', 'mall',
        'fashion', 'clothes', 'apparel', 'electronics', 'phone', 'mobile'
    ],
    'Entertainment': [
        'netflix', 'prime', 'spotify', 'youtube', 'movie', 'cinema', 'theatre',
        'game', 'gaming', 'playstation', 'xbox', 'book', 'music'
    ],
    'Bills & Utilities': [
        'electricity', 'water', 'gas', 'phone', 'internet', 'wifi', 'broadband',
        'mobile bill', 'postpaid', 'prepaid', 'jio', 'airtel', 'vodafone',
        'utility', 'bill payment'
    ],
    'Healthcare': [
        'hospital', 'clinic', 'pharmacy', 'medicine', 'medical', 'doctor',
        'apollo', 'medplus', '1mg', 'practo', 'health', 'insurance'
    ],
    'Education': [
        'school', 'college', 'university', 'tuition', 'course', 'education',
        'book', 'stationery', 'exam', 'fee'
    ],
    'Banking & Finance': [
        'bank', 'atm', 'withdrawal', 'deposit', 'loan', 'emi', 'credit card',
        'interest', 'charges', 'fee', 'transfer', 'upi'
    ],
    'Travel': [
        'hotel', 'booking', 'travel', 'trip', 'vacation', 'tour', 'tourism',
        'make my trip', 'goibibo', 'oyo', 'airbnb'
    ],
    'Recharge & DTH': [
        'recharge', 'dth', 'tv', 'cable', 'dish', 'tata sky', 'airtel digital',
        'jio', 'vodafone idea'
    ],
    'Investments': [
        'mutual fund', 'sip', 'stocks', 'equity', 'investment', 'fd', 'rd',
        'gold', 'crypto', 'bitcoin'
    ],
    'Other': []  # Default category
}


def categorize_transaction(description):
    """
    Categorize a transaction based on its description
    
    Args:
        description: Transaction description string
        
    Returns:
        Category name (string)
    """
    if not description or pd.isna(description):
        return 'Other'
    
    desc_lower = str(description).lower()
    
    # Check each category
    for category, keywords in CATEGORY_KEYWORDS.items():
        if category == 'Other':
            continue
        for keyword in keywords:
            if keyword in desc_lower:
                return category
    
    return 'Other'


def analyze_spending(df):
    """
    Analyze spending data and generate insights
    
    Args:
        df: DataFrame with columns: date, description, amount, type
        
    Returns:
        Dictionary with various metrics and insights
    """
    if df.empty:
        return {
            'total_spending': 0,
            'total_income': 0,
            'net_balance': 0,
            'transaction_count': 0,
            'spending_by_category': pd.DataFrame(),
            'monthly_spending': pd.DataFrame(),
            'top_merchants': pd.DataFrame(),
            'average_transaction': 0,
            'largest_transaction': None,
            'date_range': None
        }
    
    # Make a copy to avoid modifying original
    df = df.copy()
    
    # Add category column to main dataframe
    if 'category' not in df.columns:
        df['category'] = df['description'].apply(categorize_transaction)
    
    # Separate debits and credits
    # In GPay, debits are usually negative amounts or marked as 'Debit'
    if 'type' in df.columns:
        debits = df[df['type'] == 'Debit'].copy()
        credits = df[df['type'] == 'Credit'].copy()
    else:
        # If no type column, use amount sign to determine
        debits = df[df['amount'] < 0].copy()
        credits = df[df['amount'] > 0].copy()
        debits['type'] = 'Debit'
        credits['type'] = 'Credit'
    
    # Handle amount signs - make all amounts positive for analysis
    if not debits.empty:
        debits['amount'] = debits['amount'].abs()
        if 'category' not in debits.columns:
            debits['category'] = debits['description'].apply(categorize_transaction)
    if not credits.empty:
        credits['amount'] = credits['amount'].abs()
        if 'category' not in credits.columns:
            credits['category'] = credits['description'].apply(categorize_transaction)
    
    # Calculate totals
    total_spending = debits['amount'].sum() if not debits.empty else 0
    total_income = credits['amount'].sum() if not credits.empty else 0
    net_balance = total_income - total_spending
    transaction_count = len(df)
    
    # Spending by category
    if not debits.empty:
        spending_by_category = debits.groupby('category')['amount'].sum().sort_values(ascending=False)
        spending_by_category = spending_by_category.reset_index()
        spending_by_category.columns = ['category', 'amount']
    else:
        spending_by_category = pd.DataFrame(columns=['category', 'amount'])
    
    # Monthly spending trends
    if not debits.empty:
        debits['month'] = pd.to_datetime(debits['date']).dt.to_period('M')
        monthly_spending = debits.groupby('month')['amount'].sum().reset_index()
        monthly_spending['month'] = monthly_spending['month'].astype(str)
        monthly_spending.columns = ['month', 'amount']
    else:
        monthly_spending = pd.DataFrame(columns=['month', 'amount'])
    
    # Top merchants (by frequency and amount)
    if not debits.empty:
        merchant_stats = debits.groupby('description').agg({
            'amount': ['sum', 'count', 'mean']
        }).reset_index()
        merchant_stats.columns = ['merchant', 'total_amount', 'count', 'avg_amount']
        merchant_stats = merchant_stats.sort_values('total_amount', ascending=False).head(10)
    else:
        merchant_stats = pd.DataFrame(columns=['merchant', 'total_amount', 'count', 'avg_amount'])
    
    # Average transaction size
    average_transaction = debits['amount'].mean() if not debits.empty else 0
    
    # Largest transaction
    if not debits.empty:
        largest_idx = debits['amount'].idxmax()
        largest_transaction = {
            'description': debits.loc[largest_idx, 'description'],
            'amount': debits.loc[largest_idx, 'amount'],
            'date': debits.loc[largest_idx, 'date'],
            'category': debits.loc[largest_idx, 'category']
        }
    else:
        largest_transaction = None
    
    # Date range
    if not df.empty:
        min_date = pd.to_datetime(df['date']).min()
        max_date = pd.to_datetime(df['date']).max()
        date_range = {
            'start': min_date.strftime('%Y-%m-%d'),
            'end': max_date.strftime('%Y-%m-%d'),
            'days': (max_date - min_date).days + 1
        }
    else:
        date_range = None
    
    return {
        'total_spending': round(total_spending, 2),
        'total_income': round(total_income, 2),
        'net_balance': round(net_balance, 2),
        'transaction_count': transaction_count,
        'spending_by_category': spending_by_category,
        'monthly_spending': monthly_spending,
        'top_merchants': merchant_stats,
        'average_transaction': round(average_transaction, 2),
        'largest_transaction': largest_transaction,
        'date_range': date_range,
        'debits_df': debits,
        'credits_df': credits
    }


def get_spending_trends(df, period='monthly'):
    """
    Get spending trends over time
    
    Args:
        df: DataFrame with transaction data
        period: 'daily', 'weekly', or 'monthly'
        
    Returns:
        DataFrame with trends
    """
    if df.empty:
        return pd.DataFrame()
    
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    
    # Filter debits only
    debits = df[df['type'] == 'Debit'].copy()
    if debits.empty:
        return pd.DataFrame()
    
    debits['amount'] = debits['amount'].abs()
    
    if period == 'daily':
        debits['period'] = debits['date'].dt.date
    elif period == 'weekly':
        debits['period'] = debits['date'].dt.to_period('W')
    else:  # monthly
        debits['period'] = debits['date'].dt.to_period('M')
    
    trends = debits.groupby('period')['amount'].sum().reset_index()
    trends['period'] = trends['period'].astype(str)
    trends.columns = ['period', 'amount']
    
    return trends

