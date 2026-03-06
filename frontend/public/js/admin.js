// ============ Admin Panel JS ============

// Check auth on page load
document.addEventListener('DOMContentLoaded', async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login';
        return;
    }

    try {
        const user = await API.Auth.getCurrentUser();
        if (user.role !== 'admin') {
            alert('Access denied. Admin privileges required.');
            window.location.href = '/dashboard';
            return;
        }
        setupEventListeners();
        loadDashboard();
    } catch (error) {
        console.error('Auth check failed:', error);
        window.location.href = '/login';
    }
});

// ============ Event Listeners ============

function setupEventListeners() {
    // Navigation
    document.querySelectorAll('.nav-link[data-section]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const section = link.dataset.section;
            switchSection(section);
            link.parentElement.querySelectorAll('a').forEach(a => a.classList.remove('active'));
            link.classList.add('active');
        });
    });

    // Logout
    document.getElementById('logoutBtn').addEventListener('click', (e) => {
        e.preventDefault();
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
    });

    // Dashboard
    document.getElementById('healthCheckBtn')?.addEventListener('click', runHealthCheck);

    // Users
    document.getElementById('addUserBtn')?.addEventListener('click', () => openUserModal());
    document.getElementById('userForm')?.addEventListener('submit', saveUser);

    // Projects
    document.getElementById('addProjectBtn')?.addEventListener('click', () => openProjectModal());
    document.getElementById('projectForm')?.addEventListener('submit', saveProject);
    document.getElementById('projectStatusFilter')?.addEventListener('change', loadProjects);

    // Permissions
    document.getElementById('initializePermissionsBtn')?.addEventListener('click', initializePermissions);
    document.getElementById('roleSelect')?.addEventListener('change', loadRolePermissions);
    document.getElementById('assignPermissionBtn')?.addEventListener('click', assignPermission);

    // Backups
    document.getElementById('fullBackupBtn')?.addEventListener('click', () => triggerBackup('full'));
    document.getElementById('incrementalBackupBtn')?.addEventListener('click', () => triggerBackup('incremental'));
    document.getElementById('testCasesBackupBtn')?.addEventListener('click', () => triggerBackup('test_cases'));

    // Modal closing
    document.querySelectorAll('.modal-close').forEach(closeBtn => {
        closeBtn.addEventListener('click', (e) => {
            e.target.closest('.modal').classList.remove('active');
        });
    });

    // Modals click outside to close
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.classList.remove('active');
        }
    });
}

// ============ Section Switching ============

function switchSection(section) {
    document.querySelectorAll('.admin-section').forEach(el => el.classList.remove('active'));
    document.getElementById(`${section}-section`)?.classList.add('active');

    // Load data based on section
    switch (section) {
        case 'users':
            loadUsers();
            break;
        case 'projects':
            loadProjects();
            break;
        case 'permissions':
            loadPermissions();
            break;
        case 'system':
            loadSystemConfig();
            break;
        case 'backups':
            loadBackups();
            break;
        case 'audit-logs':
            loadAuditLogs();
            break;
    }
}

// ============ Dashboard ============

async function loadDashboard() {
    try {
        const stats = await fetch(`${API_BASE_URL}/system/stats`, {
            headers: getAuthHeaders()
        }).then(r => r.json());

        document.getElementById('totalUsers').textContent = stats.total_users;
        document.getElementById('activeUsers').textContent = stats.active_users;
        document.getElementById('totalProjects').textContent = stats.total_projects || 0;
        document.getElementById('totalTestCases').textContent = stats.total_test_cases || 0;
        document.getElementById('totalExecutions').textContent = stats.total_executions || 0;
        document.getElementById('lastBackup').textContent = stats.last_backup
            ? new Date(stats.last_backup).toLocaleDateString()
            : 'Never';
    } catch (error) {
        console.error('Failed to load dashboard:', error);
    }
}

async function runHealthCheck() {
    const resultDiv = document.getElementById('healthCheckResult');
    resultDiv.textContent = 'Running health check...';
    resultDiv.className = '';

    try {
        const response = await fetch(`${API_BASE_URL}/system/health-check`, {
            method: 'POST',
            headers: getAuthHeaders()
        }).then(r => r.json());

        if (response.status === 'healthy') {
            resultDiv.innerHTML = `<strong>✓ System Healthy</strong><br>Database: ${response.database}`;
            resultDiv.className = 'success';
        } else {
            resultDiv.innerHTML = `<strong>✗ System Issues Detected</strong>`;
            resultDiv.className = 'error';
        }
    } catch (error) {
        resultDiv.innerHTML = `<strong>✗ Health Check Failed</strong><br>${error.message}`;
        resultDiv.className = 'error';
    }
}

// ============ Users Management ============

