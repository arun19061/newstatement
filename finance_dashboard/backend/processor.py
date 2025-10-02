import pandas as pd
import pdfplumber
import json
import re
from datetime import datetime
import os
import io

class FinancialProcessor:
    def __init__(self):
        self.chart_of_accounts = {
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

    def process_file_in_memory(self, file_content, filename):
        """Processes file from in-memory content based on file type."""
        if filename.lower().endswith('.csv'):
            return self.process_csv(file_content)
        elif filename.lower().endswith(('.xlsx', '.xls')):
            return self.process_excel(file_content)
        elif filename.lower().endswith('.pdf'):
            return self.process_pdf(file_content)
        elif filename.lower().endswith('.json'):
            return self.process_json(file_content)
        else:
            raise ValueError(f"Unsupported file format: {filename}")

    def process_csv(self, file_content):
        """Processes CSV file from in-memory content."""
        df = pd.read_csv(io.StringIO(file_content.decode('utf-8')))
        transactions = []
        for _, row in df.iterrows():
            transaction = self.extract_transaction(row.to_dict())
            if transaction:
                transactions.append(transaction)
        return transactions

    def process_excel(self, file_content):
        """Processes Excel file from in-memory content."""
        df = pd.read_excel(io.BytesIO(file_content))
        transactions = []
        for _, row in df.iterrows():
            transaction = self.extract_transaction(row.to_dict())
            if transaction:
                transactions.append(transaction)
        return transactions

    def process_pdf(self, file_content):
        """Processes PDF file from in-memory content."""
        transactions = []
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    lines = text.split('\n')
                    for line in lines:
                        transaction = self.parse_pdf_line(line)
                        if transaction:
                            transactions.append(transaction)
        return transactions

    def process_json(self, file_content):
        """Processes JSON file from in-memory content."""
        data = json.loads(file_content)
        transactions = []
        if isinstance(data, list):
            for item in data:
                transaction = self.extract_transaction(item)
                if transaction:
                    transactions.append(transaction)
        return transactions

    def extract_transaction(self, row):
        """Extracts and formats transaction data from a dictionary row."""
        amount = 0
        for key, value in row.items():
            if key and value is not None:
                key_lower = str(key).lower()
                if any(term in key_lower for term in ['amount', 'amt', 'value']):
                    amount = self.parse_amount(value)
                    break
                elif any(term in key_lower for term in ['debit', 'withdrawal', 'dr']):
                    amount = -abs(self.parse_amount(value))
                    break
                elif any(term in key_lower for term in ['credit', 'deposit', 'cr']):
                    amount = abs(self.parse_amount(value))
                    break
        if amount == 0:
            return None

        description = next((str(value) for key, value in row.items() if key and any(term in str(key).lower() for term in ['description', 'desc', 'particulars', 'narration', 'details'])), "Unknown")
        date = next((str(value) for key, value in row.items() if key and 'date' in str(key).lower()), "")
        
        category = self.categorize_transaction(description)

        return {
            'date': date,
            'description': description,
            'amount': amount,
            'category': category,
            'type': 'income' if amount > 0 else 'expense'
        }

    def parse_pdf_line(self, line):
        """Parses a single line from a PDF bank statement using regex."""
        patterns = [
            r'(\d{1,2}/\d{1,2}/\d{2,4})\s+(.*?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})',
            r'(\d{1,2}-\d{1,2}-\d{2,4})\s+(.*?)\s+(-?[\d,]+\.\d{2})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                date = match.group(1)
                description = match.group(2).strip()
                amount_str = match.group(3).replace(',', '')
                try:
                    amount = float(amount_str)
                    category = self.categorize_transaction(description)
                    return {
                        'date': date,
                        'description': description,
                        'amount': amount,
                        'category': category,
                        'type': 'income' if amount > 0 else 'expense'
                    }
                except ValueError:
                    continue
        return None

    def parse_amount(self, value):
        """Parses a string or number value to a float amount."""
        if pd.isna(value) or value is None:
            return 0
        try:
            if isinstance(value, (int, float)):
                return float(value)
            cleaned = str(value).replace(',', '').replace('₹', '').replace('$', '').strip()
            return float(cleaned) if cleaned else 0
        except (ValueError, TypeError):
            return 0

    def categorize_transaction(self, description):
        """Categorizes a transaction based on its description."""
        desc_lower = str(description).lower()
        for main_cat, sub_cats in self.chart_of_accounts.items():
            for sub_cat, keywords in sub_cats.items():
                if any(keyword in desc_lower for keyword in keywords):
                    return f"{main_cat}_{sub_cat}"
        return "uncategorized"
    
    def generate_reports(self, transactions):
        """Generates financial reports from a list of transactions."""
        # Income Statement
        income_breakdown = {}
        expense_breakdown = {}
        for transaction in transactions:
            category, amount = transaction['category'], transaction['amount']
            if amount > 0:
                income_breakdown[category] = income_breakdown.get(category, 0) + amount
            else:
                expense_breakdown[category] = expense_breakdown.get(category, 0) + abs(amount)
        
        total_income = sum(income_breakdown.values())
        total_expenses = sum(expense_breakdown.values())
        net_income = total_income - total_expenses
        
        # Balance Sheet (simplified)
        total_assets = total_income * 0.7
        total_liabilities = total_expenses * 0.3
        total_equity = total_assets - total_liabilities
        
        # Cash Flow (simplified)
        operating_cash = net_income
        investing_cash = total_income * 0.1
        financing_cash = total_expenses * 0.1
        net_cash_flow = operating_cash + investing_cash + financing_cash
        
        return {
            'transactions': transactions,
            'income_statement': {
                'total_income': total_income,
                'total_expenses': total_expenses,
                'net_income': net_income,
                'breakdown': {**income_breakdown, **{f"expense_{k}": -v for k, v in expense_breakdown.items()}}
            },
            'balance_sheet': {
                'total_assets': total_assets,
                'total_liabilities': total_liabilities,
                'total_equity': total_equity
            },
            'cash_flow': {
                'operating_activities': operating_cash,
                'investing_activities': investing_cash,
                'financing_activities': financing_cash,
                'net_cash_flow': net_cash_flow
            }
        }