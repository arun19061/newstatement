import os
import pandas as pd
import zipfile
import json
import io
from datetime import datetime
import shutil

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from processor import FinancialProcessor

# Initialize FastAPI app
app = FastAPI()

# Initialize processor
processor = FinancialProcessor()
@app.post("/process")
async def process_files(files: list[UploadFile] = File(...)):
    return processor.process_files(files)

# Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Configuration
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Chart of accounts for categorization
CHART_OF_ACCOUNTS = {
    "income": {
        "salary": ["salary", "payroll", "wages"],
        "business": ["freelance", "consulting", "client", "project"],
        "investment": ["dividend", "interest", "return", "yield"],
        "other_income": ["refund", "reimbursement", "gift"]
    },
    "expenses": {
        "housing": ["rent", "mortgage", "emi", "house", "apartment"],
        "utilities": ["electric", "water", "bill", "utility", "internet", "mobile"],
        "food": ["grocery", "restaurant", "food", "dining", "supermarket"],
        "transport": ["fuel", "petrol", "uber", "ola", "transport", "bus", "train"],
        "healthcare": ["medical", "hospital", "doctor", "pharmacy", "medicine"],
        "entertainment": ["movie", "netflix", "prime", "entertainment", "game"],
        "shopping": ["shopping", "mall", "amazon", "flipkart", "purchase"]
    }
}

def parse_amount(value):
    """Parse amount from various formats"""
    if value is None or value == '':
        return 0
    try:
        if isinstance(value, (int, float)):
            return float(value)
        cleaned = str(value).replace(',', '').replace('₹', '').replace('$', '').replace('€', '').strip()
        return float(cleaned) if cleaned else 0
    except (ValueError, TypeError):
        return 0

def categorize_transaction(description):
    """Categorize transaction based on description"""
    desc_lower = str(description).lower()
    for main_cat, sub_cats in CHART_OF_ACCOUNTS.items():
        for sub_cat, keywords in sub_cats.items():
            if any(keyword in desc_lower for keyword in keywords):
                return f"{main_cat}_{sub_cat}"
    return "uncategorized"

def extract_transaction(row):
    """Extract transaction data from row"""
    amount = 0
    for key, value in row.items():
        if key and value is not None:
            key_lower = str(key).lower()
            if any(term in key_lower for term in ['amount', 'amt', 'value']):
                amount = parse_amount(value)
                break
            elif any(term in key_lower for term in ['debit', 'withdrawal', 'dr']):
                amount = -abs(parse_amount(value))
                break
            elif any(term in key_lower for term in ['credit', 'deposit', 'cr']):
                amount = abs(parse_amount(value))
                break
    if amount == 0:
        return None
    description = next((str(value) for key, value in row.items() if key and any(term in str(key).lower() for term in ['description', 'desc', 'particulars', 'narration', 'details'])), "Unknown Transaction")
    date = next((str(value) for key, value in row.items() if key and 'date' in str(key).lower()), "")
    category = categorize_transaction(description)
    return {
        'date': date,
        'description': description,
        'amount': amount,
        'category': category,
        'type': 'income' if amount > 0 else 'expense'
    }

def process_csv(file_content):
    """Process CSV file from in-memory content"""
    df = pd.read_csv(io.StringIO(file_content.decode('utf-8')))
    return [t for _, row in df.iterrows() if (t := extract_transaction(row.to_dict()))]

def process_excel(file_content):
    """Process Excel file from in-memory content"""
    df = pd.read_excel(io.BytesIO(file_content))
    return [t for _, row in df.iterrows() if (t := extract_transaction(row.to_dict()))]

def generate_reports(transactions):
    """Generate financial reports from transactions"""
    income_breakdown = {}
    expense_breakdown = {}
    for transaction in transactions:
        category, amount = transaction['category'], transaction['amount']
        if amount > 0:
            income_breakdown[category] = income_breakdown.get(category, 0) + amount
        else:
            expense_breakdown[category] = expense_breakdown.get(category, 0) + abs(amount)
    total_income, total_expenses = sum(income_breakdown.values()), sum(expense_breakdown.values())
    net_income = total_income - total_expenses
    total_assets, total_liabilities = total_income * 0.7, total_expenses * 0.3
    total_equity = total_assets - total_liabilities
    operating_cash, investing_cash, financing_cash = net_income, total_income * 0.1, total_expenses * 0.1
    net_cash_flow = operating_cash + investing_cash + financing_cash
    return {
        'transactions': transactions,
        'income_statement': {'total_income': total_income, 'total_expenses': total_expenses, 'net_income': net_income, 'breakdown': {**income_breakdown, **{f"expense_{k}": -v for k, v in expense_breakdown.items()}}},
        'balance_sheet': {'total_assets': total_assets, 'total_liabilities': total_liabilities, 'total_equity': total_equity},
        'cash_flow': {'operating_activities': operating_cash, 'investing_activities': investing_cash, 'financing_activities': financing_cash, 'net_cash_flow': net_cash_flow}
    }

