// Dashboard Main JavaScript
let currentUser = null;
let allTestCases = [];
let filteredTestCases = [];
let selectedTestCaseIds = new Set();
let currentPage = 1;
let itemsPerPage = 20;
let currentTestCaseForAction = null;
let activeExecutionId = null;
let activeExecutionTestCaseId = null;
let activeExecutionSteps = [];
let selectedExecutionStepId = null;
let executionTimerInterval = null;
let executionTimerStart = null;
let executionAccumulatedSeconds = 0;
let allBugAssignees = [];

const OPEN_BUG_STATUSES = new Set(['new', 'open', 'in_progress', 'reopened']);

// ============ Initialize Dashboard ============
document.addEventListener('DOMContentLoaded', async () => {
    // Set flag so API errors don't immediately redirect
    isDashboardInitializing = true;

    console.log('[Dashboard] Initializing at', new Date().toISOString());

    // Check authentication
    const token = localStorage.getItem('access_token');
    console.log('[Dashboard] Token check:', {
        hasToken: !!token,
        tokenLength: token ? token.length : 0,
        tokenPrefix: token ? token.substring(0, 50) : 'NONE'
    });

    if (!token) {
        console.log('[Dashboard] No token found, redirecting to login');
        isDashboardInitializing = false;
        window.location.href = '/login';
        return;
    }

    try {
        // Load current user with retry logic
        console.log('[Dashboard] Loading current user (Attempt 1)...');
        let currentUserData = null;
        let attemptCount = 0;
        const maxAttempts = 3;

        while (!currentUserData && attemptCount < maxAttempts) {
            attemptCount++;
            try {
                currentUserData = await API.Auth.getCurrentUser();
                console.log('[Dashboard] Current user loaded successfully on attempt', attemptCount, {
                    email: currentUserData.email,
                    role: currentUserData.role
                });
                break;
            } catch (userError) {
                console.error(`[Dashboard] Attempt ${attemptCount} failed:`, {
                    message: userError.message,
                    stack: userError.stack,
                    response: userError.response || 'N/A'
                });

                if (attemptCount < maxAttempts) {
                    console.log(`[Dashboard] Retrying in 500ms...`);
                    await new Promise(resolve => setTimeout(resolve, 500));
                } else {
                    console.error('[Dashboard] All retry attempts failed. User not loaded.');
                    throw userError;
                }
            }
        }

        if (!currentUserData) {
            throw new Error('Could not load current user after ' + maxAttempts + ' attempts');
        }

        currentUser = currentUserData;
        displayUserInfo();

        // Load initial data
        console.log('[Dashboard] Loading test cases...');
        await loadTestCases();
        console.log('[Dashboard] Loaded', allTestCases.length, 'test cases');

        console.log('[Dashboard] Loading testers...');
        await loadTesters();

        console.log('[Dashboard] Loading bug assignees...');
        await loadBugAssignees();

        console.log('[Dashboard] Refreshing executive KPIs...');
        await refreshDashboardExecutiveKpis();

        // Setup event listeners
        setupEventListeners();
        setupModalHandlers();
        setupNavigationHandlers();

        console.log('[Dashboard] Initialization complete at', new Date().toISOString());

        // Now allow redirects on auth errors
        isDashboardInitializing = false;
    } catch (error) {
        console.error('[Dashboard] Initialization FAILED:', {
            message: error.message,
            type: error.constructor.name,
            stack: error.stack,
            fullError: error
        });

        // Show error message
        const msg = error.message || 'Failed to load dashboard. Please check console for details.';
        console.error('[Dashboard]', msg);

        // Display error in UI if possible
        const container = document.querySelector('.dashboard-container');
        if (container) {
            container.innerHTML = `
                <div style="padding:20px;background:#ffebee;color:#c62828;border-radius:4px;margin:20px;">
                    <h2>Dashboard Load Error</h2>
                    <p>${msg}</p>
                    <p style="font-size:12px;color:#999;">Check browser console (F12) for detailed error logs</p>
                    <button onclick="location.href='/login'" style="padding:10px 20px;background:#c62828;color:white;border:none;cursor:pointer;border-radius:4px;">
                        Return to Login
                    </button>
                </div>
            `;
        }

        isDashboardInitializing = false;
        showNotification('Failed to load dashboard', 'error');
    }
});

// ============ Display User Info ============
function displayUserInfo() {
    document.getElementById('userName').textContent = currentUser.full_name || currentUser.email;
    document.getElementById('userRole').textContent = currentUser.role || 'User';

    // Show admin link if user is admin
    const adminLink = document.getElementById('adminLink');
    if (adminLink && currentUser.role === 'admin') {
        adminLink.style.display = 'flex';
    }
}

function setKpiValue(id, value) {
    const element = document.getElementById(id);
    if (!element) return;
    element.textContent = value;
}

function touchKpiLastUpdated() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    setKpiValue('kpiLastUpdated', `${hours}:${minutes}`);
}

function updateDashboardCaseKpis() {
    const totalCases = allTestCases.length;
    const approvedCases = allTestCases.filter((testCase) => testCase.status === 'approved').length;
    setKpiValue('kpiTotalCases', String(totalCases));
    setKpiValue('kpiApprovedCases', `${approvedCases} approved`);
    touchKpiLastUpdated();
}

function setDashboardOpenBugKpiFromRows(bugs) {
    const bugRows = Array.isArray(bugs) ? bugs : [];
    const openCount = bugRows.filter((bug) => OPEN_BUG_STATUSES.has((bug.status || '').toLowerCase())).length;
    setKpiValue('kpiOpenBugs', String(openCount));
    touchKpiLastUpdated();
}

function updateDashboardExecutionKpiFromRows(rows) {
    const executionRows = Array.isArray(rows) ? rows : [];
    const failedExecutions = executionRows.filter((row) => (row.status || '').toLowerCase() === 'fail').length;
    const failRate = executionRows.length > 0 ? ((failedExecutions / executionRows.length) * 100).toFixed(1) : '0.0';

    setKpiValue('kpiRecentExecutions', String(executionRows.length));
    setKpiValue('kpiExecutionMeta', `Fail rate ${failRate}%`);
    touchKpiLastUpdated();
}

async function refreshDashboardExecutionKpiSample() {
    if (!allTestCases || allTestCases.length === 0) {
        updateDashboardExecutionKpiFromRows([]);
        return;
    }

    try {
        // Sample the first 20 cases for quick KPI feedback without blocking dashboard actions.
        const sampleCases = allTestCases.slice(0, 20);
        const historyRows = await Promise.all(
            sampleCases.map(async (testCase) => {
                try {
                    const rows = await API.Execution.history(testCase.id);
                    return Array.isArray(rows) ? rows : [];
                } catch (error) {
                    console.error(`Failed to load execution KPI history for case ${testCase.id}:`, error);
                    return [];
                }
            })
        );

        const flattenedRows = historyRows.flat();
        updateDashboardExecutionKpiFromRows(flattenedRows);
    } catch (error) {
        console.error('Failed to refresh execution KPI sample:', error);
    }
}

async function refreshDashboardOpenBugKpi() {
    try {
        const bugs = await API.Bugs.list();
        setDashboardOpenBugKpiFromRows(bugs);
    } catch (error) {
        console.error('Failed to refresh open bug KPI:', error);
    }
}

async function refreshDashboardExecutiveKpis() {
    updateDashboardCaseKpis();
    await Promise.all([
        refreshDashboardOpenBugKpi(),
        refreshDashboardExecutionKpiSample()
    ]);
}

// ============ Load Test Cases ============
async function loadTestCases(filters = {}) {
    try {
        showLoading('testCasesTableBody');
        const response = await API.TestCases.list(filters);
        // Extract test_cases array from paginated response
        const data = response.test_cases || [];
        allTestCases = data;
        filteredTestCases = data;
        updateDashboardCaseKpis();
        await loadBugAssignees();
        renderTestCasesTable();
    } catch (error) {
        console.error('Failed to load test cases:', error);
        const errorMsg = error?.message || error?.detail || String(error);
        showError('testCasesTableBody', `Failed to load test cases: ${errorMsg}`);
    }
}

