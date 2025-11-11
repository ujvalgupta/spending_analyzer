"""
GPay PDF Parser
Extracts transaction data from GPay statement PDFs
"""

import pdfplumber
import pandas as pd
from datetime import datetime
import re
import streamlit as st


def parse_gpay_pdf(pdf_file, debug=False):
    """
    Parse GPay PDF and extract transaction data
    
    Args:
        pdf_file: File-like object or bytes from Streamlit file uploader
        debug: If True, show debug information
        
    Returns:
        pandas DataFrame with columns: date, description, amount, type
    """
    transactions = []
    debug_info = []
    
    try:
        # Reset file pointer if it's a file-like object
        if hasattr(pdf_file, 'seek'):
            pdf_file.seek(0)
        
        # Open PDF with pdfplumber
        with pdfplumber.open(pdf_file) as pdf:
            total_pages = len(pdf.pages)
            if debug:
                debug_info.append(f"Total pages: {total_pages}")
            
            # Iterate through all pages
            for page_num, page in enumerate(pdf.pages, 1):
                if debug:
                    debug_info.append(f"\n--- Processing page {page_num} ---")
                
                # Try to extract tables first (most common format)
                tables = page.extract_tables()
                
                if tables:
                    if debug:
                        debug_info.append(f"Found {len(tables)} table(s) on page {page_num}")
                    
                    for table_idx, table in enumerate(tables):
                        if debug:
                            debug_info.append(f"  Table {table_idx + 1} has {len(table)} rows")
                            # Show first few rows for debugging
                            if len(table) > 0:
                                sample_rows = table[:3]
                                for idx, sample_row in enumerate(sample_rows):
                                    debug_info.append(f"    Row {idx}: {sample_row}")
                        
                        # Process table rows
                        for row_idx, row in enumerate(table):
                            if row and len(row) >= 2:
                                # Clean row data
                                row_data = [cell.strip() if cell else "" for cell in row]
                                
                                # Skip if all cells are empty or very short
                                if not any(cell and len(cell) > 2 for cell in row_data):
                                    continue
                                
                                # Skip header-like rows
                                if any(header in ' '.join(row_data).lower() for header in 
                                       ['date', 'description', 'amount', 'transaction', 'debit', 'credit', 'balance']):
                                    if row_idx == 0 or row_idx < 3:  # Likely header row
                                        continue
                                
                                transaction = _parse_table_row(row_data, debug)
                                if transaction:
                                    transactions.append(transaction)
                                    if debug and len(transactions) <= 5:
                                        debug_info.append(f"  ✓ Parsed transaction: {transaction}")
                
                # Always try text extraction as well (some PDFs have text but not tables)
                text = page.extract_text()
                if text:
                    if debug:
                        if not tables:
                            debug_info.append(f"  No tables found, extracting text (length: {len(text)} chars)")
                        # Show sample of extracted text (first 500 chars)
                        sample_text = text[:500].replace('\n', ' ').strip()
                        debug_info.append(f"  Sample text: {sample_text}...")
                    
                    # Try to parse text-based transactions
                    text_transactions = _parse_text_transactions(text, debug)
                    if text_transactions:
                        if debug:
                            debug_info.append(f"  Found {len(text_transactions)} text transactions")
                        # Avoid duplicates
                        for tx in text_transactions:
                            # Simple duplicate check
                            is_duplicate = any(
                                tx.get('date') == existing.get('date') and
                                abs(tx.get('amount', 0) - existing.get('amount', 0)) < 0.01 and
                                tx.get('description', '')[:20] == existing.get('description', '')[:20]
                                for existing in transactions
                            )
                            if not is_duplicate:
                                transactions.append(tx)
                                if debug and len(transactions) <= 5:
                                    debug_info.append(f"  ✓ Parsed text transaction: {tx}")
                    elif debug:
                        debug_info.append(f"  No transactions found in text extraction")
        
        # Show debug info if requested
        if debug and debug_info:
            st.info("Debug Info:\n" + "\n".join(debug_info))
        
        # Convert to DataFrame
        if transactions:
            df = pd.DataFrame(transactions)
            # Clean and format data
            df = _clean_dataframe(df)
            if debug:
                st.success(f"Successfully parsed {len(df)} transactions!")
            return df
        else:
            if debug:
                st.warning("No transactions found. Debug info above shows what was extracted.")
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=['date', 'description', 'amount', 'type'])
            
    except Exception as e:
        error_msg = str(e).lower()
        if debug:
            st.error(f"Error details: {str(e)}")
            if debug_info:
                st.code("\n".join(debug_info))
        if 'pdf' in error_msg or 'syntax' in error_msg or 'invalid' in error_msg:
            raise Exception(f"Invalid PDF file. Please ensure you're uploading a valid GPay PDF: {str(e)}")
        else:
            raise Exception(f"Error parsing PDF: {str(e)}. Please check if the PDF format is correct.")


