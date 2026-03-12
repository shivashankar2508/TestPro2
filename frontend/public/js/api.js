// API Service Layer - Handles all backend API calls
const API_BASE_URL = 'http://localhost:8000/api';

// ============ Auth Helper ============
function getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    const headers = {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
    };
    console.log('[API] Auth Headers:', {
        hasToken: !!token,
        headerValue: headers['Authorization'],
        tokenLength: token ? token.length : 0,
        timestamp: new Date().toISOString()
    });
    return headers;
}

// Track if we're currently loading the dashboard
let isDashboardInitializing = true;

function handleApiError(error) {
    console.error('API Error Details:', {
        status: error.status,
        message: error.message,
        detail: error.detail,
        endpoint: error.endpoint,
        isDashboardInitializing: isDashboardInitializing,
        timestamp: new Date().toISOString()
    });

    // Handle 401 and 403 - but DON'T redirect during dashboard initialization
    // Just throw the error and let the dashboard retry logic handle it
    if ((error.status === 401 || error.status === 403) && !isDashboardInitializing) {
        console.error('Session expired - redirecting to login');
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        setTimeout(() => {
            window.location.href = '/login';
        }, 500);
        throw new Error('Session expired. Please log in again.');
    }

    throw error;
}

// ============ Generic API Call ============
async function apiCall(endpoint, options = {}) {
    console.log('[API] Request:', { endpoint, method: options.method || 'GET', timestamp: new Date().toISOString() });

    try {
        const finalHeaders = {
            ...getAuthHeaders(),
            ...options.headers
        };

        console.log('[API] Final Headers Being Sent:', {
            'Content-Type': finalHeaders['Content-Type'],
            'Authorization_Prefix': finalHeaders['Authorization'] ? finalHeaders['Authorization'].substring(0, 50) + '...' : 'MISSING',
            'Authorization_Exists': !!finalHeaders['Authorization'],
            allHeaders: Object.keys(finalHeaders)
        });

        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers: finalHeaders
        });

        console.log('[API] Response:', {
            endpoint,
            status: response.status,
            statusText: response.statusText,
            timestamp: new Date().toISOString()
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            console.error('[API] Error Response:', {
                endpoint,
                status: response.status,
                errorDetail: error.detail,
                fullError: error
            });
            throw {
                status: response.status,
                message: error.detail || error.message || 'Request failed',
                endpoint: endpoint,
                ...error
            };
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            console.log('[API] Response Data:', { endpoint, dataKeys: Object.keys(data || {}) });
            return data;
        }

        return response;
    } catch (error) {
        console.error('[API] Catch Error:', { endpoint, errorMessage: error.message, error });
        return handleApiError(error);
    }
}

// ============ Authentication APIs ============
const AuthAPI = {
    async getCurrentUser() {
        return apiCall('/users/me');
    },

    async logout() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
    }
};

// ============ Users APIs ============
const UsersAPI = {
    async listUsers(role = null) {
        const params = new URLSearchParams();
        if (role) params.append('role', role);
        return apiCall(`/users?${params.toString()}`);
    },

    async getTesterUsers() {
        try {
            return await apiCall('/users/testers');
        } catch (error) {
            // Fallback for older backend deployments.
            return this.listUsers('tester');
        }
    }
};

