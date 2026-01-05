// HPL Inventory Management System - Custom JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize all popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            if (alert.classList.contains('alert-dismissible')) {
                var bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        });
    }, 5000);
    
    // Sidebar toggle for mobile
    var sidebarToggle = document.querySelector('[data-bs-toggle="collapse"][data-bs-target="#sidebarMenu"]');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            document.querySelector('#sidebarMenu').classList.toggle('collapse');
        });
    }
    
    // Confirm dialogs for destructive actions
    var confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            var message = this.getAttribute('data-confirm') || 'Are you sure?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // Auto-resize textareas
    var textareas = document.querySelectorAll('textarea[auto-resize]');
    textareas.forEach(function(textarea) {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    });
    
    // Form validation styles
    var forms = document.querySelectorAll('.needs-validation');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // Date picker initialization
    var dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(function(input) {
        if (input.valueAsDate === null) {
            // Set default to today if no value
            input.valueAsDate = new Date();
        }
    });
});

// Utility functions
var Utils = {
    // Format date to string
    formatDate: function(date, format) {
        var options = { year: 'numeric', month: 'short', day: 'numeric' };
        return date.toLocaleDateString('en-US', options);
    },
    
    // Format datetime to string
    formatDateTime: function(date) {
        var options = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
        return date.toLocaleDateString('en-US', options);
    },
    
    // Debounce function
    debounce: function(func, wait) {
        var timeout;
        return function() {
            var context = this, args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(function() {
                func.apply(context, args);
            }, wait);
        };
    },
    
    // Get URL parameter
    getUrlParam: function(name) {
        var urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(name);
    },
    
    // Set URL parameter
    setUrlParam: function(name, value) {
        var urlParams = new URLSearchParams(window.location.search);
        urlParams.set(name, value);
        window.history.replaceState({}, '', window.location.pathname + '?' + urlParams.toString());
    },
    
    // Remove URL parameter
    removeUrlParam: function(name) {
        var urlParams = new URLSearchParams(window.location.search);
        urlParams.delete(name);
        window.history.replaceState({}, '', window.location.pathname + '?' + urlParams.toString());
    }
};

// API helper functions
var API = {
    baseUrl: '/',
    
    get: function(endpoint, data) {
        var url = this.baseUrl + endpoint;
        if (data) {
            url += '?' + new URLSearchParams(data).toString();
        }
        return fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(response => response.json());
    },
    
    post: function(endpoint, data) {
        return fetch(this.baseUrl + endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        }).then(response => response.json());
    },
    
    getCookie: function(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
};

// Notification helper
var Notifications = {
    show: function(message, type) {
        var alertClass = type || 'info';
        var alertHtml = '<div class="alert alert-' + alertClass + ' alert-dismissible fade show" role="alert">' +
            message +
            '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>' +
            '</div>';
        
        var container = document.querySelector('.alert-container') || document.querySelector('.container-fluid');
        var alert = document.createElement('div');
        alert.innerHTML = alertHtml;
        alert.className = 'alert-container position-fixed top-0 end-0 p-3';
        alert.style.zIndex = '9999';
        
        document.body.appendChild(alert);
        
        // Auto-remove after 5 seconds
        setTimeout(function() {
            var bsAlert = new bootstrap.Alert(alert.querySelector('.alert'));
            bsAlert.close();
        }, 5000);
    },
    
    success: function(message) {
        this.show(message, 'success');
    },
    
    error: function(message) {
        this.show(message, 'danger');
    },
    
    warning: function(message) {
        this.show(message, 'warning');
    },
    
    info: function(message) {
        this.show(message, 'info');
    }
};

// Export utilities
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { Utils: Utils, API: API, Notifications: Notifications };
}