def _parse_table_row(row_data, debug=False):
    """
    Parse a single table row into a transaction dictionary
    """
    # Skip header rows and empty rows
    if not row_data or len(row_data) < 2:
        return None
    
    # Filter out empty cells
    row_data = [cell for cell in row_data if cell and str(cell).strip()]
    if len(row_data) < 2:
        return None
    
    transaction = {}
    
    # More flexible date patterns
    date_patterns = [
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',  # DD-MM-YYYY, DD/MM/YYYY
        r'(\d{1,2}\s+\w{3}\s+\d{4})',  # DD MMM YYYY
        r'(\d{1,2}\s+\w+\s+\d{4})',  # DD Month YYYY
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',  # YYYY-MM-DD
    ]
    
    # More flexible amount patterns (order matters - try more specific first)
    amount_patterns = [
        r'[₹Rs$]?\s*-?\d{1,3}(?:[,]\d{2,3})*(?:[.]\d{1,2})?',  # With currency, commas, optional decimals
        r'[₹Rs$]\s*\d{1,3}(?:[,]\d{2,3})*(?:[.]\d{1,2})?',  # Currency symbol with space
        r'\(?\d{1,3}(?:[,]\d{2,3})*(?:[.]\d{1,2})?\)?',  # Amount in parentheses (negative)
        r'-?\d{1,3}(?:[,]\d{2,3})*(?:[.]\d{1,2})?',  # Amount without currency symbol
        r'[₹Rs$]?\s*-?\d+[.,]\d{2}',  # Standard amount with decimals
        r'[₹Rs$]?\s*-?\d+',  # Amount without decimals (integers)
    ]
    
    # Try to identify date and amount in each cell
    for cell in row_data:
        if not cell:
            continue
        
        cell_str = str(cell).strip()
        
        # Check if it's a date
        if 'date' not in transaction:
            for pattern in date_patterns:
                date_match = re.search(pattern, cell_str, re.IGNORECASE)
                if date_match:
                    try:
                        date_str = date_match.group(1)
                        parsed_date = _parse_date(date_str)
                        # Validate date is reasonable (not too far in future/past)
                        if parsed_date.year >= 2020 and parsed_date.year <= 2030:
                            transaction['date'] = parsed_date
                            break
                    except:
                        continue
        
        # Check if it's an amount
        if 'amount' not in transaction:
            # Check for negative indicators first
            is_negative = cell_str.strip().startswith('-') or cell_str.strip().startswith('(') or 'debit' in cell_str.lower()
            
            for pattern in amount_patterns:
                # Try matching on cleaned string (without commas for pattern matching)
                test_str = cell_str.replace(',', '')
                amount_match = re.search(pattern, test_str)
                if amount_match:
                    try:
                        amount_str = amount_match.group(0)
                        # Remove currency symbols, spaces, commas, and parentheses
                        amount_str = re.sub(r'[₹Rs$,\s()]', '', amount_str).strip()
                        
                        # Check if negative (could be in original string or amount_str)
                        if amount_str.startswith('-') or cell_str.strip().startswith('('):
                            is_negative = True
                            amount_str = amount_str.replace('-', '')
                        
                        if amount_str:
                            try:
                                amount_value = float(amount_str)
                                if is_negative:
                                    amount_value = -amount_value
                                # Only accept reasonable amounts (between 0.01 and 10 million)
                                if 0.01 <= abs(amount_value) <= 10000000:
                                    transaction['amount'] = amount_value
                                    break
                            except ValueError:
                                continue
                    except Exception as e:
                        continue
        
        # Check for transaction type keywords
        cell_lower = cell_str.lower()
        type_keywords = {
            'debit': ['paid', 'sent', 'debit', 'withdrawal', 'deducted', 'spent'],
            'credit': ['received', 'credit', 'deposit', 'credited', 'added', 'refund']
        }
        if 'type' not in transaction:
            for tx_type, keywords in type_keywords.items():
                if any(keyword in cell_lower for keyword in keywords):
                    transaction['type'] = tx_type.capitalize()
                    break
    
    # Description is usually the longest non-empty cell that's not date/amount/type
    descriptions = []
    for cell in row_data:
        if not cell:
            continue
        cell_str = str(cell).strip()
        
        # Skip if it's a date
        is_date = any(re.search(pattern, cell_str, re.IGNORECASE) for pattern in date_patterns)
        # Skip if it's an amount
        is_amount = any(re.search(pattern, cell_str.replace(',', '')) for pattern in amount_patterns)
        # Skip if it's a type indicator
        is_type = any(keyword in cell_str.lower() for keywords in type_keywords.values() for keyword in keywords)
        # Skip very short cells or common headers
        is_header = any(header in cell_str.lower() for header in 
                       ['date', 'description', 'amount', 'transaction', 'balance', 'total'])
        
        if not is_date and not is_amount and not is_type and not is_header and len(cell_str) > 3:
            descriptions.append(cell_str)
    
    if descriptions:
        # Use the longest description, or combine if multiple
        transaction['description'] = ' '.join(descriptions) if len(descriptions) > 1 else max(descriptions, key=len)
    
    # Set default type if not found (based on amount sign)
    if 'type' not in transaction:
        if 'amount' in transaction:
            transaction['type'] = 'Debit' if transaction['amount'] < 0 else 'Credit'
        else:
            transaction['type'] = 'Debit'  # Default
    
    # Only return if we have essential fields
    if 'date' in transaction and 'amount' in transaction:
        # Description is optional but preferred
        if 'description' not in transaction or not transaction['description']:
            transaction['description'] = 'Unknown Transaction'
        return transaction
    
    return None