// ============ Test Cases APIs ============
const TestCasesAPI = {
    // List and filter test cases
    async list(filters = {}) {
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== null && value !== undefined && value !== '') {
                params.append(key, value);
            }
        });
        return apiCall(`/test-cases?${params.toString()}`);
    },

    // Get single test case
    async get(id) {
        return apiCall(`/test-cases/${id}`);
    },

    // Create test case
    async create(data) {
        return apiCall('/test-cases', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    // Update test case
    async update(id, data, changeSummary) {
        const params = new URLSearchParams({ change_summary: changeSummary });
        return apiCall(`/test-cases/${id}?${params.toString()}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    // Delete test case (soft delete)
    async delete(id) {
        return apiCall(`/test-cases/${id}`, {
            method: 'DELETE',
            body: JSON.stringify({ confirm: true })
        });
    },

    // Clone test case
    async clone(id, cloneAttachments = true) {
        return apiCall(`/test-cases/${id}/clone`, {
            method: 'POST',
            body: JSON.stringify({ clone_attachments: cloneAttachments })
        });
    },

    // Get version history
    async getVersionHistory(id) {
        return apiCall(`/test-cases/${id}/versions`);
    },

    // Restore deleted test case (admin only)
    async restore(id) {
        return apiCall(`/test-cases/${id}/restore`, {
            method: 'POST'
        });
    },

    // Permanent delete (admin only)
    async permanentDelete(id) {
        return apiCall(`/test-cases/${id}/permanent`, {
            method: 'DELETE'
        });
    }
};

// ============ Templates APIs ============
const TemplatesAPI = {
    // List templates
    async list(category = null) {
        const params = new URLSearchParams();
        if (category) params.append('category', category);
        return apiCall(`/test-cases/templates?${params.toString()}`);
    },

    // Create template from test case
    async create(testCaseId, name, category, description) {
        return apiCall('/test-cases/templates', {
            method: 'POST',
            body: JSON.stringify({
                source_test_case_id: testCaseId,
                name,
                category,
                description
            })
        });
    },

    // Create test case from template
    async createTestCase(templateId) {
        return apiCall(`/test-cases/templates/${templateId}/create`, {
            method: 'POST',
            body: JSON.stringify({
                project_id: 1,
                module: 'General'
            })
        });
    }
};

// ============ Bulk Operations APIs ============
const BulkAPI = {
    // Bulk update
    async update(testCaseIds, updates, changeSummary) {
        return apiCall('/test-cases/bulk/update', {
            method: 'POST',
            body: JSON.stringify({
                test_case_ids: testCaseIds,
                change_summary: changeSummary,
                ...updates
            })
        });
    },

    // Bulk delete
    async delete(testCaseIds) {
        return apiCall('/test-cases/bulk/delete', {
            method: 'POST',
            body: JSON.stringify({
                test_case_ids: testCaseIds,
                confirm: true
            })
        });
    },

    // Export test cases
    async export(format = 'csv', filters = {}) {
        const params = new URLSearchParams({ format, ...filters });
        const response = await fetch(`${API_BASE_URL}/test-cases/bulk/export?${params.toString()}`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error('Export failed');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `test-cases-${Date.now()}.${format}`;
        a.click();
        window.URL.revokeObjectURL(url);
    }
};

// ============ Import APIs ============
const ImportAPI = {
    // Preview import
    async preview(file, fieldMapping) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('field_mapping', JSON.stringify(fieldMapping));

        const token = localStorage.getItem('access_token');
        const response = await fetch(`${API_BASE_URL}/test-cases/import/preview`, {
            method: 'POST',
            headers: {
                'Authorization': token ? `Bearer ${token}` : ''
            },
            body: formData
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw {
                status: response.status,
                message: error.detail || 'Preview failed',
                ...error
            };
        }

        return await response.json();
    },

    // Confirm import
    async confirm(batchId) {
        return apiCall(`/test-cases/import/confirm`, {
            method: 'POST',
            body: JSON.stringify({ batch_id: batchId })
        });
    }
};

// ============ Test Steps APIs ============
const TestStepsAPI = {
    // Create step
    async create(testCaseId, data, changeSummary) {
        const params = new URLSearchParams({ change_summary: changeSummary });
        return apiCall(`/test-cases/${testCaseId}/steps?${params.toString()}`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    // Update step
    async update(testCaseId, stepId, data, changeSummary) {
        const params = new URLSearchParams({ change_summary: changeSummary });
        return apiCall(`/test-cases/${testCaseId}/steps/${stepId}?${params.toString()}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    // Delete step
    async delete(testCaseId, stepId, changeSummary) {
        const params = new URLSearchParams({ change_summary: changeSummary });
        return apiCall(`/test-cases/${testCaseId}/steps/${stepId}?${params.toString()}`, {
            method: 'DELETE'
        });
    }
};

// ============ Execution APIs ============
const ExecutionAPI = {
    async start(testCaseId, payload = {}) {
        return apiCall(`/test-cases/${testCaseId}/executions/start`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    async autosaveStep(executionId, stepId, payload) {
        return apiCall(`/test-cases/executions/${executionId}/steps/${stepId}/autosave`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    async getSteps(executionId) {
        return apiCall(`/test-cases/executions/${executionId}/steps`);
    },

    async complete(executionId) {
        return apiCall(`/test-cases/executions/${executionId}/complete`, {
            method: 'POST'
        });
    },

    async history(testCaseId) {
        return apiCall(`/test-cases/${testCaseId}/executions/history`);
    },

    async compare(executionId) {
        return apiCall(`/test-cases/executions/${executionId}/compare`);
    },

    async reexecute(testCaseId, payload = {}) {
        return apiCall(`/test-cases/${testCaseId}/executions/reexecute`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    async failAndCreateBug(executionId, stepId, payload) {
        return apiCall(`/test-cases/executions/${executionId}/steps/${stepId}/fail-and-create-bug`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    async pauseTimer(executionId) {
        return apiCall(`/test-cases/executions/${executionId}/timer/pause`, {
            method: 'POST'
        });
    },

    async resumeTimer(executionId) {
        return apiCall(`/test-cases/executions/${executionId}/timer/resume`, {
            method: 'POST'
        });
    },

    async setManualDuration(executionId, durationMinutes) {
        return apiCall(`/test-cases/executions/${executionId}/timer/manual`, {
            method: 'POST',
            body: JSON.stringify({ duration_minutes: durationMinutes })
        });
    },

    async uploadEvidence(executionId, stepId, file) {
        const formData = new FormData();
        formData.append('file', file);
        const token = localStorage.getItem('access_token');
        const query = new URLSearchParams();
        if (stepId) query.append('step_id', stepId);
        const response = await fetch(`${API_BASE_URL}/test-cases/executions/${executionId}/evidence?${query.toString()}`, {
            method: 'POST',
            headers: {
                'Authorization': token ? `Bearer ${token}` : ''
            },
            body: formData
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw {
                status: response.status,
                message: error.detail || error.message || 'Evidence upload failed',
                ...error
            };
        }
        return await response.json();
    }
};

// ============ Test Run APIs ============
const TestRunsAPI = {
    async create(payload) {
        return apiCall('/test-cases/runs', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    async list() {
        return apiCall('/test-cases/runs');
    },

    async get(runId) {
        return apiCall(`/test-cases/runs/${runId}`);
    },

    async assign(runId, testerIds) {
        return apiCall(`/test-cases/runs/${runId}/assign`, {
            method: 'PUT',
            body: JSON.stringify({ tester_ids: testerIds })
        });
    }
};

// ============ Bug Reports API ============
const BugsAPI = {
    async list(filters = {}) {
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== null && value !== undefined && value !== '') {
                params.append(key, value);
            }
        });
        return apiCall(`/bugs?${params.toString()}`);
    },

    async create(payload) {
        return apiCall('/bugs', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    async get(bugId) {
        return apiCall(`/bugs/${bugId}`);
    },

    async updateStatus(bugId, status) {
        return apiCall(`/bugs/${bugId}/status`, {
            method: 'PUT',
            body: JSON.stringify({ status })
        });
    },

    async getAssignees() {
        return apiCall('/bugs/meta/assignees');
    }
};

// ============ Projects API ============
const ProjectsAPI = {
    async list(filters = {}) {
        const params = new URLSearchParams(filters);
        return apiCall(`/projects?${params.toString()}`);
    },

    async create(projectData) {
        return apiCall('/projects', {
            method: 'POST',
            body: JSON.stringify(projectData)
        });
    },

    async get(projectId) {
        return apiCall(`/projects/${projectId}`);
    },

    async update(projectId, projectData) {
        return apiCall(`/projects/${projectId}`, {
            method: 'PUT',
            body: JSON.stringify(projectData)
        });
    },

    async delete(projectId) {
        return apiCall(`/projects/${projectId}`, {
            method: 'DELETE'
        });
    },

    async addMember(projectId, userId, role) {
        return apiCall(`/projects/${projectId}/members`, {
            method: 'POST',
            body: JSON.stringify({ user_id: userId, role })
        });
    },

    async removeMember(projectId, userId) {
        return apiCall(`/projects/${projectId}/members/${userId}`, {
            method: 'DELETE'
        });
    }
};

// ============ System Configuration API ============
const SystemAPI = {
    async getConfig() {
        return apiCall('/system/config');
    },

    async getConfigByKey(key) {
        return apiCall(`/system/config/${key}`);
    },

    async updateConfig(key, value) {
        return apiCall(`/system/config/${key}`, {
            method: 'PUT',
            body: JSON.stringify({ value })
        });
    },

    async getStats() {
        return apiCall('/system/stats');
    },

    async healthCheck() {
        return apiCall('/system/health-check', {
            method: 'POST'
        });
    }
};

// ============ Backups API ============
const BackupsAPI = {
    async list(filters = {}) {
        const params = new URLSearchParams(filters);
        return apiCall(`/backups?${params.toString()}`);
    },

    async trigger(backupType = 'full') {
        return apiCall(`/backups/trigger?backup_type=${backupType}`, {
            method: 'POST'
        });
    },

    async get(backupId) {
        return apiCall(`/backups/${backupId}`);
    },

    async delete(backupId) {
        return apiCall(`/backups/${backupId}`, {
            method: 'DELETE'
        });
    },

    async restore(backupId) {
        return apiCall(`/backups/restore/${backupId}`, {
            method: 'POST'
        });
    },

    async cleanupOldBackups(retentionDays = 30) {
        return apiCall(`/backups/cleanup-old-backups?retention_days=${retentionDays}`, {
            method: 'POST'
        });
    }
};

// ============ Permissions API ============
const PermissionsAPI = {
    async list(category = null) {
        const params = category ? `?category=${category}` : '';
        return apiCall(`/permissions${params}`);
    },

    async create(permissionData) {
        return apiCall('/permissions', {
            method: 'POST',
            body: JSON.stringify(permissionData)
        });
    },

    async getRolePermissions(role) {
        return apiCall(`/permissions/role/${role}`);
    },

    async assignPermission(role, permissionId) {
        return apiCall('/permissions/assign', {
            method: 'POST',
            body: JSON.stringify({ role, permission_id: permissionId })
        });
    },

    async revokePermission(role, permissionId) {
        return apiCall(`/permissions/revoke/${role}/${permissionId}`, {
            method: 'DELETE'
        });
    },

    async initializeDefaults() {
        return apiCall('/permissions/initialize-defaults', {
            method: 'POST'
        });
    }
};

// ============ Export all APIs ============
function legacyApiCall(endpoint, method = 'GET', data = null) {
    // Backward compatibility for pages still calling API.apiCall('/api/...', 'METHOD', data)
    let normalizedEndpoint = endpoint || '';
    if (normalizedEndpoint.startsWith('/api/')) {
        normalizedEndpoint = normalizedEndpoint.substring(4);
    }

    const options = { method };
    if (data !== null && data !== undefined && method !== 'GET' && method !== 'HEAD') {
        options.body = JSON.stringify(data);
    }

    return apiCall(normalizedEndpoint, options);
}

window.API = {
    apiCall: legacyApiCall,
    Auth: AuthAPI,
    Users: UsersAPI,
    TestCases: TestCasesAPI,
    Templates: TemplatesAPI,
    Bulk: BulkAPI,
    Import: ImportAPI,
    TestSteps: TestStepsAPI,
    Execution: ExecutionAPI,
    TestRuns: TestRunsAPI,
    Bugs: BugsAPI,
    Projects: ProjectsAPI,
    System: SystemAPI,
    Backups: BackupsAPI,
    Permissions: PermissionsAPI
};