// ============ Render Test Cases Table ============
function renderTestCasesTable() {
    const tbody = document.getElementById('testCasesTableBody');

    if (filteredTestCases.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="text-center">No test cases found</td></tr>';
        return;
    }

    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageItems = filteredTestCases.slice(startIndex, endIndex);

    tbody.innerHTML = pageItems.map(tc => `
        <tr class="${selectedTestCaseIds.has(tc.id) ? 'selected' : ''}">
            <td>
                <input type="checkbox" class="row-checkbox" data-id="${tc.id}" 
                    ${selectedTestCaseIds.has(tc.id) ? 'checked' : ''}>
            </td>
            <td><strong>${tc.test_case_id || 'N/A'}</strong></td>
            <td>
                <a href="#" class="test-case-link" data-id="${tc.id}">${tc.title}</a>
            </td>
            <td><span class="badge badge-${tc.priority.toLowerCase()}">${tc.priority}</span></td>
            <td><span class="badge badge-${tc.status.toLowerCase()}">${tc.status}</span></td>
            <td>${tc.type}</td>
            <td>${tc.owner?.full_name || 'N/A'}</td>
            <td>${tc.assigned_tester?.full_name || 'Unassigned'}</td>
            <td>${new Date(tc.created_at).toLocaleDateString()}</td>
            <td>
                <div class="action-icons">
                    <span class="action-icon" title="View Details" onclick="viewTestCase(${tc.id})">👁️</span>
                    <span class="action-icon" title="Edit" onclick="editTestCase(${tc.id})">✏️</span>
                    <span class="action-icon" title="Execute" onclick="openExecutionFromTable(${tc.id})">▶️</span>
                    <span class="action-icon" title="Clone" onclick="openCloneModal(${tc.id})">📋</span>
                    <span class="action-icon" title="Delete" onclick="deleteTestCase(${tc.id})">🗑️</span>
                </div>
            </td>
        </tr>
    `).join('');

    updatePagination();
    setupRowCheckboxes();
    setupTestCaseLinks();
}

// ============ Setup Event Listeners ============
function setupEventListeners() {
    // Logout button
    document.getElementById('logoutBtn').addEventListener('click', () => API.Auth.logout());

    // Create test case button
    document.getElementById('createTestCaseBtn').addEventListener('click', () => {
        openTestCaseModal();
    });

    // Execution module buttons
    if (document.getElementById('startExecutionBtn')) {
        document.getElementById('startExecutionBtn').addEventListener('click', startExecutionFromSelection);
        document.getElementById('reexecuteBtn').addEventListener('click', reexecuteFromSelection);
        document.getElementById('refreshExecutionHistoryBtn').addEventListener('click', refreshExecutionHistoryFromSelection);
        document.getElementById('pauseTimerBtn').addEventListener('click', pauseExecutionTimer);
        document.getElementById('resumeTimerBtn').addEventListener('click', resumeExecutionTimer);
        document.getElementById('setManualDurationBtn').addEventListener('click', setExecutionManualDuration);
        document.getElementById('completeExecutionBtn').addEventListener('click', completeCurrentExecution);
        document.getElementById('uploadEvidenceBtn').addEventListener('click', uploadExecutionEvidenceForSelectedStep);
        document.getElementById('createRunBtn').addEventListener('click', createTestRunFromForm);
    }

    if (document.getElementById('refreshBugsBtn')) {
        document.getElementById('refreshBugsBtn').addEventListener('click', loadBugReportsView);
        document.getElementById('createBugBtn').addEventListener('click', createBugReportFromForm);
        document.getElementById('bugSearchInput').addEventListener('input', debounce(loadBugReportsView, 300));
        document.getElementById('bugFilterStatus').addEventListener('change', loadBugReportsView);
        document.getElementById('bugFilterPriority').addEventListener('change', loadBugReportsView);
        document.getElementById('bugFilterSeverity').addEventListener('change', loadBugReportsView);
        document.getElementById('bugSortBy').addEventListener('change', loadBugReportsView);
        document.getElementById('bugMineOnly').addEventListener('change', loadBugReportsView);
    }

    if (document.getElementById('refreshAnalyticsBtn')) {
        document.getElementById('refreshAnalyticsBtn').addEventListener('click', loadAnalyticsView);
    }

    // Search input
    document.getElementById('searchInput').addEventListener('input', debounce(handleSearch, 300));

    // Filter selects
    document.getElementById('filterStatus').addEventListener('change', applyFilters);
    document.getElementById('filterPriority').addEventListener('change', applyFilters);
    document.getElementById('filterType').addEventListener('change', applyFilters);
    document.getElementById('filterAutomation').addEventListener('change', applyFilters);

    // Template filter
    document.getElementById('filterTemplateCategory').addEventListener('change', loadTemplates);

    // Select all checkbox
    document.getElementById('selectAllCheckbox').addEventListener('change', handleSelectAll);

    // Bulk action buttons
    document.getElementById('bulkUpdateBtn').addEventListener('click', openBulkUpdateModal);
    document.getElementById('bulkDeleteBtn').addEventListener('click', bulkDeleteTestCases);
    document.getElementById('bulkExportBtn').addEventListener('click', () => API.Bulk.export('csv'));
    document.getElementById('clearSelectionBtn').addEventListener('click', clearSelection);

    // Import/Export buttons
    document.getElementById('importTestCasesBtn').addEventListener('click', openImportModal);
    document.getElementById('exportAllBtn').addEventListener('click', () => API.Bulk.export('csv'));

    // Pagination
    document.getElementById('prevPageBtn').addEventListener('click', () => changePage(currentPage - 1));
    document.getElementById('nextPageBtn').addEventListener('click', () => changePage(currentPage + 1));

    // Test case form
    document.getElementById('testCaseForm').addEventListener('submit', handleTestCaseFormSubmit);

    // Add step button
    document.getElementById('addStepBtn').addEventListener('click', addStepRow);

    // Clone confirmation
    document.getElementById('confirmCloneBtn').addEventListener('click', confirmClone);

    // Delete confirmation
    document.getElementById('confirmDeleteBtn').addEventListener('click', confirmDelete);

    // Bulk update confirmation
    document.getElementById('confirmBulkUpdateBtn').addEventListener('click', confirmBulkUpdate);

    // Import wizard buttons
    document.getElementById('browseFileBtn').addEventListener('click', () => {
        document.getElementById('importFileInput').click();
    });
    document.getElementById('importFileInput').addEventListener('change', handleFileSelect);
    document.getElementById('importNextBtn').addEventListener('click', handleImportNext);
    document.getElementById('importBackBtn').addEventListener('click', handleImportBack);

    // Create template buttons
    document.getElementById('confirmCreateTemplateBtn').addEventListener('click', confirmCreateTemplate);
}

// ============ Setup Modal Handlers ============
function setupModalHandlers() {
    // Close buttons
    document.querySelectorAll('.modal-close, [data-modal]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modalId = e.target.getAttribute('data-modal');
            if (modalId) {
                closeModal(modalId);
            }
        });
    });

    // Close on outside click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal(modal.id);
            }
        });
    });

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tabName = e.target.getAttribute('data-tab');
            switchTab(tabName);
        });
    });
}

// ============ Setup Navigation Handlers ============
function setupNavigationHandlers() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            const view = e.currentTarget.getAttribute('data-view');
            const href = e.currentTarget.getAttribute('href') || '';

            // Internal dashboard tabs use data-view. Real links (e.g., suite page) should navigate normally.
            if (view) {
                e.preventDefault();
                switchView(view);
                return;
            }

            if (!href || href === '#') {
                e.preventDefault();
            }
        });
    });
}