def _parse_text_transactions(text, debug=False):
    """
    Parse transactions from plain text (fallback method)
    Handles GPay format: "01Oct,2025 PaidtoShiv Kumar ₹85 08:38AM UPITransactionID:..."
    Also handles multiple transactions on the same line
    """
    transactions = []
    
    # GPay-specific date pattern: DD MMM, YYYY (e.g., "01Oct,2025")
    # This matches: 1-2 digits, 3 letters (month), comma, 4 digits (year)
    date_pattern = r'(\d{1,2}[A-Za-z]{3},\d{4})'
    
    # Amount pattern: ₹ symbol followed by number with optional decimals and Indian comma notation
    # Matches: ₹85, ₹314.43, ₹1,64,148.10
    amount_pattern = r'₹\s*(\d{1,3}(?:[,]\d{2,3})*(?:[.]\d{1,2})?)'
    
    # Transaction type keywords
    debit_keywords = ['paidto', 'selftransferto', 'paid']
    credit_keywords = ['receivedfrom', 'received', 'credited']
    
    # Split text into lines first
    lines = text.split('\n')
    
    # Process each line - but also split by date pattern in case multiple transactions are on same line
    for line in lines:
        if not line.strip() or len(line.strip()) < 15:
            continue
        
        # Skip header lines and summary lines
        line_lower = line.lower()
        skip_headers = [
            'date&time', 'transactiondetails', 'amount', 
            'transaction statement', 'statementperiod', 'sent received',
            'contact', '8081100105'
        ]
        if any(header in line_lower for header in skip_headers):
            continue
        
        # Skip lines that don't look like transactions (no date pattern)
        if not re.search(date_pattern, line, re.IGNORECASE):
            continue
        
        # Split line by date pattern to handle multiple transactions on same line
        # Find all date matches
        date_matches = list(re.finditer(date_pattern, line, re.IGNORECASE))
        
        if not date_matches:
            continue
        
        # Process each transaction (each date match represents a potential transaction start)
        for i, date_match in enumerate(date_matches):
            # Get the text for this transaction
            start_pos = date_match.start()
            # End position is either the next date match or end of line
            if i + 1 < len(date_matches):
                end_pos = date_matches[i + 1].start()
            else:
                end_pos = len(line)
            
            transaction_text = line[start_pos:end_pos].strip()
            
            if not transaction_text or len(transaction_text) < 10:
                continue
            
            # Now parse this transaction
            transaction = _parse_single_transaction(transaction_text, date_pattern, amount_pattern, 
                                                   debit_keywords, credit_keywords, debug)
            if transaction:
                transactions.append(transaction)
    
    return transactions


