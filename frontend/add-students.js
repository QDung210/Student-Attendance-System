// Add Students JavaScript
let excelFile = null;
let imagesFiles = [];
let processingInterval = null;

// Initialize drag and drop
document.addEventListener('DOMContentLoaded', function() {
    setupDragAndDrop();
    setupFileInputs();
});

function setupDragAndDrop() {
    const excelArea = document.getElementById('excel-upload-area');
    const imagesArea = document.getElementById('images-upload-area');
    
    // Excel drag and drop
    excelArea.addEventListener('dragover', handleDragOver);
    excelArea.addEventListener('dragleave', handleDragLeave);
    excelArea.addEventListener('drop', handleExcelDrop);
    excelArea.addEventListener('click', () => document.getElementById('excel-file').click());
    
    // Images drag and drop
    imagesArea.addEventListener('click', () => document.getElementById('images-folder').click());
}

function setupFileInputs() {
    document.getElementById('excel-file').addEventListener('change', handleExcelFileSelect);
    document.getElementById('images-folder').addEventListener('change', handleImagesFileSelect);
}

function handleDragOver(e) {
    e.preventDefault();
    e.target.closest('.upload-area').classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.target.closest('.upload-area').classList.remove('dragover');
}

function handleExcelDrop(e) {
    e.preventDefault();
    const area = e.target.closest('.upload-area');
    area.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        const file = files[0];
        if (file.name.endsWith('.xlsx') || file.name.endsWith('.xls')) {
            excelFile = file;
            showExcelInfo(file);
            updateStepStatus(1, 'completed');
            updateStepStatus(2, 'active');
            checkReadyToProcess();
        } else {
            alert('Please select Excel file (.xlsx or .xls)');
        }
    }
}

function handleExcelFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        excelFile = file;
        showExcelInfo(file);
        updateStepStatus(1, 'completed');
        updateStepStatus(2, 'active');
        checkReadyToProcess();
    }
}

function handleImagesFileSelect(e) {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
        imagesFiles = files;
        showImagesInfo(files);
        updateStepStatus(2, 'completed');
        checkReadyToProcess();
    }
}

function showExcelInfo(file) {
    const info = document.getElementById('excel-info');
    const nameSpan = document.getElementById('excel-name');
    
    nameSpan.textContent = `${file.name} (${formatFileSize(file.size)})`;
    info.classList.remove('hidden');
}

function showImagesInfo(files) {
    const info = document.getElementById('images-info');
    const countSpan = document.getElementById('images-count');
    
    // Group files by folder
    const folderMap = new Map();
    files.forEach(file => {
        const pathParts = file.webkitRelativePath.split('/');
        if (pathParts.length >= 2) {
            const studentId = pathParts[pathParts.length - 2];
            if (!folderMap.has(studentId)) {
                folderMap.set(studentId, []);
            }
            folderMap.get(studentId).push(file);
        }
    });
    
    const totalFolders = folderMap.size;
    const totalFiles = files.length;
    
    countSpan.textContent = `${totalFolders} folders, ${totalFiles} images`;
    info.classList.remove('hidden');
    
    // Show progress
    updateProgress(100);
}

function updateProgress(percentage) {
    const progressFill = document.getElementById('images-progress');
    const progressText = document.getElementById('images-progress-text');
    
    progressFill.style.width = percentage + '%';
    progressText.textContent = Math.round(percentage) + '%';
}

function removeExcelFile() {
    excelFile = null;
    document.getElementById('excel-file').value = '';
    document.getElementById('excel-info').classList.add('hidden');
    updateStepStatus(1, 'active');
    updateStepStatus(2, '');
    checkReadyToProcess();
}

function removeImagesFolder() {
    imagesFiles = [];
    document.getElementById('images-folder').value = '';
    document.getElementById('images-info').classList.add('hidden');
    updateStepStatus(2, 'active');
    checkReadyToProcess();
}