// ============ Switch View ============
function switchView(viewName) {
    const normalizedView = String(viewName || '').trim().toLowerCase();

    const viewMap = {
        'test-cases': 'testCasesView',
        'templates': 'templatesView',
        'executions': 'executionsView',
        'bugs': 'bugsView',
        'analytics': 'analyticsView'
    };

    const titles = {
        'test-cases': { title: 'Test Cases', subtitle: 'Manage and organize your test cases' },
        'templates': { title: 'Templates', subtitle: 'Reusable test case templates' },
        'executions': { title: 'Test Executions', subtitle: 'Run test cases, track progress, capture evidence' },
        'bugs': { title: 'Bug Reports', subtitle: 'Review bug IDs linked from failed test executions' },
        'analytics': { title: 'Analytics', subtitle: 'Execution trends and quality metrics' }
    };

    const viewId = viewMap[normalizedView];
    if (!viewId) {
        showNotification('This view is not implemented yet', 'warning');
        return;
    }

    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-view="${normalizedView}"]`).classList.add('active');

    // Update view containers
    document.querySelectorAll('.view-container').forEach(view => {
        view.classList.remove('active');
    });
    document.getElementById(viewId).classList.add('active');

    // Update header
    document.getElementById('pageTitle').textContent = titles[normalizedView].title;
    document.getElementById('pageSubtitle').textContent = titles[normalizedView].subtitle;

    // Load data if needed
    if (normalizedView === 'templates') {
        loadTemplates();
    }
    if (normalizedView === 'executions') {
        loadExecutionDashboardData();
    }
    if (normalizedView === 'bugs') {
        loadBugReportsView();
    }
    if (normalizedView === 'analytics') {
        loadAnalyticsView();
    }
}

async function fetchCasesAndExecutionHistory() {
    const list = await API.TestCases.list({ page: 1, page_size: 100 });
    const testCases = list.test_cases || [];

    const historyResults = await Promise.all(
        testCases.map(async (tc) => {
            try {
                const rows = await API.Execution.history(tc.id);
                return { testCase: tc, history: rows || [] };
            } catch (error) {
                console.error(`Failed to load execution history for test case ${tc.id}:`, error);
                return { testCase: tc, history: [] };
            }
        })
    );

    return { testCases, historyResults };
}

async function loadBugReportsView() {
    const body = document.getElementById('bugsTableBody');
    if (!body) return;

    body.innerHTML = '<tr><td colspan="10" class="text-center">Loading bug reports...</td></tr>';

    try {
        const bugs = await API.Bugs.list({
            search: document.getElementById('bugSearchInput')?.value?.trim() || '',
            status: document.getElementById('bugFilterStatus')?.value || '',
            priority: document.getElementById('bugFilterPriority')?.value || '',
            severity: document.getElementById('bugFilterSeverity')?.value || '',
            sort_by: document.getElementById('bugSortBy')?.value || 'created_at',
            mine_only: document.getElementById('bugMineOnly')?.checked ? 'true' : ''
        });

        if (!bugs || bugs.length === 0) {
            setDashboardOpenBugKpiFromRows([]);
            body.innerHTML = '<tr><td colspan="10" class="text-center">No bug reports found</td></tr>';
            return;
        }

        setDashboardOpenBugKpiFromRows(bugs);

        body.innerHTML = bugs.map((bug) => `
            <tr>
                <td><strong>${bug.bug_id}</strong></td>
                <td>${bug.title}</td>
                <td>${bug.priority}</td>
                <td>${bug.severity}</td>
                <td>${bug.status}</td>
                <td>${bug.assigned_to_name || 'Unassigned'}</td>
                <td>${bug.linked_test_case_identifier || 'N/A'}</td>
                <td>${bug.attachment_count || 0}</td>
                <td>${bug.created_at ? new Date(bug.created_at).toLocaleString() : 'N/A'}</td>
                <td>
                    <div style="display:flex; gap:6px; align-items:center;">
                        <select id="bugStatus_${bug.bug_id}" class="form-control" style="min-width: 150px;">
                            <option value="new" ${bug.status === 'new' ? 'selected' : ''}>New</option>
                            <option value="open" ${bug.status === 'open' ? 'selected' : ''}>Open</option>
                            <option value="in_progress" ${bug.status === 'in_progress' ? 'selected' : ''}>In Progress</option>
                            <option value="fixed" ${bug.status === 'fixed' ? 'selected' : ''}>Fixed</option>
                            <option value="verified" ${bug.status === 'verified' ? 'selected' : ''}>Verified</option>
                            <option value="closed" ${bug.status === 'closed' ? 'selected' : ''}>Closed</option>
                            <option value="reopened" ${bug.status === 'reopened' ? 'selected' : ''}>Reopened</option>
                            <option value="wont_fix" ${bug.status === 'wont_fix' ? 'selected' : ''}>Won't Fix</option>
                            <option value="duplicate" ${bug.status === 'duplicate' ? 'selected' : ''}>Duplicate</option>
                        </select>
                        <button class="btn btn-sm btn-secondary" onclick="updateBugStatus('${bug.bug_id}')">Save</button>
                    </div>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load bug reports view:', error);
        body.innerHTML = '<tr><td colspan="10" class="text-center">Failed to load bug reports</td></tr>';
        showNotification('Failed to load bug reports', 'error');
    }
}

async function createBugReportFromForm() {
    const title = document.getElementById('bugCreateTitle')?.value?.trim();
    const description = document.getElementById('bugCreateDescription')?.value?.trim();
    const steps = document.getElementById('bugCreateSteps')?.value?.trim();
    const expected = document.getElementById('bugCreateExpected')?.value?.trim();
    const actual = document.getElementById('bugCreateActual')?.value?.trim();

    if (!title || !description || !steps || !expected || !actual) {
        showNotification('Fill in title, description, steps, expected, and actual behavior', 'warning');
        return;
    }

    try {
        await API.Bugs.create({
            title,
            description,
            steps_to_reproduce: steps,
            expected_behavior: expected,
            actual_behavior: actual,
            priority: document.getElementById('bugCreatePriority').value,
            severity: document.getElementById('bugCreateSeverity').value,
            environment: document.getElementById('bugCreateEnvironment')?.value?.trim() || null,
            affected_version: document.getElementById('bugCreateVersion')?.value?.trim() || null,
            assigned_to_id: parseInt(document.getElementById('bugCreateAssignedTo')?.value) || null,
            linked_test_case_id: parseInt(document.getElementById('bugCreateLinkedTestCase')?.value) || null,
        });

        ['bugCreateTitle', 'bugCreateDescription', 'bugCreateSteps', 'bugCreateExpected', 'bugCreateActual', 'bugCreateEnvironment', 'bugCreateVersion'].forEach((id) => {
            const element = document.getElementById(id);
            if (element) element.value = '';
        });
        document.getElementById('bugCreateAssignedTo').value = '';
        document.getElementById('bugCreateLinkedTestCase').value = '';

        showNotification('Bug report created', 'success');
        await loadBugReportsView();
        await refreshDashboardOpenBugKpi();
    } catch (error) {
        console.error('Failed to create bug report:', error);
        showNotification(error.message || 'Failed to create bug report', 'error');
    }
}

async function updateBugStatus(bugId) {
    try {
        const status = document.getElementById(`bugStatus_${bugId}`).value;
        await API.Bugs.updateStatus(bugId, status);
        showNotification(`Bug ${bugId} updated`, 'success');
        await loadBugReportsView();
        await refreshDashboardOpenBugKpi();
    } catch (error) {
        console.error('Failed to update bug status:', error);
        showNotification(error.message || 'Failed to update bug status', 'error');
    }
}

async function loadAnalyticsView() {
    const breakdownBody = document.getElementById('analyticsBreakdownBody');
    const totalCasesEl = document.getElementById('analyticsTotalCases');
    const totalExecutionsEl = document.getElementById('analyticsTotalExecutions');
    const passRateEl = document.getElementById('analyticsPassRate');
    const totalBugsEl = document.getElementById('analyticsTotalBugs');

    if (!breakdownBody || !totalCasesEl || !totalExecutionsEl || !passRateEl || !totalBugsEl) return;

    breakdownBody.innerHTML = '<tr><td colspan="2" class="text-center">Loading analytics...</td></tr>';

    try {
        const { testCases, historyResults } = await fetchCasesAndExecutionHistory();
        const allExecutions = historyResults.flatMap((item) => item.history || []);

        const totalCases = testCases.length;
        const totalExecutions = allExecutions.length;
        const passedExecutions = allExecutions.filter((e) => e.status === 'pass').length;
        const failedExecutions = allExecutions.filter((e) => e.status === 'fail').length;
        const blockedExecutions = allExecutions.filter((e) => e.status === 'blocked').length;
        const notExecutedExecutions = allExecutions.filter((e) => e.status === 'not_executed').length;
        const skippedExecutions = allExecutions.filter((e) => e.status === 'skipped').length;

        const uniqueBugs = new Set();
        allExecutions.forEach((e) => {
            if (!e.bug_ids) return;
            e.bug_ids.split(',').map((id) => id.trim()).filter(Boolean).forEach((id) => uniqueBugs.add(id));
        });

        const passRate = totalExecutions > 0 ? ((passedExecutions / totalExecutions) * 100).toFixed(1) : '0.0';

        totalCasesEl.value = String(totalCases);
        totalExecutionsEl.value = String(totalExecutions);
        passRateEl.value = `${passRate}%`;
        totalBugsEl.value = String(uniqueBugs.size);

        breakdownBody.innerHTML = `
            <tr><td>Passed Executions</td><td>${passedExecutions}</td></tr>
            <tr><td>Failed Executions</td><td>${failedExecutions}</td></tr>
            <tr><td>Blocked Executions</td><td>${blockedExecutions}</td></tr>
            <tr><td>Not Executed</td><td>${notExecutedExecutions}</td></tr>
            <tr><td>Skipped Executions</td><td>${skippedExecutions}</td></tr>
            <tr><td>Unique Bug IDs Linked</td><td>${uniqueBugs.size}</td></tr>
        `;
    } catch (error) {
        console.error('Failed to load analytics view:', error);
        breakdownBody.innerHTML = '<tr><td colspan="2" class="text-center">Failed to load analytics</td></tr>';
        showNotification('Failed to load analytics', 'error');
    }
}