def generate_summary_text(reports):
    """Generate text summary of reports"""
    income_stmt, balance_sheet, cash_flow = reports.get('income_statement', {}), reports.get('balance_sheet', {}), reports.get('cash_flow', {})
    summary = f"FINANCIAL REPORTS SUMMARY\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nINCOME STATEMENT\n================\nTotal Income: ${income_stmt.get('total_income', 0):,.2f}\nTotal Expenses: ${income_stmt.get('total_expenses', 0):,.2f}\nNet Income: ${income_stmt.get('net_income', 0):,.2f}\n\nBALANCE SHEET\n=============\nTotal Assets: ${balance_sheet.get('total_assets', 0):,.2f}\nTotal Liabilities: ${balance_sheet.get('total_liabilities', 0):,.2f}\nTotal Equity: ${balance_sheet.get('total_equity', 0):,.2f}\n\nCASH FLOW STATEMENT\n===================\nNet Cash Flow: ${cash_flow.get('net_cash_flow', 0):,.2f}\n\nTRANSACTION SUMMARY\n===================\nTotal Transactions: {len(reports.get('transactions', []))}\n"
    return summary

def create_excel_report(reports):
    """Create Excel report in memory"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if 'transactions' in reports:
            pd.DataFrame(reports['transactions']).to_excel(writer, sheet_name='Transactions', index=False)
        income_data = [{'Category': k, 'Amount': v} for k, v in reports.get('income_statement', {}).get('breakdown', {}).items()]
        pd.DataFrame(income_data).to_excel(writer, sheet_name='Income Statement', index=False)
    output.seek(0)
    return output

@app.get("/health", response_class=JSONResponse)
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Finance API is running"}

@app.get("/")
def root():
    return {"message": "Finance Dashboard API"}

@app.get("/favicon.ico")
def favicon():
    return JSONResponse(content={}, status_code=204)

@app.post("/process")
async def process_files(files: list[UploadFile] = File(...)):
    """Process uploaded files"""
    all_transactions = []
    processed_files_status = []
    for file in files:
        if not file.filename:
            continue
        try:
            file_content = await file.read()
            transactions = []
            if file.filename.lower().endswith('.csv'):
                transactions = process_csv(file_content)
            elif file.filename.lower().endswith(('.xlsx', '.xls')):
                transactions = process_excel(file_content)
            else:
                processed_files_status.append({'filename': file.filename, 'status': 'error', 'error': 'Unsupported file format'})
                continue
            all_transactions.extend(transactions)
            processed_files_status.append({'filename': file.filename, 'transactions_count': len(transactions), 'status': 'success'})
        except Exception as e:
            processed_files_status.append({'filename': file.filename, 'status': 'error', 'error': str(e)})

    if not all_transactions:
        raise HTTPException(status_code=400, detail="No valid transactions found in any file")
    
    reports = generate_reports(all_transactions)
    return {
        "status": "success",
        "processed_files": processed_files_status,
        "summary": {
            "total_transactions": len(all_transactions),
            "total_income": reports['income_statement']['total_income'],
            "total_expenses": reports['income_statement']['total_expenses'],
            "net_income": reports['income_statement']['net_income']
        },
        "reports": reports
    }

@app.post("/download-reports")
async def download_reports(reports: dict):
    """Download reports as ZIP file"""
    if not reports or 'reports' not in reports:
        raise HTTPException(status_code=400, detail="No reports data provided")
    reports_data = reports['reports']
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr('financial_data.json', json.dumps(reports_data, indent=2))
        if 'transactions' in reports_data:
            df = pd.DataFrame(reports_data['transactions'])
            zipf.writestr('transactions.csv', df.to_csv(index=False))
        summary_text = generate_summary_text(reports_data)
        zipf.writestr('financial_summary.txt', summary_text)
        if 'transactions' in reports_data:
            excel_buffer = create_excel_report(reports_data)
            zipf.writestr('financial_reports.xlsx', excel_buffer.getvalue())
    zip_buffer.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return FileResponse(zip_buffer, media_type='application/zip', filename=f'financial_reports_{timestamp}.zip')

if __name__ == '__main__':
    import uvicorn
    print("Starting FastAPI server on http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)