def _parse_single_transaction(transaction_text, date_pattern, amount_pattern, 
                             debit_keywords, credit_keywords, debug=False):
    """
    Parse a single transaction from text
    """
    transaction = {}
    line_lower = transaction_text.lower()
    
    # Find date (should be at the start)
    date_match = re.search(date_pattern, transaction_text, re.IGNORECASE)
    if date_match:
        try:
            date_str = date_match.group(1).strip()
            parsed_date = _parse_date(date_str)
            if parsed_date.year >= 2020 and parsed_date.year <= 2030:
                transaction['date'] = parsed_date
            else:
                return None  # Skip if date is invalid
        except Exception as e:
            return None
    else:
        return None  # Skip if no date found
    
    # Find amount (₹ symbol followed by number)
    amount_match = re.search(amount_pattern, transaction_text)
    if amount_match:
        try:
            amount_str = amount_match.group(1).replace(',', '')  # Remove Indian comma notation
            amount_value = float(amount_str)
            if 0.01 <= abs(amount_value) <= 10000000:
                transaction['amount'] = amount_value
            else:
                return None  # Skip if amount is unreasonable
        except Exception as e:
            return None
    else:
        return None  # Skip if no amount found
    
    # Determine transaction type based on keywords
    if any(keyword in line_lower for keyword in debit_keywords):
        transaction['type'] = 'Debit'
    elif any(keyword in line_lower for keyword in credit_keywords):
        transaction['type'] = 'Credit'
    else:
        # Default to Debit for GPay transactions (most payments are debits)
        transaction['type'] = 'Debit'
    
    # Extract description
    desc = transaction_text
    
    # Remove date
    if date_match:
        desc = desc.replace(date_match.group(0), '', 1).strip()
    
    # Remove amount (₹XX)
    if amount_match:
        desc = desc.replace(amount_match.group(0), '', 1).strip()
    
    # Remove time pattern (HH:MM AM/PM) - usually comes after amount
    desc = re.sub(r'\d{1,2}:\d{2}\s*(AM|PM)', '', desc, flags=re.IGNORECASE).strip()
    
    # Remove UPI Transaction ID (UPITransactionID:XXXXXXXXX)
    desc = re.sub(r'UPITransactionID:\s*\d+', '', desc, flags=re.IGNORECASE).strip()
    
    # Remove bank info (PaidbyBankNameAccountNumber)
    desc = re.sub(r'Paidby[A-Za-z]+\d+', '', desc, flags=re.IGNORECASE).strip()
    
    # Clean up multiple spaces
    desc = re.sub(r'\s+', ' ', desc).strip()
    
    # Remove leading/trailing special characters
    desc = desc.strip(' ,-')
    
    # If we have a valid description, use it
    if desc and len(desc) > 1:
        transaction['description'] = desc
    else:
        # Fallback: try to extract from original line
        # Get text between date and amount
        date_end = date_match.end()
        amount_start = amount_match.start()
        if amount_start > date_end:
            desc = transaction_text[date_end:amount_start].strip()
            desc = re.sub(r'\s+', ' ', desc).strip()
            if desc and len(desc) > 1:
                transaction['description'] = desc
            else:
                transaction['description'] = 'Transaction'
        else:
            transaction['description'] = 'Transaction'
    
    return transaction