// ============ Load Templates ============
async function loadTemplates() {
    try {
        const category = document.getElementById('filterTemplateCategory').value;
        const templates = await API.Templates.list(category || null);

        // Handle response - could be array or object with data property
        const templateArray = Array.isArray(templates) ? templates : (templates?.data || []);
        renderTemplates(templateArray);
    } catch (error) {
        console.error('Failed to load templates:', error);
        const grid = document.getElementById('templatesGrid');
        const errorMsg = error?.message || error?.detail || 'Unknown error';
        grid.innerHTML = `<p class="text-center" style="color: #d32f2f; padding: 20px;">Error loading templates: ${errorMsg}</p>`;
        showNotification('Failed to load templates: ' + errorMsg, 'error');
    }
}

// ============ Render Templates ============
function renderTemplates(templates) {
    const grid = document.getElementById('templatesGrid');

    // Handle null, undefined, or empty array
    const templateArray = templates && Array.isArray(templates) ? templates : [];

    if (templateArray.length === 0) {
        grid.innerHTML = '<p class="text-center" style="padding: 40px; color: #666;">No templates available. Create templates from existing test cases.</p>';
        return;
    }

    grid.innerHTML = templateArray.map(template => `
        <div class="template-card" onclick="createFromTemplate(${template.id})">
            <h3>${template.name}</h3>
            <span class="template-category">${template.category}</span>
            <p>${template.description || 'No description'}</p>
            <div class="template-footer">
                <small>Created by ${template.created_by?.full_name || 'Unknown'}</small>
            </div>
        </div>
    `).join('');
}

// ============ Create Test Case from Template ============
async function createFromTemplate(templateId) {
    try {
        showNotification('Creating test case from template...', 'info');
        const testCase = await API.Templates.createTestCase(templateId);
        showNotification('Test case created successfully!', 'success');
        await loadTestCases();
        switchView('test-cases');
        viewTestCase(testCase.id);
    } catch (error) {
        console.error('Failed to create from template:', error);
        showNotification('Failed to create test case from template', 'error');
    }
}

// ============ Filter and Search ============
function handleSearch(e) {
    const searchTerm = e.target.value.toLowerCase();
    filteredTestCases = allTestCases.filter(tc =>
        tc.title.toLowerCase().includes(searchTerm) ||
        tc.test_case_id.toLowerCase().includes(searchTerm) ||
        (tc.description && tc.description.toLowerCase().includes(searchTerm))
    );
    currentPage = 1;
    renderTestCasesTable();
}

function applyFilters() {
    const status = document.getElementById('filterStatus').value;
    const priority = document.getElementById('filterPriority').value;
    const type = document.getElementById('filterType').value;
    const automation = document.getElementById('filterAutomation').value;

    filteredTestCases = allTestCases.filter(tc => {
        return (!status || tc.status === status) &&
            (!priority || tc.priority === priority) &&
            (!type || tc.type === type) &&
            (!automation || tc.automation_status === automation);
    });

    currentPage = 1;
    renderTestCasesTable();
}

// ============ Pagination ============
function updatePagination() {
    const totalPages = Math.ceil(filteredTestCases.length / itemsPerPage);
    document.getElementById('pageInfo').textContent = `Page ${currentPage} of ${totalPages}`;
    document.getElementById('prevPageBtn').disabled = currentPage === 1;
    document.getElementById('nextPageBtn').disabled = currentPage === totalPages;
}

function changePage(page) {
    const totalPages = Math.ceil(filteredTestCases.length / itemsPerPage);
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    renderTestCasesTable();
}

// ============ Row Selection ============
function setupRowCheckboxes() {
    document.querySelectorAll('.row-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const id = parseInt(e.target.getAttribute('data-id'));
            if (e.target.checked) {
                selectedTestCaseIds.add(id);
            } else {
                selectedTestCaseIds.delete(id);
            }
            updateBulkActionsBar();
            renderTestCasesTable();
        });
    });
}

function handleSelectAll(e) {
    if (e.target.checked) {
        filteredTestCases.forEach(tc => selectedTestCaseIds.add(tc.id));
    } else {
        selectedTestCaseIds.clear();
    }
    updateBulkActionsBar();
    renderTestCasesTable();
}

function clearSelection() {
    selectedTestCaseIds.clear();
    document.getElementById('selectAllCheckbox').checked = false;
    updateBulkActionsBar();
    renderTestCasesTable();
}

function updateBulkActionsBar() {
    const bar = document.getElementById('bulkActionsBar');
    const count = selectedTestCaseIds.size;

    if (count > 0) {
        bar.style.display = 'flex';
        document.getElementById('selectedCount').textContent = `${count} selected`;
    } else {
        bar.style.display = 'none';
    }
}

// ============ Setup Test Case Links ============
function setupTestCaseLinks() {
    document.querySelectorAll('.test-case-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const id = parseInt(e.target.getAttribute('data-id'));
            viewTestCase(id);
        });
    });
}

// ============ Load Testers for Dropdown ============
async function loadTesters() {
    try {
        const response = await API.Users.getTesterUsers();
        const users = Array.isArray(response) ? response : (response.users || []);

        const assigneeSelect = document.getElementById('assigned_tester_id');
        const bulkAssigneeSelect = document.getElementById('bulkAssignee');
        const runTestersSelect = document.getElementById('runTestersSelect');

        const options = users.map(user =>
            `<option value="${user.id}">${user.full_name || user.email}</option>`
        ).join('');

        if (assigneeSelect) {
            assigneeSelect.innerHTML = '<option value="">Unassigned</option>' + options;
        }
        if (bulkAssigneeSelect) {
            bulkAssigneeSelect.innerHTML = '<option value="">-- Keep Unchanged --</option>' + options;
        }
        if (runTestersSelect) {
            runTestersSelect.innerHTML = options;
        }
    } catch (error) {
        console.error('Failed to load testers:', error);
    }
}

async function loadBugAssignees() {
    try {
        const users = await API.Bugs.getAssignees();
        allBugAssignees = Array.isArray(users) ? users : [];

        const assigneeSelect = document.getElementById('bugCreateAssignedTo');
        if (assigneeSelect) {
            const options = allBugAssignees.map((user) => (
                `<option value="${user.id}">${user.full_name || user.email} (${user.role})</option>`
            )).join('');
            assigneeSelect.innerHTML = '<option value="">Unassigned</option>' + options;
        }

        const linkedCaseSelect = document.getElementById('bugCreateLinkedTestCase');
        if (linkedCaseSelect) {
            const options = allTestCases.map((testCase) => (
                `<option value="${testCase.id}">${testCase.test_case_id} - ${testCase.title}</option>`
            )).join('');
            linkedCaseSelect.innerHTML = '<option value="">None</option>' + options;
        }
    } catch (error) {
        console.error('Failed to load bug assignees:', error);
    }
}

// ============ Modal Management ============
function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// ============ Open Test Case Modal (Create/Edit) ============
function openTestCaseModal(testCase = null) {
    const modal = document.getElementById('testCaseModal');
    const title = document.getElementById('testCaseModalTitle');
    const form = document.getElementById('testCaseForm');
    const changeSummaryGroup = document.getElementById('changeSummaryGroup');

    form.reset();
    document.getElementById('stepsContainer').innerHTML = '';

    if (testCase) {
        // Edit mode
        title.textContent = 'Edit Test Case';
        changeSummaryGroup.style.display = 'block';
        document.getElementById('testCaseId').value = testCase.id;
        document.getElementById('title').value = testCase.title;
        document.getElementById('description').value = testCase.description || '';
        document.getElementById('priority').value = testCase.priority;
        document.getElementById('severity').value = testCase.severity;
        document.getElementById('status').value = testCase.status;
        document.getElementById('type').value = testCase.type;
        document.getElementById('automation_status').value = testCase.automation_status;
        document.getElementById('module').value = testCase.module || '';
        document.getElementById('feature').value = testCase.feature || '';
        document.getElementById('preconditions').value = testCase.preconditions || '';
        document.getElementById('assigned_tester_id').value = testCase.assigned_tester_id || '';

        if (testCase.tags && testCase.tags.length > 0) {
            document.getElementById('tags').value = testCase.tags.map(t => t.name).join(', ');
        }

        // Load steps
        if (testCase.steps && testCase.steps.length > 0) {
            testCase.steps.forEach(step => addStepRow(step));
        }
    } else {
        // Create mode
        title.textContent = 'Create Test Case';
        changeSummaryGroup.style.display = 'none';
    }

    openModal('testCaseModal');
}

