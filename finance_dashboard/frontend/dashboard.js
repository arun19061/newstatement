class FinanceDashboard {
    constructor() {
        this.selectedFiles = [];
        this.currentReports = null;
        this.apiBase = 'https://colloquially-nonpunishing-marylou.ngrok-free.dev'; 
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkBackendHealth();
    }

    setupEventListeners() {
        // File input
        document.getElementById('fileInput').addEventListener('change', (e) => {
            this.handleFileSelection(e.target.files);
        });

        // Process button
        document.getElementById('processBtn').addEventListener('click', () => {
            this.processFiles();
        });

        // Download button
        document.getElementById('downloadBtn').addEventListener('click', () => {
            this.downloadReports();
        });

        // Tabs
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Drag and drop
        const uploadArea = document.getElementById('uploadArea');
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('drag-over');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            this.handleFileSelection(e.dataTransfer.files);
        });
    }

    handleFileSelection(files) {
        this.selectedFiles = Array.from(files).slice(0, 5); // Limit to 5 files
        this.updateFileList();
    }

    updateFileList() {
        const fileList = document.getElementById('fileList');
        
        if (this.selectedFiles.length === 0) {
            fileList.innerHTML = '<p style="color: var(--muted); text-align: center;">No files selected</p>';
            return;
        }

        let html = '';
        this.selectedFiles.forEach((file, index) => {
            html += `
                <div class="file-item">
                    <div class="file-name">
                        <span>📄</span>
                        <span>${file.name}</span>
                    </div>
                    <div>${this.formatFileSize(file.size)}</div>
                </div>
            `;
        });

        fileList.innerHTML = html;
    }

    async processFiles() {
        if (this.selectedFiles.length === 0) {
            this.showStatus('Please select at least one file', 'error');
            return;
        }

        this.showStatus('Processing files...', 'info');
        document.getElementById('processBtn').disabled = true;
        document.getElementById('processBtn').innerHTML = '<div class="loading"></div> Processing...';

        const formData = new FormData();
        this.selectedFiles.forEach(file => {
            formData.append('files', file);
        });

        try {
            const response = await fetch(`${this.apiBase}/process`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                this.currentReports = result;
                this.showStatus(`✅ Successfully processed ${result.summary.total_transactions} transactions`, 'success');
                this.updateDashboard(result);
                document.getElementById('downloadBtn').disabled = false;
            } else {
                this.showStatus(`❌ Error: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showStatus(`❌ Network error: ${error.message}`, 'error');
        } finally {
            document.getElementById('processBtn').disabled = false;
            document.getElementById('processBtn').textContent = 'Generate Reports';
        }
    }

    updateDashboard(data) {
        this.updateKPIs(data.summary);
        this.updateOverview(data.reports);
        this.updateTransactions(data.reports.transactions);
        this.updateIncomeStatement(data.reports.income_statement);
        this.updateBalanceSheet(data.reports.balance_sheet);
        this.updateCashFlow(data.reports.cash_flow);
    }

    updateKPIs(summary) {
        document.getElementById('kpiIncome').textContent = this.formatCurrency(summary.total_income);
        document.getElementById('kpiExpense').textContent = this.formatCurrency(summary.total_expenses);
        document.getElementById('kpiSavings').textContent = this.formatCurrency(summary.net_income);
        document.getElementById('kpiCount').textContent = summary.total_transactions.toLocaleString();

        const savingsEl = document.getElementById('kpiSavings');
        savingsEl.className = `kpi-value ${summary.net_income >= 0 ? 'positive' : 'negative'}`;
    }

    updateOverview(reports) {
        const incomeStmt = reports.income_statement;
        const balanceSheet = reports.balance_sheet;
        const cashFlow = reports.cash_flow;

        const savingsRate = incomeStmt.total_income > 0 ? 
            (incomeStmt.net_income / incomeStmt.total_income) * 100 : 0;

        document.getElementById('overviewContent').innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-top: 20px;">
                <div class="card">
                    <h4 style="color: var(--muted); margin-bottom: 10px;">Financial Health</h4>
                    <div style="font-size: 32px; font-weight: bold; color: ${savingsRate >= 20 ? 'var(--success)' : savingsRate >= 0 ? 'var(--warning)' : 'var(--danger)'}">
                        ${savingsRate.toFixed(1)}%
                    </div>
                    <div style="color: var(--muted); font-size: 14px;">Savings Rate</div>
                </div>
                
                <div class="card">
                    <h4 style="color: var(--muted); margin-bottom: 10px;">Income vs Expenses</h4>
                    <div class="chart-container">
                        <div class="chart-bar">
                            <div class="chart-label">Income</div>
                            <div class="chart-bar-inner">
                                <div class="chart-bar-fill" style="width: ${(incomeStmt.total_income/(incomeStmt.total_income+incomeStmt.total_expenses))*100}%; background: var(--success);">
                                    ${this.formatCurrency(incomeStmt.total_income)}
                                </div>
                            </div>
                        </div>
                        <div class="chart-bar">
                            <div class="chart-label">Expenses</div>
                            <div class="chart-bar-inner">
                                <div class="chart-bar-fill" style="width: ${(incomeStmt.total_expenses/(incomeStmt.total_income+incomeStmt.total_expenses))*100}%; background: var(--danger);">
                                    ${this.formatCurrency(incomeStmt.total_expenses)}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h4 style="color: var(--muted); margin-bottom: 10px;">Quick Ratios</h4>
                    <div style="font-size: 14px;">
                        <div style="display: flex; justify-content: between; margin-bottom: 8px;">
                            <span>Profit Margin:</span>
                            <span style="color: ${incomeStmt.net_income >= 0 ? 'var(--success)' : 'var(--danger)'}">
                                ${((incomeStmt.net_income/incomeStmt.total_income)*100).toFixed(1)}%
                            </span>
                        </div>
                        <div style="display: flex; justify-content: between; margin-bottom: 8px;">
                            <span>Expense Ratio:</span>
                            <span>${((incomeStmt.total_expenses/incomeStmt.total_income)*100).toFixed(1)}%</span>
                        </div>
                        <div style="display: flex; justify-content: between;">
                            <span>Asset Coverage:</span>
                            <span>${((balanceSheet.total_assets/balanceSheet.total_liabilities) || 0).toFixed(1)}x</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    updateTransactions(transactions) {
        const container = document.getElementById('transactionList');
        const displayTransactions = transactions.slice(0, 50); // Show first 50

        if (displayTransactions.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: var(--muted);">No transactions</p>';
            return;
        }

        let html = `
            <div style="margin-bottom: 15px; color: var(--muted);">
                Showing ${displayTransactions.length} of ${transactions.length} transactions
            </div>
            <table>
                <tr>
                    <th>Date</th>
                    <th>Description</th>
                    <th>Category</th>
                    <th>Amount</th>
                </tr>
        `;

        displayTransactions.forEach(t => {
            html += `
                <tr>
                    <td>${t.date || 'N/A'}</td>
                    <td>${t.description}</td>
                    <td>${t.category}</td>
                    <td style="color: ${t.amount > 0 ? 'var(--success)' : 'var(--danger)'}; font-weight: 500;">
                        ${this.formatCurrency(t.amount)}
                    </td>
                </tr>
            `;
        });

        html += '</table>';
        container.innerHTML = html;
    }

    updateIncomeStatement(incomeStmt) {
        const container = document.getElementById('incomeStatement');
        
        let html = `
            <div style="display: grid; grid-template-columns: 1fr auto; gap: 10px; margin-top: 20px; max-width: 500px;">
                <div style="font-weight: 600; border-bottom: 1px solid var(--border); padding-bottom: 10px;">Category</div>
                <div style="font-weight: 600; border-bottom: 1px solid var(--border); padding-bottom: 10px; text-align: right;">Amount</div>
        `;

        // Add income items
        html += `<div style="grid-column: 1 / -1; font-weight: 600; margin-top: 15px; color: var(--success);">INCOME</div>`;
        
        Object.entries(incomeStmt.breakdown)
            .filter(([key]) => !key.startsWith('expense_'))
            .forEach(([category, amount]) => {
                html += `
                    <div>${this.formatCategoryName(category)}</div>
                    <div style="text-align: right; color: var(--success);">${this.formatCurrency(amount)}</div>
                `;
            });

        html += `
            <div style="border-top: 2px solid var(--border); padding-top: 10px; font-weight: 600;">Total Income</div>
            <div style="border-top: 2px solid var(--border); padding-top: 10px; text-align: right; font-weight: 600; color: var(--success);">
                ${this.formatCurrency(incomeStmt.total_income)}
            </div>
        `;

        // Add expense items
        html += `<div style="grid-column: 1 / -1; font-weight: 600; margin-top: 15px; color: var(--danger);">EXPENSES</div>`;
        
        Object.entries(incomeStmt.breakdown)
            .filter(([key]) => key.startsWith('expense_'))
            .forEach(([category, amount]) => {
                html += `
                    <div>${this.formatCategoryName(category.replace('expense_', ''))}</div>
                    <div style="text-align: right; color: var(--danger);">${this.formatCurrency(amount)}</div>
                `;
            });

        html += `
            <div style="border-top: 2px solid var(--border); padding-top: 10px; font-weight: 600;">Total Expenses</div>
            <div style="border-top: 2px solid var(--border); padding-top: 10px; text-align: right; font-weight: 600; color: var(--danger);">
                ${this.formatCurrency(incomeStmt.total_expenses)}
            </div>
            
            <div style="border-top: 2px solid var(--border); padding-top: 10px; font-weight: 600; grid-column: 1 / -1; margin-top: 10px;">NET INCOME</div>
            <div style="border-top: 2px solid var(--border); padding-top: 10px; text-align: right; font-weight: 600; color: ${incomeStmt.net_income >= 0 ? 'var(--success)' : 'var(--danger)'};">
                ${this.formatCurrency(incomeStmt.net_income)}
            </div>
        `;

        container.innerHTML = html;
    }

    updateBalanceSheet(balanceSheet) {
        const container = document.getElementById('balanceSheet');
        
        container.innerHTML = `
            <div style="display: grid; grid-template-columns: 1fr auto; gap: 10px; margin-top: 20px; max-width: 500px;">
                <div style="font-weight: 600; color: var(--success);">ASSETS</div>
                <div style="text-align: right; font-weight: 600; color: var(--success);">${this.formatCurrency(balanceSheet.total_assets)}</div>
                
                <div style="font-weight: 600; color: var(--danger); margin-top: 15px;">LIABILITIES</div>
                <div style="text-align: right; font-weight: 600; color: var(--danger);">${this.formatCurrency(balanceSheet.total_liabilities)}</div>
                
                <div style="font-weight: 600; color: var(--primary); margin-top: 15px;">EQUITY</div>
                <div style="text-align: right; font-weight: 600; color: var(--primary);">${this.formatCurrency(balanceSheet.total_equity)}</div>
                
                <div style="border-top: 2px solid var(--border); padding-top: 10px; font-weight: 600; margin-top: 15px;">TOTAL</div>
                <div style="border-top: 2px solid var(--border); padding-top: 10px; text-align: right; font-weight: 600;">
                    ${this.formatCurrency(balanceSheet.total_assets)}
                </div>
            </div>
        `;
    }

    updateCashFlow(cashFlow) {
        const container = document.getElementById('cashFlowStatement');
        
        container.innerHTML = `
            <div style="display: grid; grid-template-columns: 1fr auto; gap: 10px; margin-top: 20px; max-width: 500px;">
                <div>Operating Activities</div>
                <div style="text-align: right; color: ${cashFlow.operating_activities >= 0 ? 'var(--success)' : 'var(--danger)'};">
                    ${this.formatCurrency(cashFlow.operating_activities)}
                </div>
                
                <div>Investing Activities</div>
                <div style="text-align: right; color: ${cashFlow.investing_activities >= 0 ? 'var(--success)' : 'var(--danger)'};">
                    ${this.formatCurrency(cashFlow.investing_activities)}
                </div>
                
                <div>Financing Activities</div>
                <div style="text-align: right; color: ${cashFlow.financing_activities >= 0 ? 'var(--success)' : 'var(--danger)'};">
                    ${this.formatCurrency(cashFlow.financing_activities)}
                </div>
                
                <div style="border-top: 2px solid var(--border); padding-top: 10px; font-weight: 600; margin-top: 10px;">Net Cash Flow</div>
                <div style="border-top: 2px solid var(--border); padding-top: 10px; text-align: right; font-weight: 600; color: ${cashFlow.net_cash_flow >= 0 ? 'var(--success)' : 'var(--danger)'};">
                    ${this.formatCurrency(cashFlow.net_cash_flow)}
                </div>
            </div>
        `;
    }

    async downloadReports() {
        if (!this.currentReports) {
            this.showStatus('No reports available to download', 'error');
            return;
        }

        this.showStatus('Preparing download...', 'info');
        
        try {
            const response = await fetch(`${this.apiBase}/download-reports`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    reports: this.currentReports.reports
                })
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `financial_reports_${new Date().toISOString().split('T')[0]}.zip`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                this.showStatus('✅ Reports downloaded successfully!', 'success');
            } else {
                const error = await response.json();
                this.showStatus(`❌ Download failed: ${error.error}`, 'error');
            }
        } catch (error) {
            this.showStatus(`❌ Network error: ${error.message}`, 'error');
        }
    }

    async checkBackendHealth() {
        try {
            const response = await fetch(`${this.apiBase}/health`);
            if (response.ok) {
                console.log('Backend is healthy');
            } else {
                this.showStatus('⚠️ Backend server not responding', 'warning');
            }
        } catch (error) {
            this.showStatus('⚠️ Cannot connect to backend server. Make sure Flask is running on port 5000.', 'warning');
        }
    }

    switchTab(tabName) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        document.getElementById(tabName).classList.add('active');
    }

    showStatus(message, type) {
        // Remove existing status
        const existing = document.querySelector('.status');
        if (existing) existing.remove();

        const status = document.createElement('div');
        status.className = `status ${type}`;
        status.textContent = message;
        
        document.querySelector('.upload-area').after(status);
    }

    formatCurrency(amount) {
        return '$' + Math.abs(amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatCategoryName(category) {
        return category.split('_').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    }
}

// Initialize the dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    new FinanceDashboard();
});