def _parse_date(date_str):
    """
    Parse date string into datetime object
    Handles multiple date formats including Indian formats
    """
    # Clean the date string
    date_str = date_str.strip()
    
    # Handle GPay format first: "01Oct,2025" (day + month abbreviation + comma + year)
    # Python's strptime doesn't handle comma directly, so we need to parse it manually
    gpay_pattern = r'(\d{1,2})([A-Za-z]{3}),(\d{4})'
    gpay_match = re.match(gpay_pattern, date_str, re.IGNORECASE)
    if gpay_match:
        try:
            day = int(gpay_match.group(1))
            month_str = gpay_match.group(2).capitalize()
            year = int(gpay_match.group(3))
            
            # Map month abbreviations to numbers
            months = {
                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
            }
            
            if month_str in months:
                return datetime(year, months[month_str], day)
        except:
            pass
    
    # Common formats (Indian formats first, including GPay format)
    formats = [
        '%d %b, %Y',     # 01 Oct, 2025
        '%d%b %Y',       # 01Oct 2025
        '%d %b %Y',      # 01 Oct 2025
        '%d-%m-%Y',      # 25-12-2024
        '%d/%m/%Y',      # 25/12/2024
        '%d.%m.%Y',      # 25.12.2024
        '%d-%m-%y',      # 25-12-24
        '%d/%m/%y',      # 25/12/24
        '%d.%m.%y',      # 25.12.24
        '%Y-%m-%d',      # 2024-12-25
        '%Y/%m/%d',      # 2024/12/25
        '%d %B %Y',      # 25 December 2024
        '%d-%b-%Y',      # 25-Dec-2024
        '%d-%B-%Y',      # 25-December-2024
        '%b %d, %Y',     # Dec 25, 2024
        '%B %d, %Y',     # December 25, 2024
        '%m/%d/%Y',      # 12/25/2024 (US format)
        '%m-%d-%Y',      # 12-25-2024 (US format)
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    
    # If all formats fail, try to parse flexibly
    try:
        # Extract numbers from date string
        numbers = re.findall(r'\d+', date_str)
        if len(numbers) >= 3:
            num1, num2, year = int(numbers[0]), int(numbers[1]), int(numbers[2])
            if year < 100:
                year += 2000
            
            # Try Indian format: DD-MM-YY (if first num <= 31 and second <= 12)
            if 1 <= num1 <= 31 and 1 <= num2 <= 12:
                return datetime(year, num2, num1)
            # Try US format: MM-DD-YY (if first num <= 12 and second <= 31)
            elif 1 <= num1 <= 12 and 1 <= num2 <= 31:
                return datetime(year, num1, num2)
    except Exception as e:
        pass
    
    # Return today's date as fallback (but log warning in debug mode)
    return datetime.now()


def _clean_dataframe(df):
    """
    Clean and standardize the DataFrame
    """
    if df.empty:
        return df
    
    # Ensure required columns exist
    required_columns = ['date', 'description', 'amount', 'type']
    for col in required_columns:
        if col not in df.columns:
            if col == 'date':
                df[col] = datetime.now()
            elif col == 'description':
                df[col] = 'Unknown'
            elif col == 'amount':
                df[col] = 0.0
            elif col == 'type':
                df[col] = 'Debit'
    
    # Remove duplicates
    df = df.drop_duplicates()
    
    # Sort by date
    df = df.sort_values('date', ascending=False)
    
    # Reset index
    df = df.reset_index(drop=True)
    
    return df

