// Dashboard JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // WebSocket connection
    let socket = null;
    let attendanceData = [];
    
    // Initialize dashboard
    initializeDashboard();
    
    function initializeDashboard() {
        // Load initial data from API
        loadTodayAttendance();
        
        // Connect to WebSocket for real-time updates
        connectWebSocket();
        
        // Initialize sidebar interactions
        initializeSidebar();
        
        // Initialize other features
        initializeOtherFeatures();
    }
    
    // Load attendance data from API
    async function loadTodayAttendance() {
        try {
            showLoading();
            const response = await fetch('/today-checkins');
            const result = await response.json();
            
            if (result.success) {
                attendanceData = result.data;
                updateTable();
                console.log(`✅ Loaded ${result.total} attendance records`);
            } else {
                console.error('Failed to load attendance data');
                showError('Unable to load attendance data');
            }
        } catch (error) {
            console.error('Error loading attendance data:', error);
            showError('Connection error while loading data');
        } finally {
            hideLoading();
        }
    }
    
    // Connect to WebSocket
    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const socketUrl = `${protocol}//${window.location.host}/ws/attendance`;
        
        socket = new WebSocket(socketUrl);
        
        socket.onopen = function(event) {
            console.log('✅ WebSocket connected');
            showNotification('Real-time connection successful', 'success');
        };
        
        socket.onmessage = function(event) {
            try {
                const newAttendance = JSON.parse(event.data);
                console.log('📨 Received new attendance:', newAttendance);
                
                // Add new attendance to the beginning of the array
                attendanceData.unshift(newAttendance);
                
                // Update table
                updateTable();
                
                // Show notification
                showNotification(`🎉 ${newAttendance.name} (${newAttendance.student_id}) has successfully checked in!`, 'success');
                
                // Play notification sound (optional)
                playNotificationSound();
                
            } catch (error) {
                console.error('Error processing WebSocket message:', error);
            }
        };
        
        socket.onclose = function(event) {
            console.log('❌ WebSocket disconnected');
            showNotification('Real-time connection lost. Attempting to reconnect...', 'warning');
            
            // Reconnect after 3 seconds
            setTimeout(connectWebSocket, 3000);
        };
        
        socket.onerror = function(error) {
            console.error('WebSocket error:', error);
            showNotification('Real-time connection error', 'error');
        };
    }
    
    // Update table with current data
    function updateTable() {
        const tableBody = document.getElementById('attendanceTableBody');
        
        if (attendanceData.length === 0) {
            tableBody.innerHTML = `
                <tr id="noDataRow">
                    <td colspan="6" class="px-6 py-8 text-center text-gray-500">
                        <i class="fas fa-clock text-4xl mb-4"></i>
                        <p class="text-lg">No students have attended today</p>
                        <p class="text-sm">Data will automatically update when students attend</p>
                    </td>
                </tr>
            `;
            return;
        }
        
        tableBody.innerHTML = attendanceData.map((student, index) => {
            const checkinImage = student.checkin_face_base64 
                ? `<img src="data:image/jpeg;base64,${student.checkin_face_base64}" alt="Recent Check-in" class="attendance-image">`
                : `<div class="image-placeholder">
                     <i class="fas fa-camera text-gray-500 text-xl"></i>
                   </div>`;
            
            const avatarImage = student.avatar_base64 
                ? `<img src="data:image/jpeg;base64,${student.avatar_base64}" alt="Avatar" class="attendance-image">`
                : `<div class="image-placeholder">
                     <i class="fas fa-user text-gray-500 text-xl"></i>
                   </div>`;
            
            const formattedTime = formatDateTime(student.attendance_time);
            
            return `
                <tr class="border-b border-gray-200 hover:bg-gray-50" data-student-id="${student.student_id}">
                    <td class="px-6 py-4 text-lg text-gray-800">${index + 1}</td>
                    <td class="px-6 py-4">${checkinImage}</td>
                    <td class="px-6 py-4">${avatarImage}</td>
                    <td class="px-6 py-4 text-lg font-medium text-gray-800">${student.name}</td>
                    <td class="px-6 py-4 text-lg text-gray-800">${student.student_id}</td>
                    <td class="px-6 py-4 text-lg text-gray-800">${formattedTime}</td>
                </tr>
            `;
        }).join('');
        
        // Add click events to rows
        addTableRowEvents();
    }
    
    // Format datetime for display
    function formatDateTime(dateTimeString) {
        try {
            const date = new Date(dateTimeString);
            return date.toLocaleString('en-US', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            }).replace(',', '<br>');
        } catch (error) {
            return dateTimeString;
        }
    }
    
    // Initialize sidebar interactions
    function initializeSidebar() {
        const sidebarItems = document.querySelectorAll('.sidebar-item');
        
        sidebarItems.forEach(item => {
            item.addEventListener('click', function() {
                // Remove active class from all items
                sidebarItems.forEach(i => i.classList.remove('active'));
                // Add active class to clicked item
                this.classList.add('active');
            });
        });
        
        // Logout functionality
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', function() {
                if (confirm('Bạn có chắc chắn muốn đăng xuất?')) {
                    // Clear any stored session data
                    localStorage.removeItem('userToken');
                    sessionStorage.clear();
                    
                    // Redirect to login page (root URL)
                    window.location.href = '/';
                }
            });
        }
        
        // Add Student functionality (placeholder)
        const addStudentBtn = document.querySelector('.sidebar-item:nth-child(2)');
        if (addStudentBtn) {
            addStudentBtn.addEventListener('click', function() {
                alert('Chức năng thêm sinh viên đang được phát triển!');
            });
        }
    }
    
    // Initialize other features
    function initializeOtherFeatures() {
        // Real-time clock update
        function updateClock() {
            const now = new Date();
            const timeString = now.toLocaleString('vi-VN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
            
            // Update any clock elements if they exist
            const clockElements = document.querySelectorAll('.clock');
            clockElements.forEach(element => {
                element.textContent = timeString;
            });
        }
        
        // Update clock every second
        setInterval(updateClock, 1000);
        updateClock(); // Initial call
        
        // Responsive sidebar for mobile
        function handleResize() {
            const sidebar = document.querySelector('.sidebar');
            const mainContent = document.querySelector('.main-content');
            
            if (window.innerWidth <= 768) {
                sidebar.style.position = 'fixed';
                sidebar.style.bottom = '0';
                sidebar.style.left = '0';
                sidebar.style.width = '100%';
                sidebar.style.height = 'auto';
                sidebar.style.flexDirection = 'row';
                sidebar.style.justifyContent = 'space-around';
                
                mainContent.style.marginLeft = '0';
                mainContent.style.paddingBottom = '80px';
            } else {
                sidebar.style.position = 'fixed';
                sidebar.style.top = '0';
                sidebar.style.left = '0';
                sidebar.style.width = '64px';
                sidebar.style.height = '100vh';
                sidebar.style.flexDirection = 'column';
                sidebar.style.justifyContent = 'flex-start';
                
                mainContent.style.marginLeft = '64px';
                mainContent.style.paddingBottom = '0';
            }
        }
        
        // Handle window resize
        window.addEventListener('resize', handleResize);
        handleResize(); // Initial call
    }
    
    // Add click events to table rows
    function addTableRowEvents() {
        const tableRows = document.querySelectorAll('tbody tr[data-student-id]');
        tableRows.forEach(row => {
            row.addEventListener('click', function() {
                const studentId = this.getAttribute('data-student-id');
                const studentName = this.querySelector('td:nth-child(4)').textContent;
                
                // Show student details (placeholder)
                console.log(`Selected student: ${studentName} (ID: ${studentId})`);
                
                // You can add more functionality here like showing a modal with student details
            });
        });
    }
    
    // Show notification
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        // Add notification styles
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            z-index: 1000;
            animation: slideIn 0.3s ease-out;
        `;
        
        // Set background color based on type
        switch (type) {
            case 'success':
                notification.style.backgroundColor = '#10b981';
                break;
            case 'error':
                notification.style.backgroundColor = '#ef4444';
                break;
            case 'warning':
                notification.style.backgroundColor = '#f59e0b';
                break;
            default:
                notification.style.backgroundColor = '#3b82f6';
        }
        
        document.body.appendChild(notification);
        
        // Remove notification after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
    
    // Show error message
    function showError(message) {
        showNotification(message, 'error');
    }
    
    // Play notification sound
    function playNotificationSound() {
        try {
            const audio = new Audio();
            audio.src = 'data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhAUCR0O+leiYIHYPK9NaJOwcfcsHs4KlICAcUdLTT2LGQXgwqUMTl3GEgAT2SsOqfeSQFM3vB7N1vSw4QTa7T4KdvIwweD9+J/kqGUHMEBgARAVBmGOb7nqQAIABFGAhkfGa6KCEBQhrDqGzWvfgEQb0qGBJnuMEaLBYAfxhVQCIRGABXSFKOQRb0K2kTFAZ2dGrS6xhVYSUKHxR3EqMaVU4gBhJPEyxK5wNYHIIDnIgASQBnS5E4oagKABjRXYlGZ4YYCQGiGQUhJDJiEIlEgQOEgkJqaxFzWMZgQALfCEOFlkUQHFQNYEQHFYM8YnqFWGApAZ6nMXhGYx5nCwOcgUNAeBcFfxVHpF4FXQYBxmtPE0iYGkgJNBAAixxLCvgHgZsOY1YAFnQEG3FdM0gdZBNBJRRh9JMwl8DYjCCaKt5aDgJJaJBJOgwxNJhOXDEg';
            audio.play().catch(e => console.log('Could not play notification sound'));
        } catch (error) {
            console.log('Notification sound not available');
        }
    }
    
    // Search functionality (if needed in the future)
    function searchStudents(query) {
        const rows = document.querySelectorAll('tbody tr[data-student-id]');
        rows.forEach(row => {
            const name = row.querySelector('td:nth-child(4)').textContent.toLowerCase();
            const id = row.querySelector('td:nth-child(5)').textContent.toLowerCase();
            
            if (name.includes(query.toLowerCase()) || id.includes(query.toLowerCase())) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }
    
    // Add loading animation
    function showLoading() {
        const loadingDiv = document.createElement('div');
        loadingDiv.id = 'loading';
        loadingDiv.innerHTML = `
            <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div class="bg-white p-6 rounded-lg shadow-lg">
                    <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-600 mx-auto"></div>
                    <p class="mt-4 text-gray-700">Đang tải...</p>
                </div>
            </div>
        `;
        document.body.appendChild(loadingDiv);
    }
    
    function hideLoading() {
        const loadingDiv = document.getElementById('loading');
        if (loadingDiv) {
            loadingDiv.remove();
        }
    }
    
    // Export functions for potential use
    window.dashboardUtils = {
        loadTodayAttendance,
        searchStudents,
        showLoading,
        hideLoading,
        showNotification,
        connectWebSocket
    };
    
    console.log('Dashboard initialized successfully!');
});
