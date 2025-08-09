# main.py
import os
import json
import hashlib
import shutil
import tempfile
import mimetypes
from datetime import timedelta
from flask import Flask, render_template_string, request, redirect, url_for, session, send_from_directory, jsonify, Response, after_this_request, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(days=30)

# --- Embedded HTML Templates ---

LAYOUT_HTML = """
<!DOCTYPE html>
<html lang="en" class="">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Python File Server</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
    <style>
        .dark .bg-gray-100 { background-color: #1a202c; }
        .dark .bg-white { background-color: #2d3748; }
        .dark .text-gray-800 { color: #e2e8f0; }
        .dark .text-gray-700 { color: #a0aec0; }
        .dark .border-gray-200 { border-color: #4a5568; }
        .dark .hover\\:bg-gray-50:hover { background-color: #4a5568; }
        .dark .hover\\:bg-gray-200:hover { background-color: #4a5568; }
        input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 16px; height: 16px; background: #3b82f6; cursor: pointer; border-radius: 50%; }
        input[type=range]::-moz-range-thumb { width: 16px; height: 16px; background: #3b82f6; cursor: pointer; border-radius: 50%; }
    </style>
</head>
<body class="bg-gray-100 text-gray-800">
    <div class="flex h-screen">
        <!-- Sidebar -->
        <aside class="w-64 bg-white p-4 overflow-y-auto flex-shrink-0">
            <h2 class="text-xl font-bold mb-4">Directories</h2>
            <div id="directory-tree"></div>
        </aside>

        <div class="flex-1 flex flex-col">
            <!-- Top Bar -->
            <header class="bg-white shadow p-4">
                <div class="flex justify-between items-center">
                    <div class="flex space-x-2">
                        <button id="upload-file-btn" class="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600">
                            <i class="fas fa-file-arrow-up mr-2"></i>Upload File(s)
                        </button>
                        <button id="upload-folder-btn" class="bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600">
                            <i class="fas fa-folder-plus mr-2"></i>Upload Folder
                        </button>
                        <input type="file" id="file-input" class="hidden" multiple>
                        <input type="file" id="folder-input" class="hidden" webkitdirectory directory multiple>
                    </div>
                    <div class="flex items-center">
                         <button id="theme-toggle" class="mr-4 text-gray-500 hover:text-gray-700">
                            <i class="fas fa-moon"></i>
                        </button>
                        {% if session.user.is_admin %}
                            <a href="{{ url_for('admin') }}" class="px-3 py-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700">Admin</a>
                        {% endif %}
                        <a href="{{ url_for('logout') }}" class="px-3 py-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700">Logout</a>
                    </div>
                </div>
                <div id="zipping-status" class="mt-4 hidden">
                    <div class="flex justify-between mb-1">
                        <span id="zipping-filename" class="text-sm font-medium"></span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                        <div class="bg-indigo-500 h-full w-full animate-pulse"></div>
                    </div>
                     <div class="text-sm text-right mt-1">Zipping folder, download will begin shortly...</div>
                </div>
                <div id="hash-status" class="mt-4 hidden">
                    <div class="flex justify-between mb-1">
                        <span id="hash-filename" class="text-sm font-medium"></span>
                        <span id="hash-percentage" class="text-sm font-medium">0%</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2.5">
                        <div id="hash-progress-bar" class="bg-yellow-400 h-2.5 rounded-full" style="width: 0%"></div>
                    </div>
                     <div class="text-sm text-right mt-1">Generating hash for resumable upload...</div>
                </div>
                <div id="upload-status" class="mt-4 hidden">
                    <div class="flex justify-between mb-1">
                        <span id="upload-filename" class="text-sm font-medium"></span>
                        <span id="upload-details" class="text-sm font-medium"></span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2.5">
                        <div id="upload-progress-bar" class="bg-blue-600 h-2.5 rounded-full" style="width: 0%"></div>
                    </div>
                    <div id="upload-speed" class="text-sm text-right mt-1"></div>
                </div>
            </header>

            <!-- Main Content -->
            <main class="flex-1 p-6 overflow-y-auto">
                {{ content | safe }}
            </main>
        </div>
    </div>

    <script>
        // Theme switcher
        const themeToggle = document.getElementById('theme-toggle');
        const html = document.documentElement;

        themeToggle.addEventListener('click', () => {
            html.classList.toggle('dark');
            localStorage.setItem('theme', html.classList.contains('dark') ? 'dark' : 'light');
        });

        if (localStorage.getItem('theme') === 'dark') {
            html.classList.add('dark');
        }
    </script>
</body>
</html>
"""

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en" class="">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Python File Server</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .dark .bg-gray-100 { background-color: #1a202c; }
        .dark .bg-white { background-color: #2d3748; }
        .dark .text-gray-800 { color: #e2e8f0; }
        .dark .text-gray-700 { color: #a0aec0; }
    </style>
</head>
<body class="bg-gray-100 text-gray-800">
    <div class="flex items-center justify-center h-screen">
        <div class="max-w-md w-full bg-white p-8 rounded-lg shadow-md">
            <h2 class="text-2xl font-bold mb-6 text-center">Login</h2>
            {% if error %}
                <p class="text-red-500 text-center mb-4">{{ error }}</p>
            {% endif %}
            <form method="post">
                <div class="mb-4">
                    <label for="username" class="block text-gray-700">Username</label>
                    <input type="text" name="username" id="username" class="w-full px-3 py-2 border rounded-lg bg-gray-200 dark:bg-gray-700 dark:border-gray-600" required>
                </div>
                <div class="mb-6">
                    <label for="password" class="block text-gray-700">Password</label>
                    <input type="password" name="password" id="password" class="w-full px-3 py-2 border rounded-lg bg-gray-200 dark:bg-gray-700 dark:border-gray-600" required>
                </div>
                <button type="submit" class="w-full bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600">Login</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

SETUP_ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en" class="">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Setup - Python File Server</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 text-gray-800">
    <div class="flex items-center justify-center h-screen">
        <div class="max-w-md w-full bg-white p-8 rounded-lg shadow-md">
            <h2 class="text-2xl font-bold mb-6 text-center">Create Admin User</h2>
            <p class="text-center mb-4">This is the first time you are running the server. Please create an admin account.</p>
            {% if error %}
                <p class="text-red-500 text-center mb-4">{{ error }}</p>
            {% endif %}
            <form method="post">
                <div class="mb-4">
                    <label for="username" class="block text-gray-700">Admin Username</label>
                    <input type="text" name="username" id="username" class="w-full px-3 py-2 border rounded-lg" required>
                </div>
                <div class="mb-6">
                    <label for="password" class="block text-gray-700">Password</label>
                    <input type="password" name="password" id="password" class="w-full px-3 py-2 border rounded-lg" required>
                </div>
                <button type="submit" class="w-full bg-green-500 text-white py-2 rounded-lg hover:bg-green-600">Create Admin</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

INDEX_HTML = """
<div class="flex justify-between items-center mb-4">
    <div class="flex items-center space-x-2">
        <button id="up-dir-btn" title="Up one level" class="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700">
            <i class="fas fa-arrow-up"></i>
        </button>
        <h1 id="current-path-header" class="text-2xl font-bold truncate">Files</h1>
    </div>
    <div>
        <button id="list-view-btn" class="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700"><i class="fas fa-list"></i></button>
        <button id="icon-view-btn" class="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700"><i class="fas fa-th-large"></i></button>
    </div>
</div>
<div id="file-view" data-view="list" class="grid grid-cols-1 gap-2">
    <!-- File items will be injected here by JavaScript -->
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.1.1/crypto-js.min.js"></script>
<script>
    const fileView = document.getElementById('file-view');
    const listViewBtn = document.getElementById('list-view-btn');
    const iconViewBtn = document.getElementById('icon-view-btn');
    const treeContainer = document.getElementById('directory-tree');
    const currentPathHeader = document.getElementById('current-path-header');
    const upDirBtn = document.getElementById('up-dir-btn');
    let currentPath = '';

    const VIDEO_EXTENSIONS = ['.mp4', '.webm', '.ogv', '.mkv'];

    function formatBytes(bytes, decimals = 2) {
        if (!+bytes) return '0 Bytes'
        const k = 1024
        const dm = decimals < 0 ? 0 : decimals
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`
    }

    function renderDirectoryTree(nodes) {
        const ul = document.createElement('ul');
        nodes.forEach(node => {
            const li = document.createElement('li');
            const hasChildren = node.children && node.children.length > 0;
            
            const chevron = hasChildren ? `<i class="fas fa-chevron-right mr-1 text-xs cursor-pointer expand-icon"></i>` : '<span class="inline-block w-4 mr-1"></span>';

            li.innerHTML = `
                <div class="flex items-center">
                    ${chevron}
                    <a href="#" data-path="${node.path}" class="block p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 flex-grow dir-name-link truncate">
                        <i class="fas fa-folder mr-2 text-yellow-500"></i>
                        <span>${node.name}</span>
                    </a>
                </div>
            `;
            
            if (hasChildren) {
                const childUl = renderDirectoryTree(node.children);
                childUl.classList.add('ml-4', 'hidden');
                li.appendChild(childUl);
            }
            ul.appendChild(li);
        });
        return ul;
    }

    async function fetchDirectoryTree() {
        try {
            const response = await fetch('/api/dir_tree');
            if (!response.ok) return null;
            return await response.json();
        } catch (e) {
            console.error("Failed to fetch directory tree:", e);
            return null;
        }
    }

    async function fetchAndRenderFiles(path) {
        currentPath = path;
        currentPathHeader.textContent = path;
        
        const apiPath = path === '/' ? '' : (path.startsWith('/') ? path.substring(1) : path);
        const response = await fetch(`/api/browse/${apiPath}`);
        
        if (!response.ok) {
            const err = await response.json().catch(() => ({ error: 'Failed to load directory.' }));
            fileView.innerHTML = `<p class="text-red-500">${err.error || 'An unknown error occurred.'}</p>`;
            return;
        }

        const items = await response.json();
        renderFiles(items);
    }

    function renderFiles(items) {
        const viewMode = fileView.dataset.view || 'list';

        if (viewMode === 'list') {
            fileView.className = 'grid grid-cols-1 gap-2';
        } else {
            fileView.className = 'grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-4 text-center';
        }

        fileView.innerHTML = '';
        if (!items || items.length === 0) {
            fileView.innerHTML = '<p class="text-gray-500">This directory is empty.</p>';
            return;
        }

        items.forEach(item => {
            const isDir = item.is_dir;
            const element = document.createElement('div');
            element.dataset.path = item.path;
            element.dataset.isDir = item.is_dir;
            
            if (viewMode === 'list') {
                element.className = 'flex items-center justify-between p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700';
                const icon = isDir ? 'fa-folder text-yellow-500' : 'fa-file text-gray-500';
                const fileExt = item.name.substring(item.name.lastIndexOf('.')).toLowerCase();
                const isVideo = VIDEO_EXTENSIONS.includes(fileExt);

                let actions = `<a href="${item.is_dir ? '#' : `/download${item.path}`}" class="text-green-500 hover:underline mr-4 download-link">${item.is_dir ? 'Download ZIP' : 'Download'}</a>`;
                if (isVideo) {
                    actions += `<a href="/stream${item.path}" target="_blank" class="text-purple-500 hover:underline">Stream</a>`;
                }

                element.innerHTML = `
                    <div class="flex items-center truncate w-3/5">
                        <i class="fas ${icon} fa-fw mr-4"></i>
                        <a href="#" class="truncate">${item.name}</a>
                    </div>
                    <div class="w-1/5 text-right pr-4">
                        ${!isDir ? formatBytes(item.size) : ''}
                    </div>
                    <div class="flex-shrink-0 w-1/5 text-right">
                        ${actions}
                    </div>
                `;
            } else { // Icon view
                element.className = 'flex flex-col items-center p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700 cursor-pointer';
                const icon = isDir ? 'fa-folder fa-3x text-yellow-500' : 'fa-file fa-3x text-gray-500';
                 element.innerHTML = `
                    <div class="flex flex-col items-center">
                        <i class="fas ${icon} mb-2"></i>
                        <span class="text-sm truncate w-24">${item.name}</span>
                    </div>
                `;
            }
            fileView.appendChild(element);
        });
    }

    treeContainer.addEventListener('click', e => {
        const expandIcon = e.target.closest('.expand-icon');
        if (expandIcon) {
            e.preventDefault();
            const childUl = expandIcon.parentElement.nextElementSibling;
            if (childUl) {
                childUl.classList.toggle('hidden');
                expandIcon.classList.toggle('fa-chevron-right');
                expandIcon.classList.toggle('fa-chevron-down');
            }
            return;
        }

        const link = e.target.closest('.dir-name-link');
        if (link && link.dataset.path) {
            e.preventDefault();
            fetchAndRenderFiles(link.dataset.path);
        }
    });

    fileView.addEventListener('dblclick', e => {
        const itemElement = e.target.closest('[data-path]');
        if (itemElement && itemElement.dataset.isDir === 'true') {
            fetchAndRenderFiles(itemElement.dataset.path);
        }
    });

    fileView.addEventListener('click', e => {
        const downloadLink = e.target.closest('.download-link');
        if (downloadLink && (downloadLink.href.includes('/download_folder') || downloadLink.href.endsWith('#'))) {
            e.preventDefault();
            const zippingStatus = document.getElementById('zipping-status');
            const zippingFilename = document.getElementById('zipping-filename');
            const path = downloadLink.closest('[data-path]').dataset.path;
            const token = `zip-token-${Date.now()}`;
            zippingFilename.textContent = path;
            zippingStatus.classList.remove('hidden');
            
            window.location.href = `/download_folder${path}?token=${token}`;

            const interval = setInterval(() => {
                if (document.cookie.includes(`download-ready=${token}`)) {
                    zippingStatus.classList.add('hidden');
                    document.cookie = `download-ready=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;`;
                    clearInterval(interval);
                }
            }, 500);
        }
    });

    listViewBtn.addEventListener('click', () => {
        fileView.dataset.view = 'list';
        fetchAndRenderFiles(currentPath);
    });

    iconViewBtn.addEventListener('click', () => {
        fileView.dataset.view = 'icon';
        fetchAndRenderFiles(currentPath);
    });

    upDirBtn.addEventListener('click', () => {
        if (currentPath === '/' || !currentPath) {
            return;
        }
        let parentPath = currentPath.substring(0, currentPath.lastIndexOf('/'));
        if (parentPath === '') {
            parentPath = '/';
        }
        fetchAndRenderFiles(parentPath);
    });
    
    // Upload functionality
    const uploadFileBtn = document.getElementById('upload-file-btn');
    const uploadFolderBtn = document.getElementById('upload-folder-btn');
    const fileInput = document.getElementById('file-input');
    const folderInput = document.getElementById('folder-input');
    
    uploadFileBtn.addEventListener('click', () => fileInput.click());
    uploadFolderBtn.addEventListener('click', () => folderInput.click());
    fileInput.addEventListener('change', () => handleFiles(fileInput.files));
    folderInput.addEventListener('change', () => {
        handleFiles(folderInput.files).then(() => {
            fetchDirectoryTree(); // Refresh tree after folder upload
        });
    });

    document.body.addEventListener('dragover', (e) => { e.preventDefault(); e.stopPropagation(); });
    document.body.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.target.closest('main')) {
             handleFiles(e.dataTransfer.files).then(() => {
                fetchDirectoryTree();
             });
        }
    });

    async function handleFiles(files) {
        for (const file of files) {
            await uploadFile(file);
        }
    }

    async function uploadFile(file) {
        const hashStatus = document.getElementById('hash-status');
        const hashFilename = document.getElementById('hash-filename');
        const hashProgressBar = document.getElementById('hash-progress-bar');
        const hashPercentage = document.getElementById('hash-percentage');
        
        hashFilename.textContent = file.name;
        hashStatus.classList.remove('hidden');

        const fileHash = await hashFile(file, (progress) => {
            const percentage = Math.round(progress);
            hashProgressBar.style.width = `${percentage}%`;
            hashPercentage.textContent = `${percentage}%`;
        });

        hashStatus.classList.add('hidden');

        const chunkSize = 1024 * 1024; // 1MB
        const totalChunks = Math.ceil(file.size / chunkSize);
        
        const uploadStatus = document.getElementById('upload-status');
        const uploadFilename = document.getElementById('upload-filename');
        const uploadProgressBar = document.getElementById('upload-progress-bar');
        const uploadDetails = document.getElementById('upload-details');
        const uploadSpeed = document.getElementById('upload-speed');

        uploadFilename.textContent = file.webkitRelativePath || file.name;
        uploadStatus.classList.remove('hidden');

        let startTime = Date.now();
        let uploadedBytes = 0;

        for (let i = 0; i < totalChunks; i++) {
            const start = i * chunkSize;
            const end = Math.min(start + chunkSize, file.size);
            const chunk = file.slice(start, end);

            const formData = new FormData();
            formData.append('file', chunk);
            formData.append('file_hash', fileHash);
            formData.append('chunk_index', i);
            formData.append('total_chunks', totalChunks);
            formData.append('filename', file.name);
            formData.append('target_dir', currentPath);
            formData.append('relative_path', file.webkitRelativePath || '');

            try {
                const response = await fetch('/upload', { method: 'POST', body: formData });
                const result = await response.json();

                uploadedBytes += chunk.size;
                const elapsedTime = (Date.now() - startTime) / 1000;
                const speed = elapsedTime > 0 ? uploadedBytes / elapsedTime : 0;
                
                const percentage = Math.round(((i + 1) / totalChunks) * 100);
                uploadProgressBar.style.width = `${percentage}%`;
                uploadDetails.textContent = `${formatBytes(uploadedBytes)} / ${formatBytes(file.size)} (${percentage}%)`;
                uploadSpeed.textContent = `${formatBytes(speed)}/s`;

            } catch (error) {
                console.error('Upload failed:', error);
                uploadStatus.classList.add('hidden');
                return;
            }
        }
        
        setTimeout(() => uploadStatus.classList.add('hidden'), 3000);
        fetchAndRenderFiles(currentPath);
    }

    function hashFile(file, progressCallback) {
        return new Promise((resolve, reject) => {
            const chunkSize = 1024 * 1024 * 2; // 2MB chunks for hashing
            const totalChunks = Math.ceil(file.size / chunkSize);
            let currentChunk = 0;
            const spark = new CryptoJS.lib.WordArray.init();
            const reader = new FileReader();

            reader.onload = (event) => {
                spark.concat(CryptoJS.lib.WordArray.create(event.target.result));
                currentChunk++;
                
                if (progressCallback) {
                    progressCallback((currentChunk / totalChunks) * 100);
                }

                if (currentChunk < totalChunks) {
                    loadNext();
                } else {
                    const hash = CryptoJS.SHA256(spark).toString();
                    resolve(hash);
                }
            };
            
            reader.onerror = (error) => reject(error);

            function loadNext() {
                const start = currentChunk * chunkSize;
                const end = Math.min(start + chunkSize, file.size);
                reader.readAsArrayBuffer(file.slice(start, end));
            }

            loadNext();
        });
    }

    async function initialLoad() {
        const treeData = await fetchDirectoryTree();
        if (treeData && treeData.length > 0) {
            treeContainer.innerHTML = '';
            treeContainer.appendChild(renderDirectoryTree(treeData));
            const firstLink = document.querySelector('#directory-tree a.dir-name-link');
            if (firstLink) {
                 await fetchAndRenderFiles(firstLink.dataset.path);
            }
        } else {
            fileView.innerHTML = '<p>No accessible directories. Please contact an administrator.</p>';
        }
    }

    document.addEventListener('DOMContentLoaded', initialLoad);

</script>
"""

ADMIN_HTML = """
<div class="flex justify-between items-center mb-6">
    <h1 class="text-3xl font-bold">Admin Dashboard</h1>
    <a href="{{ url_for('index') }}" class="text-blue-500 hover:underline">&larr; Back to Files</a>
</div>

<!-- Allowed Directories -->
<div class="bg-white p-6 rounded-lg shadow-md mb-6">
    <h2 class="text-xl font-bold mb-4">Allowed Directories</h2>
    <form method="post" class="mb-4">
        <input type="text" name="new_dir" placeholder="Enter absolute path to directory" class="w-full md:w-1/2 px-3 py-2 border rounded-lg mb-2">
        <button type="submit" class="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600">Add Directory</button>
    </form>
    <ul>
        {% for dir in config.allowed_directories %}
        <li class="flex justify-between items-center mb-2">
            <span>{{ dir }}</span>
            <form method="post">
                <input type="hidden" name="remove_dir" value="{{ dir }}">
                <button type="submit" class="text-red-500 hover:underline">Remove</button>
            </form>
        </li>
        {% endfor %}
    </ul>
</div>

<!-- User Management -->
<div class="bg-white p-6 rounded-lg shadow-md">
    <h2 class="text-xl font-bold mb-4">User Management</h2>
    
    <!-- Create User Form -->
    <form action="{{ url_for('create_user') }}" method="post" class="mb-6 border-b pb-6">
        <h3 class="text-lg font-semibold mb-2">Create New User</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input type="text" name="username" placeholder="Username" class="px-3 py-2 border rounded-lg" required>
            <input type="password" name="password" placeholder="Password" class="px-3 py-2 border rounded-lg" required>
        </div>
        <div class="mt-4">
            <label class="inline-flex items-center">
                <input type="checkbox" name="is_admin" class="form-checkbox">
                <span class="ml-2">Is Admin</span>
            </label>
        </div>
        <div class="mt-4">
            <h4 class="font-semibold">Allowed Directories (for non-admins)</h4>
            {% for dir in config.allowed_directories %}
            <label class="block">
                <input type="checkbox" name="allowed_dirs" value="{{ dir }}"> {{ dir }}
            </label>
            {% endfor %}
        </div>
        <button type="submit" class="mt-4 bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600">Create User</button>
    </form>

    <!-- User List -->
    <h3 class="text-lg font-semibold mb-2">Existing Users</h3>
    <ul>
        {% for username, user in users.items() %}
        <li class="flex justify-between items-center mb-2">
            <span>{{ username }} {% if user.is_admin %}(Admin){% endif %}</span>
            {% if not user.is_admin %}
            <form action="{{ url_for('delete_user', username=username) }}" method="post">
                <button type="submit" class="text-red-500 hover:underline">Delete</button>
            </form>
            {% endif %}
        </li>
        {% endfor %}
    </ul>
</div>
"""

# --- Configuration ---
DATA_DIR = 'data'
UPLOADS_DIR = 'uploads'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')
CHUNK_DIR = os.path.join(UPLOADS_DIR, 'chunks')

# --- Helper Functions ---
def setup():
    """Create necessary directories and files if they don't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    os.makedirs(CHUNK_DIR, exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump({}, f)
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'allowed_directories': ['/']}, f)

def get_users():
    """Load user data from the JSON file."""
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    """Save user data to the JSON file."""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def get_config():
    """Load configuration from the JSON file."""
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    """Save configuration to the JSON file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def is_admin_setup():
    """Check if an admin user has been created."""
    users = get_users()
    for user in users.values():
        if user.get('is_admin'):
            return True
    return False

def get_user_dirs():
    user = session['user']
    config = get_config()
    if user.get('is_admin'):
        return config['allowed_directories']
    return user.get('allowed_dirs', [])

def build_dir_tree(path, user_dirs):
    tree = []
    if not os.path.isdir(path):
        return tree
        
    try:
        for entry in os.scandir(path):
            if entry.is_dir():
                is_allowed = any(os.path.abspath(entry.path).startswith(os.path.abspath(d)) for d in user_dirs)
                if is_allowed:
                    node = {'name': entry.name, 'path': entry.path, 'children': build_dir_tree(entry.path, user_dirs)}
                    tree.append(node)
    except PermissionError:
        pass # Ignore directories we can't access
    return tree

def render_with_layout(template_string, **context):
    """Helper to render a content string within the main layout."""
    context['session'] = session
    content_html = render_template_string(template_string, **context)
    return render_template_string(LAYOUT_HTML, content=content_html, **context)

# --- Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        session.permanent = True # Extend session on activity
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or not session['user'].get('is_admin'):
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---
@app.route('/')
@login_required
def index():
    return render_with_layout(INDEX_HTML)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if not is_admin_setup():
        return redirect(url_for('setup_admin'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = get_users()
        user = users.get(username)
        if user and check_password_hash(user['password_hash'], password):
            session.permanent = True
            session['user'] = user
            session['user']['username'] = username
            return redirect(url_for('index'))
        return render_template_string(LOGIN_HTML, error='Invalid username or password')
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/setup_admin', methods=['GET', 'POST'])
def setup_admin():
    if is_admin_setup():
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = get_users()
        if username in users:
            return render_template_string(SETUP_ADMIN_HTML, error='Username already exists')
        
        users[username] = {
            'password_hash': generate_password_hash(password),
            'is_admin': True,
            'allowed_dirs': []
        }
        save_users(users)
        return redirect(url_for('login'))
    return render_template_string(SETUP_ADMIN_HTML)

@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin():
    if request.method == 'POST':
        new_dir = request.form.get('new_dir')
        if new_dir and os.path.isdir(new_dir):
            config = get_config()
            if new_dir not in config['allowed_directories']:
                config['allowed_directories'].append(os.path.abspath(new_dir))
                save_config(config)
        
        remove_dir = request.form.get('remove_dir')
        if remove_dir:
            config = get_config()
            if remove_dir in config['allowed_directories']:
                config['allowed_directories'].remove(remove_dir)
                save_config(config)

        return redirect(url_for('admin'))

    config = get_config()
    users = get_users()
    return render_with_layout(ADMIN_HTML, config=config, users=users)

@app.route('/admin/create_user', methods=['POST'])
@admin_required
def create_user():
    username = request.form['username']
    password = request.form['password']
    users = get_users()
    if username in users:
        return redirect(url_for('admin'))
    
    users[username] = {
        'password_hash': generate_password_hash(password),
        'is_admin': 'is_admin' in request.form,
        'allowed_dirs': request.form.getlist('allowed_dirs')
    }
    save_users(users)
    return redirect(url_for('admin'))

@app.route('/admin/delete_user/<username>', methods=['POST'])
@admin_required
def delete_user(username):
    users = get_users()
    if username in users and not users[username].get('is_admin'):
        del users[username]
        save_users(users)
    return redirect(url_for('admin'))

@app.route('/download/<path:filepath>')
@login_required
def download_file(filepath):
    abs_path = f"/{filepath}"
    user_dirs = get_user_dirs()
    is_allowed = any(os.path.abspath(abs_path).startswith(os.path.abspath(d)) for d in user_dirs)

    if not is_allowed or os.path.isdir(abs_path):
        return "Access Denied or Not a File", 403
        
    directory = os.path.dirname(abs_path)
    filename = os.path.basename(abs_path)
    return send_from_directory(directory, filename, as_attachment=True)

@app.route('/download_folder/<path:folderpath>')
@login_required
def download_folder(folderpath):
    abs_path = f"/{folderpath}"
    user_dirs = get_user_dirs()
    is_allowed = any(os.path.abspath(abs_path).startswith(os.path.abspath(d)) for d in user_dirs)

    if not is_allowed or not os.path.isdir(abs_path):
        return "Access Denied or Not a Directory", 403

    temp_dir = tempfile.mkdtemp()
    archive_basename = os.path.join(temp_dir, os.path.basename(abs_path))
    archive_path = shutil.make_archive(archive_basename, 'zip', abs_path)
    archive_filename = os.path.basename(archive_path)

    @after_this_request
    def cleanup(response):
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Error cleaning up temp directory {temp_dir}: {e}")
        return response
    
    response = make_response(send_from_directory(temp_dir, archive_filename, as_attachment=True))
    token = request.args.get('token')
    if token:
        response.set_cookie(f'download-ready', token, max_age=20) # Short-lived cookie
    return response

@app.route('/stream/<path:filepath>')
@login_required
def stream_file(filepath):
    abs_path = f"/{filepath}"
    user_dirs = get_user_dirs()
    is_allowed = any(os.path.abspath(abs_path).startswith(os.path.abspath(d)) for d in user_dirs)

    if not is_allowed or os.path.isdir(abs_path):
        return "Access Denied or Not a File", 403

    def generate():
        with open(abs_path, "rb") as f:
            while True:
                chunk = f.read(1024*1024)
                if not chunk:
                    break
                yield chunk
    
    mimetype, _ = mimetypes.guess_type(abs_path)
    return Response(generate(), mimetype=mimetype or "application/octet-stream")

@app.route('/upload', methods=['POST'])
@login_required
def upload_chunk():
    file = request.files['file']
    file_hash = request.form['file_hash']
    chunk_index = int(request.form['chunk_index'])
    total_chunks = int(request.form['total_chunks'])
    filename = request.form['filename']
    target_dir = request.form['target_dir']
    relative_path = request.form.get('relative_path', '')

    user_dirs = get_user_dirs()
    
    final_dir = os.path.join(target_dir, os.path.dirname(relative_path))
    is_allowed = any(os.path.abspath(final_dir).startswith(os.path.abspath(d)) for d in user_dirs)

    if not is_allowed:
        return jsonify({'message': 'Upload failed: Target directory not allowed.'}), 403

    chunk_filename = f"{file_hash}_{chunk_index}"
    chunk_path = os.path.join(CHUNK_DIR, chunk_filename)
    file.save(chunk_path)
    
    all_chunks_present = all(os.path.exists(os.path.join(CHUNK_DIR, f"{file_hash}_{i}")) for i in range(total_chunks))
            
    if all_chunks_present:
        os.makedirs(final_dir, exist_ok=True)
        target_path = os.path.join(final_dir, filename)

        with open(target_path, 'wb') as outfile:
            for i in range(total_chunks):
                chunk_to_write = os.path.join(CHUNK_DIR, f"{file_hash}_{i}")
                with open(chunk_to_write, 'rb') as infile:
                    outfile.write(infile.read())
                os.remove(chunk_to_write)

        hasher = hashlib.sha256()
        with open(target_path, 'rb') as f:
            while chunk := f.read(4096):
                hasher.update(chunk)
        
        if hasher.hexdigest() == file_hash:
            return jsonify({'message': 'File uploaded and verified successfully!'})
        else:
            os.remove(target_path)
            return jsonify({'message': 'File verification failed.'}), 500

    return jsonify({'message': f'Chunk {chunk_index + 1}/{total_chunks} uploaded.'})

# --- API Routes ---
@app.route('/api/dir_tree')
@login_required
def dir_tree():
    user_dirs = get_user_dirs()
    tree = []
    for d in user_dirs:
        tree.append({
            'name': os.path.basename(d) or d,
            'path': d,
            'children': build_dir_tree(d, user_dirs)
        })
    return jsonify(tree)

@app.route('/api/browse/', defaults={'subpath': ''})
@app.route('/api/browse/<path:subpath>')
@login_required
def api_browse(subpath):
    abs_path = f"/{subpath}"
    user_dirs = get_user_dirs()
    is_allowed = any(os.path.abspath(abs_path).startswith(os.path.abspath(d)) for d in user_dirs)

    if not is_allowed:
        return jsonify({'error': 'Access Denied'}), 403

    if not os.path.isdir(abs_path):
        return jsonify({'error': 'Directory Not Found'}), 404

    items = []
    try:
        for item in os.scandir(abs_path):
            stat_result = item.stat()
            items.append({
                'name': item.name,
                'is_dir': item.is_dir(),
                'path': item.path,
                'size': stat_result.st_size if not item.is_dir() else 0
            })
    except PermissionError:
        return jsonify({'error': f'Permission denied to read directory: {abs_path}'}), 403
    
    items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
    return jsonify(items)


if __name__ == '__main__':
    setup()
    app.run(host='0.0.0.0', debug=True, port=5001)