async function loadUsers() {
    try {
        const response = await fetch(`${API_BASE_URL}/users?page=1&page_size=50`, {
            headers: getAuthHeaders()
        }).then(r => r.json());

        const tbody = document.getElementById('usersTableBody');
        tbody.innerHTML = response.users.map(user => `
            <tr>
                <td>${user.email}</td>
                <td>${user.full_name}</td>
                <td><span class="badge badge-${user.role}">${user.role}</span></td>
                <td>${user.status}</td>
                <td>${new Date(user.created_at).toLocaleDateString()}</td>
                <td>
                    <button class="action-btn btn-edit" onclick="editUser(${user.id})">Edit</button>
                    <button class="action-btn btn-delete" onclick="deleteUser(${user.id})">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load users:', error);
        document.getElementById('usersTableBody').innerHTML =
            `<tr><td colspan="6" class="text-center">Failed to load users</td></tr>`;
    }
}

function openUserModal(userId = null) {
    const modal = document.getElementById('userModal');
    document.getElementById('userForm').reset();

    if (userId) {
        // Load user data (would fetch from API)
        document.getElementById('userId').value = userId;
        modal.querySelector('h2').textContent = 'Edit User';
    } else {
        modal.querySelector('h2').textContent = 'Add New User';
    }

    modal.classList.add('active');
}

async function saveUser(e) {
    e.preventDefault();

    const userEmail = document.getElementById('userEmail').value;
    const userName = document.getElementById('userName').value;
    const userRole = document.getElementById('userRole').value;

    try {
        const response = await fetch(`${API_BASE_URL}/users`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: userEmail,
                username: userEmail.split('@')[0],
                full_name: userName,
                role: userRole
            })
        }).then(r => r.json());

        alert('User saved successfully');
        document.getElementById('userModal').classList.remove('active');
        loadUsers();
    } catch (error) {
        alert(`Failed to save user: ${error.message}`);
    }
}

async function deleteUser(userId) {
    if (!confirm('Are you sure you want to deactivate this user?')) return;

    try {
        await fetch(`${API_BASE_URL}/users/${userId}/deactivate`, {
            method: 'POST',
            headers: getAuthHeaders()
        });

        alert('User deactivated successfully');
        loadUsers();
    } catch (error) {
        alert(`Failed to deactivate user: ${error.message}`);
    }
}

// ============ Projects Management ============

async function loadProjects() {
    try {
        const status = document.getElementById('projectStatusFilter')?.value || '';
        const params = new URLSearchParams();
        if (status) params.append('status', status);

        const response = await fetch(`${API_BASE_URL}/projects?page=1&page_size=50&${params}`, {
            headers: getAuthHeaders()
        }).then(r => r.json());

        const tbody = document.getElementById('projectsTableBody');
        tbody.innerHTML = response.projects.map(project => `
            <tr>
                <td>${project.name}</td>
                <td><span class="badge">${project.status}</span></td>
                <td>${project.lead_id || 'N/A'}</td>
                <td>${project.project_members?.length || 0}</td>
                <td>${new Date(project.created_at).toLocaleDateString()}</td>
                <td>
                    <button class="action-btn btn-edit" onclick="editProject(${project.id})">Edit</button>
                    <button class="action-btn btn-delete" onclick="deleteProject(${project.id})">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load projects:', error);
        document.getElementById('projectsTableBody').innerHTML =
            `<tr><td colspan="6" class="text-center">Failed to load projects</td></tr>`;
    }
}

function openProjectModal(projectId = null) {
    const modal = document.getElementById('projectModal');
    document.getElementById('projectForm').reset();

    if (projectId) {
        document.getElementById('projectId').value = projectId;
        modal.querySelector('h2').textContent = 'Edit Project';
    } else {
        modal.querySelector('h2').textContent = 'Add New Project';
    }

    modal.classList.add('active');
}

async function saveProject(e) {
    e.preventDefault();

    const projectName = document.getElementById('projectName').value;
    const projectDescription = document.getElementById('projectDescription').value;

    try {
        const response = await fetch(`${API_BASE_URL}/projects`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: projectName,
                description: projectDescription
            })
        }).then(r => r.json());

        alert('Project saved successfully');
        document.getElementById('projectModal').classList.remove('active');
        loadProjects();
    } catch (error) {
        alert(`Failed to save project: ${error.message}`);
    }
}