// ============ Handle Test Case Form Submit ============
async function handleTestCaseFormSubmit(e) {
    e.preventDefault();

    const testCaseId = document.getElementById('testCaseId').value;
    const isEdit = !!testCaseId;

    const data = {
        title: document.getElementById('title').value,
        description: document.getElementById('description').value,
        priority: document.getElementById('priority').value,
        severity: document.getElementById('severity').value,
        status: document.getElementById('status').value,
        type: document.getElementById('type').value,
        automation_status: document.getElementById('automation_status').value,
        module: document.getElementById('module').value,
        pre_conditions: document.getElementById('preconditions').value || null,
        project_id: 1, // Default project
        assigned_tester_id: parseInt(document.getElementById('assigned_tester_id').value) || null,
        steps: [], // Steps can be added later
        tags: [] // Tags can be added later
    };

    // Parse tags if provided
    const tagsInput = document.getElementById('tags').value;
    if (tagsInput) {
        data.tags = tagsInput.split(',').map(tag => tag.trim()).filter(tag => tag);
    }

    try {
        if (isEdit) {
            const changeSummary = document.getElementById('change_summary').value;
            if (!changeSummary || changeSummary.length < 5) {
                showNotification('Please provide a change summary (minimum 5 characters)', 'error');
                return;
            }
            await API.TestCases.update(testCaseId, data, changeSummary);
            showNotification('Test case updated successfully!', 'success');
        } else {
            await API.TestCases.create(data);
            showNotification('Test case created successfully!', 'success');
        }

        closeModal('testCaseModal');
        await loadTestCases();
    } catch (error) {
        console.error('Failed to save test case:', error);
        showNotification(error.message || 'Failed to save test case', 'error');
    }
}

// ============ Steps Management ============
let stepCounter = 0;

function addStepRow(step = null) {
    stepCounter++;
    const container = document.getElementById('stepsContainer');
    const stepDiv = document.createElement('div');
    stepDiv.className = 'step-item';
    stepDiv.innerHTML = `
        <div class="step-header">
            <span class="step-number">Step ${stepCounter}</span>
            <button type="button" class="step-remove" onclick="removeStepRow(this)">Remove</button>
        </div>
        <div class="form-group">
            <input type="text" class="form-control step-action" placeholder="Action/Step description" 
                value="${step ? step.step_description : ''}" required>
        </div>
        <div class="form-group">
            <input type="text" class="form-control step-expected" placeholder="Expected result" 
                value="${step ? step.expected_result : ''}">
        </div>
    `;
    container.appendChild(stepDiv);
}

function removeStepRow(button) {
    button.closest('.step-item').remove();
}

// ============ View Test Case Details ============
async function viewTestCase(id) {
    try {
        const testCase = await API.TestCases.get(id);
        currentTestCaseForAction = testCase;

        document.getElementById('detailTestCaseId').textContent = testCase.test_case_id;
        document.getElementById('detailTestCaseTitle').textContent = testCase.title;

        // Overview tab
        const overview = document.getElementById('testCaseOverview');
        overview.innerHTML = `
            <div class="detail-grid">
                <div class="detail-item">
                    <strong>Priority:</strong> <span class="badge badge-${testCase.priority.toLowerCase()}">${testCase.priority}</span>
                </div>
                <div class="detail-item">
                    <strong>Severity:</strong> <span class="badge badge-${testCase.severity.toLowerCase()}">${testCase.severity}</span>
                </div>
                <div class="detail-item">
                    <strong>Status:</strong> <span class="badge badge-${testCase.status.toLowerCase()}">${testCase.status}</span>
                </div>
                <div class="detail-item">
                    <strong>Type:</strong> ${testCase.type}
                </div>
                <div class="detail-item">
                    <strong>Automation:</strong> ${testCase.automation_status}
                </div>
                <div class="detail-item">
                    <strong>Module:</strong> ${testCase.module || 'N/A'}
                </div>
                <div class="detail-item">
                    <strong>Feature:</strong> ${testCase.feature || 'N/A'}
                </div>
                <div class="detail-item">
                    <strong>Owner:</strong> ${testCase.owner?.full_name || 'N/A'}
                </div>
                <div class="detail-item">
                    <strong>Assigned To:</strong> ${testCase.assigned_tester?.full_name || 'Unassigned'}
                </div>
                <div class="detail-item">
                    <strong>Created:</strong> ${new Date(testCase.created_at).toLocaleString()}
                </div>
            </div>
            <div class="detail-section">
                <h4>Description</h4>
                <p>${testCase.description || 'No description'}</p>
            </div>
            <div class="detail-section">
                <h4>Preconditions</h4>
                <p>${testCase.preconditions || 'None'}</p>
            </div>
            ${testCase.tags && testCase.tags.length > 0 ? `
                <div class="detail-section">
                    <h4>Tags</h4>
                    <div>${testCase.tags.map(tag => `<span class="badge" style="background-color: ${tag.color}">${tag.name}</span>`).join(' ')}</div>
                </div>
            ` : ''}
        `;

        // Steps tab
        const stepsDiv = document.getElementById('testCaseSteps');
        if (testCase.steps && testCase.steps.length > 0) {
            stepsDiv.innerHTML = testCase.steps.map((step, index) => `
                <div class="step-detail">
                    <h5>Step ${index + 1}</h5>
                    <p><strong>Action:</strong> ${step.step_description}</p>
                    <p><strong>Expected Result:</strong> ${step.expected_result || 'N/A'}</p>
                </div>
            `).join('');
        } else {
            stepsDiv.innerHTML = '<p>No steps defined</p>';
        }

        // Load version history
        loadVersionHistory(id);

        // Setup detail action buttons
        document.getElementById('editFromDetailBtn').onclick = () => {
            closeModal('testCaseDetailModal');
            editTestCase(id);
        };
        document.getElementById('cloneFromDetailBtn').onclick = () => {
            closeModal('testCaseDetailModal');
            openCloneModal(id);
        };
        document.getElementById('createTemplateFromDetailBtn').onclick = () => {
            closeModal('testCaseDetailModal');
            openCreateTemplateModal(id);
        };

        openModal('testCaseDetailModal');
    } catch (error) {
        console.error('Failed to load test case:', error);
        showNotification('Failed to load test case details', 'error');
    }
}

