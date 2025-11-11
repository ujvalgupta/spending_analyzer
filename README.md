# GPay Spending Analyzer 💰

A web-based application to analyze your Google Pay transaction statements and gain insights into your spending patterns.

## Features

- 📊 **Spending Analysis** - View total spending, income, and net balance
- 🥧 **Category Breakdown** - Automatically categorize transactions and see spending by category
- 📈 **Monthly Trends** - Track your spending patterns over time
- 🏪 **Top Merchants** - Identify your most frequent merchants and spending amounts
- 📋 **Transaction Details** - View, filter, and download all transactions
- 💡 **Additional Insights** - Average transaction size, largest transaction, daily spending averages

## Tech Stack

- **Streamlit** - Web UI framework
- **Python 3.8+** - Main language
- **pdfplumber** - PDF parsing
- **pandas** - Data processing
- **plotly** - Interactive visualizations

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. Clone this repository:
```bash
git clone <repository-url>
cd Spending_Analyzer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Local Development

1. Run the Streamlit app:
```bash
streamlit run app.py
```

2. Open your browser and navigate to `http://localhost:8501`

3. Upload your GPay statement PDF using the sidebar

4. View your spending insights!

### How to Get Your GPay Statement

1. Open **Google Pay** app on your phone
2. Tap on your **profile picture** (top right)
3. Go to **Bank account** or **Transactions**
4. Look for **Export** or **Download statement** option
5. Select the date range and export as **PDF**
6. Upload the PDF file in the app

## Deployment

### Deploy to Streamlit Cloud (Free)

1. **Push to GitHub**
   - Create a new repository on GitHub
   - Push your code to the repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Deploy to Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with your GitHub account
   - Click **"New app"**
   - Select your repository and branch (main)
   - Set the main file path to `app.py`
   - Click **"Deploy"**
   - Your app will be available at `https://<app-name>.streamlit.app`

3. **Share Your App**
   - Once deployed, you'll get a public URL
   - Share this URL with anyone who wants to use the app
   - The app updates automatically when you push changes to GitHub

## Project Structure

```
Spending_Analyzer/
├── app.py                 # Main Streamlit application
├── pdf_parser.py          # GPay PDF parsing logic
├── analyzer.py            # Data analysis and insights
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore file
└── README.md             # This file
```

## Privacy

- Your PDF files are processed in memory and not stored
- All processing happens in your browser session (local) or on Streamlit Cloud servers
- No transaction data is saved permanently
- When deployed on Streamlit Cloud, files are processed in memory and discarded after analysis

## How It Works

1. **PDF Parsing**: Uses `pdfplumber` to extract tables and text from GPay PDF statements
2. **Data Processing**: Cleans and structures the transaction data into a pandas DataFrame
3. **Categorization**: Automatically categorizes transactions based on merchant names and keywords
4. **Analysis**: Calculates various metrics and insights from the transaction data
5. **Visualization**: Creates interactive charts and graphs using Plotly

## Categories

The app automatically categorizes transactions into:
- Food & Dining
- Transport
- Shopping
- Entertainment
- Bills & Utilities
- Healthcare
- Education
- Banking & Finance
- Travel
- Recharge & DTH
- Investments
- Other

## Troubleshooting

### PDF Not Parsing Correctly

- **Enable Debug Mode**: Check the "Enable Debug Mode" checkbox in the sidebar to see detailed parsing information
- Make sure you're uploading a valid GPay transaction PDF (not a bank statement)
- Check if the PDF contains transaction data (not just account summary)
- Try exporting a different date range from GPay
- Verify the PDF opens correctly in a PDF viewer

### No Transactions Found

- **Enable Debug Mode**: This will show you exactly what the parser is extracting from your PDF
- Verify that the PDF contains transaction history with dates and amounts
- Check if the PDF format matches GPay's standard export format
- Try re-exporting the statement from GPay
- Ensure the PDF is not password protected or a scanned image
- Check the debug output to see if tables or text are being found

### Debug Mode

The app includes a debug mode that shows:
- Number of pages in the PDF
- Number of tables found on each page
- Sample rows from tables
- Extracted text samples
- Parsed transactions
- Any errors during parsing

This is very helpful for troubleshooting parsing issues.

### App Not Loading on Streamlit Cloud

- Check that `requirements.txt` includes all dependencies
- Verify that `app.py` is in the root directory
- Check the Streamlit Cloud logs for error messages

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Support

For issues or questions, please open an issue on GitHub.

---

Made with ❤️ for better financial awareness