async function deleteProject(projectId) {
    if (!confirm('Are you sure you want to delete this project?')) return;

    try {
        await fetch(`${API_BASE_URL}/projects/${projectId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        alert('Project deleted successfully');
        loadProjects();
    } catch (error) {
        alert(`Failed to delete project: ${error.message}`);
    }
}

// ============ Permissions Management ============

async function loadPermissions() {
    try {
        const response = await fetch(`${API_BASE_URL}/permissions`, {
            headers: getAuthHeaders()
        }).then(r => r.json());

        const permList = document.getElementById('permissionsList');
        permList.innerHTML = response.map(perm => `
            <div class="permission-item">
                <label>${perm.name}</label>
                <small>${perm.category}</small>
            </div>
        `).join('');

        loadRolePermissions();
    } catch (error) {
        console.error('Failed to load permissions:', error);
    }
}

async function loadRolePermissions() {
    try {
        const role = document.getElementById('roleSelect')?.value || 'admin';

        const response = await fetch(`${API_BASE_URL}/permissions/role/${role}`, {
            headers: getAuthHeaders()
        }).then(r => r.json());

        const rolePermList = document.getElementById('rolePermissionsList');
        rolePermList.innerHTML = response.permissions.map(perm => `
            <div class="permission-item">
                <input type="checkbox" checked>
                <label>${perm.name}</label>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load role permissions:', error);
    }
}

async function assignPermission() {
    alert('Permission assignment UI - connect to API as needed');
}

async function initializePermissions() {
    try {
        const response = await fetch(`${API_BASE_URL}/permissions/initialize-defaults`, {
            method: 'POST',
            headers: getAuthHeaders()
        }).then(r => r.json());

        alert('Permissions initialized: ' + response.message);
        loadPermissions();
    } catch (error) {
        alert(`Failed to initialize permissions: ${error.message}`);
    }
}

// ============ System Configuration ============

async function loadSystemConfig() {
    try {
        const response = await fetch(`${API_BASE_URL}/system/config`, {
            headers: getAuthHeaders()
        }).then(r => r.json());

        const configList = document.getElementById('configList');
        configList.innerHTML = response.map(config => `
            <div class="config-item">
                <h4>${config.key}</h4>
                <p>${config.description}</p>
                <div class="config-value">
                    <input type="text" value="${config.value}" id="config-${config.id}">
                    <button class="btn-save" onclick="saveConfig(${config.id}, '${config.key}')">Save</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load system config:', error);
        document.getElementById('configList').innerHTML = 'Failed to load configuration';
    }
}

async function saveConfig(configId, configKey) {
    const newValue = document.getElementById(`config-${configId}`).value;

    try {
        await fetch(`${API_BASE_URL}/system/config/${configKey}`, {
            method: 'PUT',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ value: newValue })
        });

        alert('Configuration saved successfully');
        loadSystemConfig();
    } catch (error) {
        alert(`Failed to save configuration: ${error.message}`);
    }
}

// ============ Backup Management ============

async function loadBackups() {
    try {
        const response = await fetch(`${API_BASE_URL}/backups?page=1&page_size=20`, {
            headers: getAuthHeaders()
        }).then(r => r.json());

        const tbody = document.getElementById('backupsTableBody');
        tbody.innerHTML = response.backups.map(backup => `
            <tr>
                <td>${backup.name}</td>
                <td>${backup.backup_type}</td>
                <td>${backup.file_size ? (backup.file_size / 1024 / 1024).toFixed(2) + ' MB' : 'N/A'}</td>
                <td><span class="badge badge-${backup.status}">${backup.status}</span></td>
                <td>${new Date(backup.backup_date).toLocaleDateString()}</td>
                <td>
                    ${backup.status === 'completed' ? `
                        <button class="action-btn btn-restore" onclick="restoreBackup(${backup.id})">Restore</button>
                    ` : ''}
                    <button class="action-btn btn-delete" onclick="deleteBackup(${backup.id})">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load backups:', error);
        document.getElementById('backupsTableBody').innerHTML =
            `<tr><td colspan="6" class="text-center">Failed to load backups</td></tr>`;
    }
}

async function triggerBackup(type) {
    try {
        const response = await fetch(`${API_BASE_URL}/backups/trigger?backup_type=${type}`, {
            method: 'POST',
            headers: getAuthHeaders()
        }).then(r => r.json());

        alert(`Backup triggered: ${response.name}`);
        loadBackups();
    } catch (error) {
        alert(`Failed to trigger backup: ${error.message}`);
    }
}

async function restoreBackup(backupId) {
    if (!confirm('WARNING: This will restore the database to this backup point. All current data will be replaced. Continue?')) return;

    try {
        await fetch(`${API_BASE_URL}/backups/restore/${backupId}`, {
            method: 'POST',
            headers: getAuthHeaders()
        });

        alert('Backup restored successfully. Please refresh the application.');
        loadBackups();
    } catch (error) {
        alert(`Failed to restore backup: ${error.message}`);
    }
}

async function deleteBackup(backupId) {
    if (!confirm('Are you sure you want to delete this backup?')) return;

    try {
        await fetch(`${API_BASE_URL}/backups/${backupId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        alert('Backup deleted successfully');
        loadBackups();
    } catch (error) {
        alert(`Failed to delete backup: ${error.message}`);
    }
}

// ============ Audit Logs ============

async function loadAuditLogs() {
    try {
        const response = await fetch(`${API_BASE_URL}/users/1/audit-logs?page=1&page_size=50`, {
            headers: getAuthHeaders()
        }).then(r => r.json());

        const tbody = document.getElementById('auditLogsTableBody');
        tbody.innerHTML = response.map(log => `
            <tr>
                <td>${log.user_id || 'System'}</td>
                <td>${log.action}</td>
                <td>${log.resource_type}</td>
                <td>${log.details}</td>
                <td>${new Date(log.created_at).toLocaleString()}</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load audit logs:', error);
        document.getElementById('auditLogsTableBody').innerHTML =
            `<tr><td colspan="5" class="text-center">Failed to load audit logs</td></tr>`;
    }
}

// ============ Helper Functions ============

function getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return {
        'Authorization': token ? `Bearer ${token}` : '',
        'Content-Type': 'application/json'
    };
}

const API_BASE_URL = window.location.origin;

