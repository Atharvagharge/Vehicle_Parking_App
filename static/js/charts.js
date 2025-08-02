// Chart.js integration for dashboard charts
document.addEventListener('DOMContentLoaded', function() {
    // Function to create parking lot status chart
    function createParkingStatusChart(canvasId, availableSpots, occupiedSpots) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Available', 'Occupied'],
                datasets: [{
                    data: [availableSpots, occupiedSpots],
                    backgroundColor: ['#28a745', '#dc3545'],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            font: {
                                size: 12
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Function to create booking trends chart
    function createBookingTrendsChart(canvasId, bookingData) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: bookingData.labels,
                datasets: [{
                    label: 'Bookings',
                    data: bookingData.data,
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }
    
    // Initialize charts if data is available
    if (typeof chartData !== 'undefined') {
        if (chartData.parkingStatus) {
            createParkingStatusChart('parkingStatusChart', 
                chartData.parkingStatus.available, 
                chartData.parkingStatus.occupied);
        }
        
        if (chartData.bookingTrends) {
            createBookingTrendsChart('bookingTrendsChart', chartData.bookingTrends);
        }
    }
    
    // Auto-refresh dashboard data every 30 seconds
    function refreshDashboard() {
        // Add AJAX call to refresh dashboard data
        fetch('/api/dashboard_data')
            .then(response => response.json())
            .then(data => {
                // Update dashboard elements with new data
                console.log('Dashboard refreshed');
            })
            .catch(error => console.error('Error refreshing dashboard:', error));
    }
    
    // Set interval for auto-refresh (optional)
    // setInterval(refreshDashboard, 30000);
    
    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // Confirmation dialogs for delete actions
    const deleteButtons = document.querySelectorAll('[data-confirm]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                event.preventDefault();
            }
        });
    });
});

// Utility functions
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<div class="loading"></div>';
    }
}

function hideLoading(elementId, content) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = content;
    }
}

// Real-time updates using Server-Sent Events (optional enhancement)
function initializeRealTimeUpdates() {
    if (typeof(EventSource) !== "undefined") {
        const source = new EventSource('/stream');
        source.onmessage = function(event) {
            const data = JSON.parse(event.data);
            // Update UI with real-time data
            console.log('Real-time update:', data);
        };
    }
}