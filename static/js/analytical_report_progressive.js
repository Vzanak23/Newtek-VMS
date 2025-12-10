/**
 * Analytical Report - Sequential Data Loading
 * ==========================================
 * 
 * This script loads data sequentially when filters are applied:
 * 1. First load all table data (severity, highlight, attribute)
 * 2. Then load chart data separately
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('📊 Analytical Report - Sequential Loading Ready');
    
    // Check if we have any filter values (meaning data should be loaded)
    // If so, automatically start loading charts
    if (hasAnyFilterValue()) {
        console.log('📋 Filters detected - loading charts automatically...');
        console.log('🔍 Filter values found:', getCurrentFilterParams().toString());
        showChartLoadingIndicators();
        loadChartData()
            .then(() => {
                console.log('✅ Charts loaded successfully!');
                hideChartLoadingIndicators();
            })
            .catch(error => {
                console.error('❌ Chart loading failed:', error);
                hideChartLoadingIndicators();
                showErrorMessage('Failed to load charts. Please try again.');
            });
    } else {
        console.log('ℹ️ No filters applied - charts will not load');
    }
    
    // Listen for filter form submissions (normal form submission)
    const filterForm = document.querySelector('#filterForm');
    if (filterForm) {
        console.log('✅ Form found: #filterForm - will submit normally');
        // Don't prevent form submission - let it load tables normally
        // Charts will auto-load after page reloads with table data
    } else {
        console.log('❌ Form #filterForm not found');
    }
});

function hasAnyFilterValue() {
    const date = document.querySelector('[name="date"]')?.value;
    const month = document.querySelector('[name="month"]')?.value;
    const year = document.querySelector('[name="year"]')?.value;
    const qc_no = document.querySelector('[name="qc_no"]')?.value;
    
    return !!(date || month || year || qc_no);
}

function hasTableData() {
    // Check if any table has data rows (not just empty state message)
    const severityTable = document.querySelector('#severityStatsTable tbody');
    const highlightTable = document.querySelector('#highlightStatsTable tbody');
    const attributeTable = document.querySelector('#attributeStatsTable tbody');
    
    if (severityTable && severityTable.children.length > 0) {
        // Check if it's not the "Select filters" message
        const firstRow = severityTable.children[0];
        const firstCell = firstRow?.querySelector('td');
        if (firstCell && !firstCell.textContent.includes('Select filters')) {
            return true;
        }
    }
    
    return false;
}

function loadDataSequentially() {
    // Step 1: Load table data first
    console.log('📋 Step 1: Loading table data...');
    showTableLoadingIndicators();
    
    loadTableData()
        .then(() => {
            console.log('✅ Step 1 Complete: Table data loaded');
            // Step 2: Load chart data after tables are loaded
            console.log('📊 Step 2: Loading chart data...');
            showChartLoadingIndicators();
            return loadChartData();
        })
        .then(() => {
            console.log('✅ Step 2 Complete: Chart data loaded');
            console.log('🎉 All data loaded successfully!');
        })
        .catch(error => {
            console.error('❌ Data loading failed:', error);
            hideChartLoadingIndicators();
            showErrorMessage('Failed to load charts. Please try again.');
        });
}

function loadTableData() {
    // Get current filter parameters
    const params = getCurrentFilterParams();
    params.set('load_tables', '1'); // Load only table data
    params.set('load_charts', '0'); // Skip charts for now
    
    const url = window.location.pathname + '?' + params.toString();
    
    return fetch(url)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.text();
        })
        .then(html => {
            // Update table sections only
            updateTableSections(html);
            hideTableLoadingIndicators();
        });
}

function loadChartData() {
    // Get current filter parameters  
    const params = getCurrentFilterParams();
    params.set('load_tables', '0'); // Skip tables (already loaded)
    params.set('load_charts', '1'); // Load only chart data
    
    const url = window.location.pathname + '?' + params.toString();
    
    return fetch(url)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json(); // Expect JSON response for charts
        })
        .then(chartData => {
            // Update chart sections only
            updateChartSections(chartData);
            hideChartLoadingIndicators();
        });
}

function getCurrentFilterParams() {
    const params = new URLSearchParams();
    
    const date = document.querySelector('[name="date"]')?.value;
    const month = document.querySelector('[name="month"]')?.value;  
    const year = document.querySelector('[name="year"]')?.value;
    const qc_no = document.querySelector('[name="qc_no"]')?.value;
    
    if (date) params.set('date', date);
    if (month) params.set('month', month);
    if (year) params.set('year', year);
    if (qc_no) params.set('qc_no', qc_no);
    
    return params;
}
            console.error('❌ Failed to load data:', error);
            showErrorMessage('Failed to load report data. Please refresh the page.');
            hideLoadingIndicators();
        });
}

function showLoadingIndicators() {
    // Add loading spinners to main sections
    const sections = [
        '.severity-stats-container',
        '.highlight-stats-container', 
        '.attribute-stats-container',
        '.chart-container'
    ];
    
    sections.forEach(selector => {
        const element = document.querySelector(selector);
        if (element) {
            element.innerHTML = `
                <div class="loading-spinner text-center p-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="sr-only">Loading...</span>
                    </div>
                    <p class="mt-2 text-muted">Loading data...</p>
                </div>
            `;
        }
    });
    
    // Show loading message for dropdowns
    const dropdowns = document.querySelectorAll('select[data-loading="true"]');
    dropdowns.forEach(dropdown => {
        dropdown.innerHTML = '<option>Loading...</option>';
        dropdown.disabled = true;
    });
}

function hideLoadingIndicators() {
    // Remove loading spinners
    const spinners = document.querySelectorAll('.loading-spinner');
    spinners.forEach(spinner => spinner.remove());
    
    // Enable dropdowns
    const dropdowns = document.querySelectorAll('select[disabled]');
    dropdowns.forEach(dropdown => {
        dropdown.disabled = false;
    });
}

function updatePageWithData(html) {
    // Create a temporary DOM parser
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    
    // Update severity stats
    updateSection('.severity-stats-container', doc);
    
    // Update highlight stats
    updateSection('.highlight-stats-container', doc);
    
    // Update attribute stats  
    updateSection('.attribute-stats-container', doc);
    
    // Update chart container
    updateSection('.chart-container', doc);
    
    // Update dropdowns
    updateDropdowns(doc);
    
    // Update total records count
    updateTotalRecords(doc);
    
    console.log('🎯 Page updated with loaded data');
}

function updateSection(selector, sourceDoc) {
    const currentElement = document.querySelector(selector);
    const newElement = sourceDoc.querySelector(selector);
    
    if (currentElement && newElement) {
        currentElement.innerHTML = newElement.innerHTML;
    }
}

function updateDropdowns(sourceDoc) {
    // Update QC dropdown
    const qcSelect = document.querySelector('select[name="qc_no"]');
    const newQcSelect = sourceDoc.querySelector('select[name="qc_no"]');
    if (qcSelect && newQcSelect) {
        qcSelect.innerHTML = newQcSelect.innerHTML;
    }
    
    // Update year dropdown
    const yearSelect = document.querySelector('select[name="year"]');
    const newYearSelect = sourceDoc.querySelector('select[name="year"]');
    if (yearSelect && newYearSelect) {
        yearSelect.innerHTML = newYearSelect.innerHTML;
    }
}

function updateTotalRecords(sourceDoc) {
    const totalElement = document.querySelector('.total-records');
    const newTotalElement = sourceDoc.querySelector('.total-records');
    
    if (totalElement && newTotalElement) {
        totalElement.textContent = newTotalElement.textContent;
    }
}

function showErrorMessage(message) {
    const alertHtml = `
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Error!</strong> ${message}
            <button type="button" class="close" data-dismiss="alert">
                <span aria-hidden="true">&times;</span>
            </button>
        </div>
    `;
    
    // Insert at top of main content
    const mainContent = document.querySelector('.main-content') || document.body;
    mainContent.insertAdjacentHTML('afterbegin', alertHtml);
}

// === NEW SEQUENTIAL LOADING FUNCTIONS ===

// === TABLE LOADING INDICATORS ===
function showTableLoadingIndicators() {
    console.log('📋 Showing table loading indicators...');
    
    const tableSections = [
        '.severity-stats-container',
        '.highlight-stats-container', 
        '.attribute-stats-container'
    ];
    
    tableSections.forEach(selector => {
        const element = document.querySelector(selector);
        if (element) {
            element.innerHTML = `
                <div class="loading-spinner text-center p-4">
                    <div class="spinner-border text-success" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <div class="mt-2">Loading table data...</div>
                </div>
            `;
        }
    });
}

function hideTableLoadingIndicators() {
    console.log('✅ Table data loaded');
    // Table spinners will be replaced by actual data in updateTableSections
}

// === CHART LOADING INDICATORS ===
function showChartLoadingIndicators() {
    console.log('📊 Showing chart loading indicators...');
    
    // Show loading indicators for each chart
    const chartLoadings = [
        'severityChartLoading',
        'highlightChartLoading', 
        'attributeChartLoading'
    ];
    
    chartLoadings.forEach(loadingId => {
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) {
            loadingElement.style.display = 'flex';
        }
    });
    
    console.log('✅ Chart loading indicators shown');
}

function hideChartLoadingIndicators() {
    console.log('📊 Hiding chart loading indicators...');
    
    // Hide loading indicators for each chart
    const chartLoadings = [
        'severityChartLoading',
        'highlightChartLoading', 
        'attributeChartLoading'
    ];
    
    chartLoadings.forEach(loadingId => {
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) {
            loadingElement.style.display = 'none';
        }
    });
    
    console.log('✅ Chart loading indicators hidden');
}

function hideAllLoadingIndicators() {
    const spinners = document.querySelectorAll('.loading-spinner');
    spinners.forEach(spinner => spinner.remove());
}

// === UPDATE FUNCTIONS ===
function updateTableSections(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    
    // Update table sections only
    updateSectionFromDoc('.severity-stats-container', doc);
    updateSectionFromDoc('.highlight-stats-container', doc);
    updateSectionFromDoc('.attribute-stats-container', doc);
    
    console.log('📋 Table sections updated');
}

function updateChartSections(chartData) {
    // Update charts with received data
    if (window.updateCharts && typeof window.updateCharts === 'function') {
        window.updateCharts(chartData);
    } else {
        console.warn('Chart update function not found');
    }
    
    console.log('📊 Chart sections updated');
}

function updateSectionFromDoc(selector, sourceDoc) {
    const currentElement = document.querySelector(selector);
    const newElement = sourceDoc.querySelector(selector);
    
    if (currentElement && newElement) {
        currentElement.innerHTML = newElement.innerHTML;
    }
}

function showErrorMessage(message) {
    const alertHtml = `
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <i class="fas fa-exclamation-triangle"></i>
            <strong>Error:</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    const mainContent = document.querySelector('.main-content') || document.body;
    mainContent.insertAdjacentHTML('afterbegin', alertHtml);
}

// Export for potential external use
window.AnalyticalReport = {
    loadData: loadDataSequentially,
    showTableLoading: showTableLoadingIndicators,
    showChartLoading: showChartLoadingIndicators,
    hideLoading: hideAllLoadingIndicators
};