// ============ Load Version History ============
async function loadVersionHistory(testCaseId) {
    try {
        const versions = await API.TestCases.getVersionHistory(testCaseId);
        const versionsDiv = document.getElementById('testCaseVersions');

        if (versions.length === 0) {
            versionsDiv.innerHTML = '<p>No version history available</p>';
            return;
        }

        versionsDiv.innerHTML = versions.map(version => `
            <div class="version-item">
                <div class="version-header">
                    <strong>Version ${version.version_number}</strong>
                    <span>${new Date(version.changed_at).toLocaleString()}</span>
                </div>
                <p><strong>Changed by:</strong> ${version.changed_by?.full_name || 'Unknown'}</p>
                <p><strong>Summary:</strong> ${version.change_summary}</p>
                ${version.changed_fields ? `<p><em>Fields changed: ${version.changed_fields}</em></p>` : ''}
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load version history:', error);
        document.getElementById('testCaseVersions').innerHTML = '<p class="text-center">Failed to load version history</p>';
    }
}

// ============ Edit Test Case ============
async function editTestCase(id) {
    try {
        const testCase = await API.TestCases.get(id);
        openTestCaseModal(testCase);
    } catch (error) {
        console.error('Failed to load test case for editing:', error);
        showNotification('Failed to load test case', 'error');
    }
}

// ============ Clone Test Case ============
function openCloneModal(id) {
    currentTestCaseForAction = { id };
    document.getElementById('cloneAttachments').checked = true;
    openModal('cloneModal');
}

async function confirmClone() {
    try {
        const cloneAttachments = document.getElementById('cloneAttachments').checked;
        const clonedTestCase = await API.TestCases.clone(currentTestCaseForAction.id, cloneAttachments);
        showNotification('Test case cloned successfully!', 'success');
        closeModal('cloneModal');
        await loadTestCases();
        viewTestCase(clonedTestCase.id);
    } catch (error) {
        console.error('Failed to clone test case:', error);
        showNotification('Failed to clone test case', 'error');
    }
}

// ============ Delete Test Case ============
function deleteTestCase(id) {
    currentTestCaseForAction = { id };
    openModal('deleteModal');
}

async function confirmDelete() {
    try {
        await API.TestCases.delete(currentTestCaseForAction.id);
        showNotification('Test case deleted successfully!', 'success');
        closeModal('deleteModal');
        await loadTestCases();
    } catch (error) {
        console.error('Failed to delete test case:', error);
        showNotification('Failed to delete test case', 'error');
    }
}

// ============ Bulk Operations ============
function openBulkUpdateModal() {
    if (selectedTestCaseIds.size === 0) {
        showNotification('Please select test cases first', 'warning');
        return;
    }

    document.getElementById('bulkUpdateCount').textContent = selectedTestCaseIds.size;
    document.getElementById('bulkUpdateForm').reset();
    openModal('bulkUpdateModal');
}

async function confirmBulkUpdate() {
    const changeSummary = document.getElementById('bulkChangeSummary').value;
    if (!changeSummary || changeSummary.length < 5) {
        showNotification('Please provide a change summary (minimum 5 characters)', 'error');
        return;
    }

    const updates = {};
    const status = document.getElementById('bulkStatus').value;
    const priority = document.getElementById('bulkPriority').value;
    const severity = document.getElementById('bulkSeverity').value;
    const assignee = document.getElementById('bulkAssignee').value;

    if (status) updates.status = status;
    if (priority) updates.priority = priority;
    if (severity) updates.severity = severity;
    if (assignee) updates.assigned_tester_id = parseInt(assignee);

    if (Object.keys(updates).length === 0) {
        showNotification('Please select at least one field to update', 'warning');
        return;
    }

    try {
        await API.Bulk.update(Array.from(selectedTestCaseIds), updates, changeSummary);
        showNotification(`Successfully updated ${selectedTestCaseIds.size} test cases!`, 'success');
        closeModal('bulkUpdateModal');
        clearSelection();
        await loadTestCases();
    } catch (error) {
        console.error('Bulk update failed:', error);
        showNotification('Bulk update failed', 'error');
    }
}

async function bulkDeleteTestCases() {
    if (selectedTestCaseIds.size === 0) {
        showNotification('Please select test cases first', 'warning');
        return;
    }

    if (!confirm(`Are you sure you want to delete ${selectedTestCaseIds.size} test cases?`)) {
        return;
    }

    try {
        await API.Bulk.delete(Array.from(selectedTestCaseIds));
        showNotification(`Successfully deleted ${selectedTestCaseIds.size} test cases!`, 'success');
        clearSelection();
        await loadTestCases();
    } catch (error) {
        console.error('Bulk delete failed:', error);
        showNotification('Bulk delete failed', 'error');
    }
}

// ============ Create Template from Test Case ============
function openCreateTemplateModal(testCaseId) {
    currentTestCaseForAction = { id: testCaseId };
    document.getElementById('createTemplateForm').reset();
    openModal('createTemplateModal');
}

async function confirmCreateTemplate() {
    const name = document.getElementById('templateName').value;
    const category = document.getElementById('templateCategory').value;
    const description = document.getElementById('templateDescription').value;

    if (!name || !category) {
        showNotification('Please fill in all required fields', 'error');
        return;
    }

    try {
        await API.Templates.create(currentTestCaseForAction.id, name, category, description);
        showNotification('Template created successfully!', 'success');
        closeModal('createTemplateModal');
    } catch (error) {
        console.error('Failed to create template:', error);
        showNotification('Failed to create template', 'error');
    }
}

// ============ Import Wizard ============
let importFile = null;
let importStep = 1;
let importBatchId = null;

function openImportModal() {
    importStep = 1;
    importFile = null;
    importBatchId = null;
    showImportStep(1);
    openModal('importModal');
}

function showImportStep(step) {
    document.querySelectorAll('.import-step').forEach(s => s.classList.remove('active'));
    document.getElementById(`importStep${step}`).classList.add('active');

    const backBtn = document.getElementById('importBackBtn');
    const nextBtn = document.getElementById('importNextBtn');

    backBtn.style.display = step > 1 && step < 4 ? 'inline-block' : 'none';

    if (step === 4) {
        nextBtn.style.display = 'none';
    } else {
        nextBtn.style.display = 'inline-block';
        nextBtn.textContent = step === 3 ? 'Confirm Import' : 'Next →';
    }
}

function handleFileSelect(e) {
    importFile = e.target.files[0];
    if (importFile) {
        document.getElementById('fileInfo').style.display = 'block';
        document.getElementById('fileName').textContent = importFile.name;
        document.getElementById('fileSize').textContent = (importFile.size / 1024).toFixed(2) + ' KB';
    }
}

function handleImportNext() {
    if (importStep === 1) {
        if (!importFile) {
            showNotification('Please select a file first', 'error');
            return;
        }
        importStep = 2;
        showImportFieldMapping();
    } else if (importStep === 2) {
        importStep = 3;
        previewImport();
    } else if (importStep === 3) {
        confirmImport();
    }
    showImportStep(importStep);
}

function handleImportBack() {
    importStep--;
    showImportStep(importStep);
}

function showImportFieldMapping() {
    const container = document.getElementById('fieldMappingContainer');
    const fields = ['title', 'description', 'priority', 'severity', 'type', 'status'];

    container.innerHTML = fields.map(field => `
        <div class="form-group">
            <label>${field.charAt(0).toUpperCase() + field.slice(1)}:</label>
            <input type="text" class="form-control" data-field="${field}" placeholder="Column name in your file" value="${field}">
        </div>
    `).join('');
}

async function previewImport() {
    try {
        const fieldMapping = {};
        document.querySelectorAll('[data-field]').forEach(input => {
            fieldMapping[input.getAttribute('data-field')] = input.value;
        });

        showNotification('Processing file...', 'info');
        const result = await API.Import.preview(importFile, fieldMapping);
        importBatchId = result.batch_id;

        const summary = document.getElementById('importSummary');
        summary.innerHTML = `
            <div class="alert alert-info">
                <strong>Import Summary:</strong><br>
                Total records: ${result.total_records}<br>
                Valid records: ${result.valid_records}<br>
                Invalid records: ${result.invalid_records}
            </div>
        `;

        const preview = document.getElementById('importPreview');
        if (result.errors && result.errors.length > 0) {
            preview.innerHTML = `
                <h4>Validation Errors:</h4>
                <ul>
                    ${result.errors.map(err => `<li>Row ${err.row}: ${err.message}</li>`).join('')}
                </ul>
            `;
        } else {
            preview.innerHTML = '<p class="text-center">All records are valid! Ready to import.</p>';
        }
    } catch (error) {
        console.error('Preview failed:', error);
        showNotification('Failed to preview import', 'error');
        importStep = 1;
        showImportStep(1);
    }
}

async function confirmImport() {
    try {
        showNotification('Importing test cases...', 'info');
        const result = await API.Import.confirm(importBatchId);

        importStep = 4;
        showImportStep(4);

        document.getElementById('importResults').innerHTML = `
            <p><strong>Import completed successfully!</strong></p>
            <p>Created: ${result.created_count} test cases</p>
            <p>Skipped: ${result.skipped_count} records</p>
        `;

        await loadTestCases();
    } catch (error) {
        console.error('Import failed:', error);
        showNotification('Import failed', 'error');
    }
}

// ============ Execution Module UI ============
async function loadExecutionDashboardData() {
    try {
        await loadExecutionCaseSelectors();
        await renderTestRunsTable();
        await refreshDashboardExecutionKpiSample();
    } catch (error) {
        console.error('Failed to load execution dashboard data:', error);
        showNotification('Failed to load execution module', 'error');
    }
}

async function loadExecutionCaseSelectors() {
    const caseSelect = document.getElementById('executionTestCaseSelect');
    const runCasesSelect = document.getElementById('runTestCasesSelect');
    if (!caseSelect || !runCasesSelect) return;

    if (!allTestCases || allTestCases.length === 0) {
        await loadTestCases();
    }

    const options = allTestCases.map(tc => `<option value="${tc.id}">${tc.test_case_id} - ${tc.title}</option>`).join('');
    caseSelect.innerHTML = `<option value="">Select test case...</option>${options}`;
    runCasesSelect.innerHTML = options;
}

function openExecutionFromTable(testCaseId) {
    switchView('executions');
    const select = document.getElementById('executionTestCaseSelect');
    if (select) {
        select.value = String(testCaseId);
    }
    refreshExecutionHistoryFromSelection();
}

async function startExecutionFromSelection() {
    const testCaseId = parseInt(document.getElementById('executionTestCaseSelect').value);
    if (!testCaseId) {
        showNotification('Select a test case first', 'warning');
        return;
    }

    try {
        const execution = await API.Execution.start(testCaseId, {
            environment: 'qa',
            browser: navigator.userAgent.includes('Chrome') ? 'chrome' : 'browser',
            os: navigator.platform || 'unknown'
        });

        activeExecutionId = execution.execution_id;
        activeExecutionTestCaseId = testCaseId;
        await loadExecutionSteps(testCaseId);
        startLocalExecutionTimer();
        await refreshExecutionHistoryFromSelection();
        await refreshDashboardExecutionKpiSample();
        showNotification('Execution started', 'success');
    } catch (error) {
        console.error('Failed to start execution:', error);
        showNotification(error.message || 'Failed to start execution', 'error');
    }
}

async function reexecuteFromSelection() {
    const testCaseId = parseInt(document.getElementById('executionTestCaseSelect').value);
    if (!testCaseId) {
        showNotification('Select a test case first', 'warning');
        return;
    }

    try {
        const response = await API.Execution.reexecute(testCaseId, {
            environment: 'qa',
            browser: navigator.userAgent.includes('Chrome') ? 'chrome' : 'browser',
            os: navigator.platform || 'unknown'
        });

        activeExecutionId = response.execution_id;
        activeExecutionTestCaseId = testCaseId;
        await loadExecutionSteps(testCaseId);
        startLocalExecutionTimer();
        await refreshExecutionHistoryFromSelection();
        await refreshDashboardExecutionKpiSample();

        if (response.previous_execution) {
            showNotification(`Re-execution started. Previous status: ${response.previous_execution.status}`, 'info');
        } else {
            showNotification('Re-execution started', 'success');
        }
    } catch (error) {
        console.error('Failed to re-execute:', error);
        showNotification(error.message || 'Failed to re-execute', 'error');
    }
}

async function loadExecutionSteps(testCaseId) {
    const tbody = document.getElementById('executionStepsBody');
    if (!tbody) return;

    try {
        if (!activeExecutionId) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center">Start execution to load step snapshots</td></tr>';
            return;
        }

        activeExecutionSteps = await API.Execution.getSteps(activeExecutionId);

        if (activeExecutionSteps.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center">No steps found for this test case</td></tr>';
            return;
        }

        tbody.innerHTML = activeExecutionSteps.map((step, idx) => {
            const stepLabel = step.step_number || (idx + 1);
            return `
                <tr>
                    <td>${stepLabel}</td>
                    <td>${step.action || step.step_description || ''}</td>
                    <td>${step.expected_result || ''}</td>
                    <td>
                        <select id="stepStatus_${step.id}" class="form-control" style="min-width: 130px;">
                            <option value="not_executed" ${step.status === 'not_executed' ? 'selected' : ''}>Not Executed</option>
                            <option value="pass" ${step.status === 'pass' ? 'selected' : ''}>Pass</option>
                            <option value="fail" ${step.status === 'fail' ? 'selected' : ''}>Fail</option>
                            <option value="blocked" ${step.status === 'blocked' ? 'selected' : ''}>Blocked</option>
                            <option value="skipped" ${step.status === 'skipped' ? 'selected' : ''}>Skipped</option>
                        </select>
                    </td>
                    <td><input id="stepActual_${step.id}" class="form-control" value="${step.actual_result || ''}" placeholder="Actual result"></td>
                    <td><input id="stepNotes_${step.id}" class="form-control" value="${step.notes || ''}" placeholder="Notes"></td>
                    <td style="display:flex; gap:6px; flex-wrap: wrap;">
                        <button class="btn btn-sm btn-primary" onclick="saveExecutionStep(${step.id})">Save</button>
                        <button class="btn btn-sm btn-danger" onclick="failAndCreateBugForStep(${step.id})">Fail & Bug</button>
                        <button class="btn btn-sm btn-secondary" onclick="selectExecutionStep(${step.id})">Select</button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Failed to load execution steps:', error);
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">Failed to load steps</td></tr>';
    }
}

function selectExecutionStep(stepId) {
    selectedExecutionStepId = stepId;
    showNotification(`Selected step ${stepId} for evidence upload`, 'info');
}

async function saveExecutionStep(stepId) {
    if (!activeExecutionId) {
        showNotification('Start execution first', 'warning');
        return;
    }

    try {
        const status = document.getElementById(`stepStatus_${stepId}`).value;
        const actualResult = document.getElementById(`stepActual_${stepId}`).value;
        const notes = document.getElementById(`stepNotes_${stepId}`).value;

        await API.Execution.autosaveStep(activeExecutionId, stepId, {
            status,
            actual_result: actualResult || null,
            notes: notes || null
        });
        selectedExecutionStepId = stepId;
        showNotification('Step saved (auto-save)', 'success');
    } catch (error) {
        console.error('Failed to save execution step:', error);
        showNotification(error.message || 'Failed to save step', 'error');
    }
}

async function failAndCreateBugForStep(stepId) {
    if (!activeExecutionId) {
        showNotification('Start execution first', 'warning');
        return;
    }

    const summary = document.getElementById('bugSummary').value?.trim();
    const description = document.getElementById('bugDescription').value?.trim();

    if (!summary) {
        showNotification('Enter bug summary first', 'warning');
        return;
    }

    try {
        const result = await API.Execution.failAndCreateBug(activeExecutionId, stepId, {
            summary,
            description: description || null,
            affected_version: document.getElementById('bugCreateVersion')?.value?.trim() || null,
            assigned_to_id: parseInt(document.getElementById('bugCreateAssignedTo')?.value) || null
        });
        document.getElementById(`stepStatus_${stepId}`).value = 'fail';
        await saveExecutionStep(stepId);
        if (document.getElementById('bugsView')?.classList.contains('active')) {
            await loadBugReportsView();
        }
        await refreshDashboardOpenBugKpi();
        showNotification(`Bug created: ${result.bug.id}`, 'success');
    } catch (error) {
        console.error('Fail and create bug failed:', error);
        showNotification(error.message || 'Failed to create bug', 'error');
    }
}

async function uploadExecutionEvidenceForSelectedStep() {
    if (!activeExecutionId) {
        showNotification('Start execution first', 'warning');
        return;
    }
    if (!selectedExecutionStepId) {
        showNotification('Select a step first', 'warning');
        return;
    }

    const fileInput = document.getElementById('executionEvidenceFile');
    const file = fileInput?.files?.[0];
    if (!file) {
        showNotification('Choose a file to upload', 'warning');
        return;
    }

    try {
        await API.Execution.uploadEvidence(activeExecutionId, selectedExecutionStepId, file);
        showNotification('Evidence uploaded', 'success');
        fileInput.value = '';
    } catch (error) {
        console.error('Evidence upload failed:', error);
        showNotification(error.message || 'Evidence upload failed', 'error');
    }
}

async function pauseExecutionTimer() {
    if (!activeExecutionId) {
        showNotification('No active execution', 'warning');
        return;
    }
    try {
        await API.Execution.pauseTimer(activeExecutionId);
        stopLocalExecutionTimer();
        showNotification('Timer paused', 'info');
    } catch (error) {
        console.error('Pause timer failed:', error);
        showNotification(error.message || 'Failed to pause timer', 'error');
    }
}

async function resumeExecutionTimer() {
    if (!activeExecutionId) {
        showNotification('No active execution', 'warning');
        return;
    }
    try {
        await API.Execution.resumeTimer(activeExecutionId);
        startLocalExecutionTimer();
        showNotification('Timer resumed', 'info');
    } catch (error) {
        console.error('Resume timer failed:', error);
        showNotification(error.message || 'Failed to resume timer', 'error');
    }
}

async function setExecutionManualDuration() {
    if (!activeExecutionId) {
        showNotification('No active execution', 'warning');
        return;
    }
    const minutes = parseFloat(document.getElementById('manualDurationInput').value);
    if (Number.isNaN(minutes) || minutes < 0) {
        showNotification('Enter valid manual minutes', 'warning');
        return;
    }

    try {
        await API.Execution.setManualDuration(activeExecutionId, minutes);
        showNotification('Manual duration set', 'success');
    } catch (error) {
        console.error('Set manual duration failed:', error);
        showNotification(error.message || 'Failed to set manual duration', 'error');
    }
}

async function completeCurrentExecution() {
    if (!activeExecutionId) {
        showNotification('No active execution', 'warning');
        return;
    }

    try {
        const result = await API.Execution.complete(activeExecutionId);
        stopLocalExecutionTimer();
        showNotification(`Execution completed: ${result.status}`, 'success');
        await refreshExecutionHistoryFromSelection();
        await refreshDashboardExecutionKpiSample();
    } catch (error) {
        console.error('Complete execution failed:', error);
        showNotification(error.message || 'Failed to complete execution', 'error');
    }
}

function startLocalExecutionTimer() {
    stopLocalExecutionTimer();
    executionTimerStart = Date.now();
    executionTimerInterval = setInterval(() => {
        const elapsedSeconds = executionAccumulatedSeconds + Math.floor((Date.now() - executionTimerStart) / 1000);
        const mins = String(Math.floor(elapsedSeconds / 60)).padStart(2, '0');
        const secs = String(elapsedSeconds % 60).padStart(2, '0');
        const display = document.getElementById('executionTimerDisplay');
        if (display) display.textContent = `Timer: ${mins}:${secs}`;
    }, 1000);
}

function stopLocalExecutionTimer() {
    if (executionTimerInterval) {
        clearInterval(executionTimerInterval);
        executionTimerInterval = null;
        if (executionTimerStart) {
            executionAccumulatedSeconds += Math.floor((Date.now() - executionTimerStart) / 1000);
            executionTimerStart = null;
        }
    }
}

async function refreshExecutionHistoryFromSelection() {
    const testCaseId = parseInt(document.getElementById('executionTestCaseSelect').value);
    if (!testCaseId) {
        document.getElementById('executionHistoryBody').innerHTML = '<tr><td colspan="6" class="text-center">Select a test case to load history</td></tr>';
        return;
    }

    try {
        const rows = await API.Execution.history(testCaseId);
        const body = document.getElementById('executionHistoryBody');
        if (!rows || rows.length === 0) {
            updateDashboardExecutionKpiFromRows([]);
            body.innerHTML = '<tr><td colspan="6" class="text-center">No execution history found</td></tr>';
            return;
        }

        updateDashboardExecutionKpiFromRows(rows);

        body.innerHTML = rows.map(r => `
            <tr>
                <td>${r.id}</td>
                <td>${r.status}</td>
                <td>${r.execution_duration ?? 'N/A'}</td>
                <td>${r.pass_count}/${r.fail_count}/${r.blocked_count}/${r.skipped_count}</td>
                <td>${r.execution_date ? new Date(r.execution_date).toLocaleString() : 'In Progress'}</td>
                <td><button class="btn btn-sm btn-secondary" onclick="compareExecutionHistory(${r.id})">Compare</button></td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load execution history:', error);
        document.getElementById('executionHistoryBody').innerHTML = '<tr><td colspan="6" class="text-center">Failed to load history</td></tr>';
    }
}

async function compareExecutionHistory(executionId) {
    const body = document.getElementById('executionComparisonBody');
    if (!body) return;

    body.innerHTML = '<tr><td colspan="5" class="text-center">Loading comparison...</td></tr>';

    try {
        const result = await API.Execution.compare(executionId);
        if (!result.previous_execution) {
            body.innerHTML = '<tr><td colspan="5" class="text-center">No previous execution available for comparison</td></tr>';
            return;
        }

        body.innerHTML = result.comparison.map((row) => `
            <tr>
                <td>${row.step_number}</td>
                <td>${row.action || ''}</td>
                <td>${row.expected_result || ''}</td>
                <td>${row.current?.status || 'n/a'}${row.current?.actual_result ? `<br><small>${row.current.actual_result}</small>` : ''}</td>
                <td>${row.previous?.status || 'n/a'}${row.previous?.actual_result ? `<br><small>${row.previous.actual_result}</small>` : ''}</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to compare execution history:', error);
        body.innerHTML = '<tr><td colspan="5" class="text-center">Failed to load comparison</td></tr>';
    }
}

async function createTestRunFromForm() {
    const name = document.getElementById('runName').value?.trim();
    if (!name) {
        showNotification('Run name is required', 'warning');
        return;
    }

    const selectedCaseIds = Array.from(document.getElementById('runTestCasesSelect').selectedOptions).map(o => parseInt(o.value));
    if (selectedCaseIds.length === 0) {
        showNotification('Select at least one test case for the run', 'warning');
        return;
    }

    const testerIds = Array.from(document.getElementById('runTestersSelect').selectedOptions).map(o => parseInt(o.value));
    const startDate = document.getElementById('runStartDate').value;
    const endDate = document.getElementById('runEndDate').value;

    try {
        await API.TestRuns.create({
            name,
            description: 'Created from execution dashboard',
            target_start_date: startDate ? new Date(startDate).toISOString() : null,
            target_end_date: endDate ? new Date(endDate).toISOString() : null,
            test_case_ids: selectedCaseIds,
            tester_ids: testerIds
        });
        showNotification('Test run created', 'success');
        await renderTestRunsTable();
    } catch (error) {
        console.error('Failed to create test run:', error);
        showNotification(error.message || 'Failed to create run', 'error');
    }
}

async function renderTestRunsTable() {
    const tbody = document.getElementById('testRunsTableBody');
    if (!tbody) return;

    try {
        const runs = await API.TestRuns.list();
        if (!runs || runs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center">No test runs yet</td></tr>';
            return;
        }

        tbody.innerHTML = runs.map(run => `
            <tr>
                <td>${run.name}</td>
                <td>${run.status}</td>
                <td>${run.progress?.completed || 0}/${run.progress?.total || 0} (${run.progress?.progress_percent || 0}%)</td>
                <td>${run.target_end_date ? new Date(run.target_end_date).toLocaleString() : 'N/A'}</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load test runs:', error);
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">Failed to load test runs</td></tr>';
    }
}

// ============ Tab Switching ============
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.querySelector(`[data-tab-content="${tabName}"]`).classList.add('active');
}

// ============ Utility Functions ============
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    element.innerHTML = `
        <tr class="loading-row">
            <td colspan="10" class="text-center">
                <div class="spinner"></div>
                Loading...
            </td>
        </tr>
    `;
}

function showError(elementId, message) {
    const element = document.getElementById(elementId);
    element.innerHTML = `<tr><td colspan="10" class="text-center">${message}</td></tr>`;
}

function showNotification(message, type = 'info') {
    // Create notification container if it doesn't exist
    let container = document.getElementById('notificationContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notificationContainer';
        container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 10000; max-width: 400px;';
        document.body.appendChild(container);
    }

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;

    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    };

    notification.innerHTML = `
        <span class="notification-icon">${icons[type] || 'ℹ'}</span>
        <span class="notification-message">${message}</span>
        <button class="notification-close" onclick="this.parentElement.remove()">×</button>
    `;

    notification.style.cssText = `
        background: ${type === 'success' ? '#d4edda' : type === 'error' ? '#f8d7da' : type === 'warning' ? '#fff3cd' : '#d1ecf1'};
        color: ${type === 'success' ? '#155724' : type === 'error' ? '#721c24' : type === 'warning' ? '#856404' : '#0c5460'};
        border: 1px solid ${type === 'success' ? '#c3e6cb' : type === 'error' ? '#f5c6cb' : type === 'warning' ? '#ffeaa7' : '#bee5eb'};
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        animation: slideIn 0.3s ease;
    `;

    container.appendChild(notification);

    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Add animations
if (!document.getElementById('notificationStyles')) {
    const style = document.createElement('style');
    style.id = 'notificationStyles';
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
        .notification-icon {
            font-size: 20px;
            font-weight: bold;
        }
        .notification-message {
            flex: 1;
        }
        .notification-close {
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: inherit;
            padding: 0;
            line-height: 1;
        }
    `;
    document.head.appendChild(style);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
