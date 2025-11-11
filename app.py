"""
GPay Spending Analyzer
Streamlit web application for analyzing GPay transaction PDFs
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from pdf_parser import parse_gpay_pdf
from analyzer import analyze_spending

# Page configuration
st.set_page_config(
    page_title="GPay Spending Analyzer",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .stMetric {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    # Header
    st.markdown('<h1 class="main-header">💰 GPay Spending Analyzer</h1>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("📤 Upload PDF")
        st.markdown("Upload your GPay statement PDF to analyze your spending patterns.")
        
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            help="Upload your GPay transaction history PDF"
        )
        
        if uploaded_file is not None:
            st.success("PDF uploaded successfully!")
            st.info(f"File: {uploaded_file.name}")
            st.markdown("---")
            st.session_state.debug_mode = st.checkbox("Enable Debug Mode", 
                                                      value=st.session_state.get('debug_mode', False),
                                                      help="Show detailed parsing information")
        else:
            st.info("Please upload a GPay PDF file to get started.")
            st.session_state.debug_mode = False
            st.markdown("---")
            st.markdown("### How to get your GPay statement:")
            st.markdown("""
            1. Open Google Pay app
            2. Go to your profile
            3. Select 'Bank account' or 'Transactions'
            4. Export transactions as PDF
            5. Upload the PDF here
            """)
    
    # Main content
    if uploaded_file is not None:
        try:
            # Parse PDF
            with st.spinner("Parsing PDF and analyzing transactions..."):
                # Reset file pointer
                uploaded_file.seek(0)
                debug_mode = st.session_state.get('debug_mode', False)
                df = parse_gpay_pdf(uploaded_file, debug=debug_mode)
            
            if df.empty:
                st.error("⚠️ No transactions found in the PDF. Please check if the PDF format is correct.")
                st.info("💡 Tip: Make sure you're uploading a GPay transaction history PDF with actual transaction data.")
                
                if not debug_mode:
                    st.warning("🔍 **Enable Debug Mode** in the sidebar to see what the parser is extracting from your PDF. This will help identify the issue.")
                
                st.markdown("""
                **Possible issues:**
                - PDF might be empty or corrupted
                - PDF format might not be recognized
                - Transactions might not be in the expected format
                - PDF might be password protected or scanned image
                
                **Try:**
                - Enable Debug Mode to see what's being extracted
                - Export a different date range from GPay
                - Ensure the PDF contains transaction details (not just summary)
                - Check if the PDF opens correctly in a PDF viewer
                - Make sure the PDF is from GPay transaction history (not bank statement)
                """)
                return
            
            # Analyze spending
            insights = analyze_spending(df)
            
            # Display success message
            st.success(f"✅ Successfully parsed {len(df)} transactions!")
            
            # Key Metrics
            st.markdown("## 📊 Key Metrics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="Total Spending",
                    value=f"₹{insights['total_spending']:,.2f}",
                    delta=None
                )
            
            with col2:
                st.metric(
                    label="Total Income",
                    value=f"₹{insights['total_income']:,.2f}",
                    delta=None
                )
            
            with col3:
                net_balance_color = "normal" if insights['net_balance'] >= 0 else "inverse"
                st.metric(
                    label="Net Balance",
                    value=f"₹{insights['net_balance']:,.2f}",
                    delta=None
                )
            
            with col4:
                st.metric(
                    label="Transactions",
                    value=insights['transaction_count'],
                    delta=None
                )
            
            st.markdown("---")
            
            # Date Range
            if insights['date_range']:
                st.info(f"📅 Date Range: {insights['date_range']['start']} to {insights['date_range']['end']} ({insights['date_range']['days']} days)")
            
            # Charts Row 1
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🥧 Spending by Category")
                if not insights['spending_by_category'].empty:
                    fig_pie = px.pie(
                        insights['spending_by_category'],
                        values='amount',
                        names='category',
                        hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    fig_pie.update_layout(height=400, showlegend=True)
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("No spending data available for categories.")
            
            with col2:
                st.markdown("### 📈 Monthly Spending Trends")
                if not insights['monthly_spending'].empty:
                    fig_line = px.line(
                        insights['monthly_spending'],
                        x='month',
                        y='amount',
                        markers=True,
                        color_discrete_sequence=['#1f77b4']
                    )
                    fig_line.update_layout(
                        height=400,
                        xaxis_title="Month",
                        yaxis_title="Amount (₹)",
                        hovermode='x unified'
                    )
                    fig_line.update_traces(line=dict(width=3))
                    st.plotly_chart(fig_line, use_container_width=True)
                else:
                    st.info("No monthly spending data available.")
            
            # Charts Row 2
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🏪 Top Merchants by Spending")
                if not insights['top_merchants'].empty:
                    top_merchants_display = insights['top_merchants'].head(10).copy()
                    fig_bar = px.bar(
                        top_merchants_display,
                        x='total_amount',
                        y='merchant',
                        orientation='h',
                        color='total_amount',
                        color_continuous_scale='Blues',
                        labels={'total_amount': 'Amount (₹)', 'merchant': 'Merchant'}
                    )
                    fig_bar.update_layout(
                        height=400,
                        yaxis={'categoryorder': 'total ascending'},
                        showlegend=False
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.info("No merchant data available.")
            
            with col2:
                st.markdown("### 📊 Category Breakdown")
                if not insights['spending_by_category'].empty:
                    fig_bar_cat = px.bar(
                        insights['spending_by_category'],
                        x='category',
                        y='amount',
                        color='amount',
                        color_continuous_scale='Greens',
                        labels={'amount': 'Amount (₹)', 'category': 'Category'}
                    )
                    fig_bar_cat.update_layout(
                        height=400,
                        xaxis_tickangle=-45,
                        showlegend=False
                    )
                    st.plotly_chart(fig_bar_cat, use_container_width=True)
                else:
                    st.info("No category data available.")
            
            # Additional Insights
            st.markdown("---")
            st.markdown("## 💡 Additional Insights")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    label="Average Transaction",
                    value=f"₹{insights['average_transaction']:,.2f}"
                )
            
            with col2:
                if insights['largest_transaction']:
                    st.metric(
                        label="Largest Transaction",
                        value=f"₹{insights['largest_transaction']['amount']:,.2f}"
                    )
                    st.caption(f"{insights['largest_transaction']['description'][:30]}...")
                else:
                    st.metric(label="Largest Transaction", value="N/A")
            
            with col3:
                if insights['date_range']:
                    avg_daily = insights['total_spending'] / insights['date_range']['days'] if insights['date_range']['days'] > 0 else 0
                    st.metric(
                        label="Average Daily Spending",
                        value=f"₹{avg_daily:,.2f}"
                    )
            
            # Transaction Details
            st.markdown("---")
            st.markdown("## 📋 Transaction Details")
            
            # Filter options
            col1, col2, col3 = st.columns(3)
            with col1:
                show_type = st.selectbox("Filter by Type", ["All", "Debit", "Credit"])
            with col2:
                categories = ['All'] + list(insights['spending_by_category']['category'].unique()) if not insights['spending_by_category'].empty else ['All']
                show_category = st.selectbox("Filter by Category", categories)
            with col3:
                sort_by = st.selectbox("Sort by", ["Date", "Amount", "Description"])
            
            # Filter data
            if show_type == "Debit":
                display_df = insights.get('debits_df', df[df['type'] == 'Debit'].copy())
            elif show_type == "Credit":
                display_df = insights.get('credits_df', df[df['type'] == 'Credit'].copy())
            else:  # All
                display_df = df.copy()
            
            if show_category != "All" and 'category' in display_df.columns:
                display_df = display_df[display_df['category'] == show_category]
            
            # Sort
            if sort_by == "Date":
                display_df = display_df.sort_values('date', ascending=False)
            elif sort_by == "Amount":
                display_df = display_df.sort_values('amount', ascending=False)
            else:
                display_df = display_df.sort_values('description')
            
            # Display table
            if not display_df.empty:
                # Format columns for display
                display_columns = ['date', 'description', 'amount']
                if 'category' in display_df.columns:
                    display_columns.append('category')
                
                display_df_display = display_df[display_columns].copy()
                display_df_display['date'] = pd.to_datetime(display_df_display['date']).dt.strftime('%Y-%m-%d')
                display_df_display['amount'] = display_df_display['amount'].abs().apply(lambda x: f"₹{x:,.2f}")
                
                # Rename columns
                column_mapping = {
                    'date': 'Date',
                    'description': 'Description',
                    'amount': 'Amount',
                    'category': 'Category'
                }
                display_df_display = display_df_display.rename(columns=column_mapping)
                
                st.dataframe(display_df_display, use_container_width=True, height=400)
                
                # Download button
                csv = display_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Transactions as CSV",
                    data=csv,
                    file_name="gpay_transactions.csv",
                    mime="text/csv"
                )
            else:
                st.info("No transactions match the selected filters.")
        
        except Exception as e:
            st.error(f"❌ Error processing PDF: {str(e)}")
            st.info("💡 Please make sure you're uploading a valid GPay transaction PDF.")
            with st.expander("Show detailed error"):
                st.exception(e)
    
    else:
        # Welcome message
        st.markdown("""
        ## Welcome to GPay Spending Analyzer! 👋
        
        This tool helps you analyze your spending patterns from GPay transaction statements.
        
        ### Features:
        - 📊 **Spending Analysis** - View total spending and income
        - 🥧 **Category Breakdown** - See where your money goes
        - 📈 **Monthly Trends** - Track spending over time
        - 🏪 **Top Merchants** - Identify your most frequent merchants
        - 📋 **Transaction Details** - View and filter all transactions
        
        ### Getting Started:
        1. Upload your GPay statement PDF using the sidebar
        2. Wait for the analysis to complete
        3. Explore your spending insights!
        
        ### Privacy:
        - Your PDF is processed in memory and not stored
        - All processing happens locally in your browser session
        - No data is saved or transmitted to external servers
        """)
        
        # Sample screenshot or instructions
        st.markdown("---")
        st.markdown("### 📱 How to Export GPay Statement:")
        st.markdown("""
        1. Open **Google Pay** app on your phone
        2. Tap on your **profile picture** (top right)
        3. Go to **Bank account** or **Transactions**
        4. Look for **Export** or **Download statement** option
        5. Select the date range and export as **PDF**
        6. Upload the PDF file here
        """)

if __name__ == "__main__":
    main()