function updateStepStatus(stepNum, status) {
    const step = document.getElementById(`step${stepNum}`);
    step.classList.remove('active', 'completed');
    if (status) {
        step.classList.add(status);
    }
}

function checkReadyToProcess() {
    const processBtn = document.getElementById('process-btn');
    processBtn.disabled = !(excelFile && imagesFiles.length > 0);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function addLogEntry(message, type = 'info') {
    const logContainer = document.getElementById('log-container');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    
    const timestamp = new Date().toLocaleTimeString();
    entry.textContent = `[${timestamp}] ${message}`;
    
    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

async function processStudents() {
    if (!excelFile || imagesFiles.length === 0) {
        alert('Please upload both Excel file and image folder');
        return;
    }
    
    // Show log section
    document.getElementById('log-section').style.display = 'block';
    document.getElementById('log-container').innerHTML = '';
    
    // Update steps
    updateStepStatus(3, 'active');
    
    // Disable process button
    document.getElementById('process-btn').disabled = true;
    document.getElementById('process-btn').innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Processing...';
    
    try {
        addLogEntry('Starting student data processing', 'info');
        
        // Step 1: Upload Excel file
        addLogEntry('Uploading Excel file...', 'info');
        await uploadExcelFile();
        addLogEntry('✓ Excel file uploaded successfully', 'success');
        
        // Step 2: Upload images
        addLogEntry('Uploading image folder...', 'info');
        await uploadImagesFolder();
        addLogEntry('✓ Image folder uploaded successfully', 'success');
        
        // Step 3: Process data
        addLogEntry('Processing data and creating embeddings...', 'info');
        await processData();
        addLogEntry('✓ Data processing completed', 'success');
        
        // Step 4: Update database
        addLogEntry('Updating database...', 'info');
        await updateDatabase();
        addLogEntry('✓ Database updated successfully', 'success');
        
        // Complete
        updateStepStatus(3, 'completed');
        updateStepStatus(4, 'completed');
        
        addLogEntry('🎉 Complete! All students have been added to the system.', 'success');
        
        // Show success message
        setTimeout(() => {
            if (confirm('Students added successfully! Do you want to return to dashboard?')) {
                window.location.href = 'dashboard.html';
            }
        }, 2000);
        
    } catch (error) {
        addLogEntry(`❌ Error: ${error.message}`, 'error');
        updateStepStatus(3, 'error');
        
        // Re-enable process button
        document.getElementById('process-btn').disabled = false;
        document.getElementById('process-btn').innerHTML = '<i class="fas fa-cogs mr-2"></i>Retry Processing';
    }
}

async function uploadExcelFile() {
    const formData = new FormData();
    formData.append('file', excelFile);
    
    const response = await fetch('/api/upload-excel', {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Excel file upload failed');
    }
    
    return await response.json();
}

async function uploadImagesFolder() {
    const formData = new FormData();
    
    // Add all files with correct naming convention
    imagesFiles.forEach((file, index) => {
        const pathParts = file.webkitRelativePath.split('/');
        if (pathParts.length >= 2) {
            const studentId = pathParts[pathParts.length - 2];
            const originalFileName = pathParts[pathParts.length - 1];
            
            // Create a new File object with the correct name for the backend
            const newFile = new File([file], `images_${studentId}_${index}_${originalFileName}`, {
                type: file.type,
                lastModified: file.lastModified
            });
            
            formData.append('files', newFile);
        }
    });
    
    const response = await fetch('/api/upload-images', {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Image folder upload failed');
    }
    
    return await response.json();
}

async function processData() {
    const response = await fetch('/api/process-data', {
        method: 'POST'
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Data processing failed');
    }
    
    return await response.json();
}

async function updateDatabase() {
    const response = await fetch('/api/update-database', {
        method: 'POST'
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Database update failed');
    }
    
    return await response.json();
}

function logout() {
    if (confirm('Are you sure you want to logout?')) {
        window.location.href = 'login.html';
    }
}
