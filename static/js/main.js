/**
 * Main JavaScript for Medical Expert System
 * Global utilities and event handlers
 */

// Global variables
let currentSession = {
    selectedSymptoms: [],
    diagnosisHistory: [],
    lastDiagnosis: null
};

// Utility functions
const Utils = {
    // Format timestamp
    formatTimestamp: function(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        return date.toLocaleString('vi-VN');
    },

    // Show notification
    showNotification: function(message, type = 'info') {
        const alertClass = `alert-${type}`;
        const icon = this.getNotificationIcon(type);
        
        const notification = $(`
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                <i class="${icon} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `);
        
        // Add to page
        $('main').prepend(notification);
        
        // Auto dismiss after 5 seconds
        setTimeout(() => {
            notification.alert('close');
        }, 5000);
    },

    // Get notification icon
    getNotificationIcon: function(type) {
        const icons = {
            success: 'fas fa-check-circle',
            warning: 'fas fa-exclamation-triangle',
            error: 'fas fa-times-circle',
            info: 'fas fa-info-circle'
        };
        return icons[type] || icons.info;
    },

    // Validate symptoms
    validateSymptoms: function(symptoms) {
        if (!Array.isArray(symptoms)) {
            return { valid: false, message: 'Triệu chứng phải là một danh sách' };
        }
        
        if (symptoms.length === 0) {
            return { valid: false, message: 'Vui lòng chọn ít nhất một triệu chứng' };
        }
        
        if (symptoms.length > 20) {
            return { valid: false, message: 'Tối đa 20 triệu chứng được phép chọn' };
        }
        
        return { valid: true };
    },

    // Debounce function
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Local storage utilities
    storage: {
        set: function(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
            } catch (e) {
                console.warn('Could not save to localStorage:', e);
            }
        },
        
        get: function(key, defaultValue = null) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : defaultValue;
            } catch (e) {
                console.warn('Could not read from localStorage:', e);
                return defaultValue;
            }
        },
        
        remove: function(key) {
            try {
                localStorage.removeItem(key);
            } catch (e) {
                console.warn('Could not remove from localStorage:', e);
            }
        }
    }
};

// API functions
const API = {
    // Get symptoms
    getSymptoms: function() {
        return $.ajax({
            url: '/api/symptoms',
            method: 'GET'
        });
    },

    // Get diseases
    getDiseases: function() {
        return $.ajax({
            url: '/api/diseases',
            method: 'GET'
        });
    },

    // Get statistics
    getStats: function() {
        return $.ajax({
            url: '/api/stats',
            method: 'GET'
        });
    },

    // Get history
    getHistory: function(limit = 10) {
        return $.ajax({
            url: `/api/history?limit=${limit}`,
            method: 'GET'
        });
    },

    // Perform diagnosis
    diagnose: function(symptoms) {
        return $.ajax({
            url: '/diagnose',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ symptoms: symptoms })
        });
    }
};

// Session management
const SessionManager = {
    // Initialize session
    init: function() {
        // Load saved session data
        const savedSession = Utils.storage.get('medical_expert_session', {});
        currentSession = {
            ...currentSession,
            ...savedSession
        };
        
        // Generate session ID if not exists
        if (!currentSession.sessionId) {
            currentSession.sessionId = 'session_' + Date.now();
            this.save();
        }
    },

    // Save session
    save: function() {
        Utils.storage.set('medical_expert_session', currentSession);
    },

    // Add diagnosis to history
    addDiagnosis: function(diagnosis) {
        currentSession.diagnosisHistory.unshift({
            timestamp: new Date().toISOString(),
            diagnosis: diagnosis
        });
        
        // Keep only last 50 diagnoses
        if (currentSession.diagnosisHistory.length > 50) {
            currentSession.diagnosisHistory = currentSession.diagnosisHistory.slice(0, 50);
        }
        
        currentSession.lastDiagnosis = diagnosis;
        this.save();
    },

    // Clear session
    clear: function() {
        currentSession = {
            selectedSymptoms: [],
            diagnosisHistory: [],
            lastDiagnosis: null,
            sessionId: currentSession.sessionId
        };
        this.save();
    }
};

// UI Components
const UI = {
    // Loading indicator
    showLoading: function(message = 'Đang xử lý...') {
        $('#loadingModal .modal-body h6').text(message);
        $('#loadingModal').modal('show');
    },

    hideLoading: function() {
        try {
            $('#loadingModal').modal('hide');
            // Force hide if modal doesn't respond
            setTimeout(() => {
                if ($('#loadingModal').hasClass('show')) {
                    $('#loadingModal').removeClass('show');
                    $('body').removeClass('modal-open');
                    $('.modal-backdrop').remove();
                }
            }, 100);
        } catch (e) {
            console.warn('Error hiding loading modal:', e);
        }
    },

    // Update statistics display
    updateStats: function(stats) {
        $('.stats-diseases').text(stats.total_diseases);
        $('.stats-symptoms').text(stats.total_symptoms);
        $('.stats-rules').text(stats.total_rules);
        $('.stats-diagnoses').text(stats.diagnosis_count);
    },

    // Animate element
    animateElement: function(selector, animation = 'fade-in') {
        const element = $(selector);
        element.addClass(animation);
        setTimeout(() => {
            element.removeClass(animation);
        }, 500);
    }
};

// Event handlers
$(document).ready(function() {
    // Initialize session
    SessionManager.init();

    // Global error handler for AJAX
    $(document).ajaxError(function(event, xhr, settings) {
        console.error('AJAX Error:', xhr.status, xhr.statusText);
        
        let message = 'Có lỗi xảy ra khi kết nối với máy chủ';
        
        if (xhr.status === 404) {
            message = 'Không tìm thấy tài nguyên yêu cầu';
        } else if (xhr.status === 500) {
            message = 'Lỗi máy chủ nội bộ';
        } else if (xhr.status === 0) {
            message = 'Không thể kết nối đến máy chủ';
        }
        
        Utils.showNotification(message, 'error');
        UI.hideLoading();
    });

    // Global success handler for AJAX
    $(document).ajaxSuccess(function(event, xhr, settings) {
        // Hide loading if it's showing
        if ($('#loadingModal').hasClass('show')) {
            UI.hideLoading();
        }
    });

    // Global complete handler for AJAX
    $(document).ajaxComplete(function(event, xhr, settings) {
        // Ensure loading modal is hidden after any AJAX request
        if ($('#loadingModal').hasClass('show')) {
            UI.hideLoading();
        }
    });

    // Keyboard shortcuts
    $(document).keydown(function(e) {
        // Ctrl/Cmd + Enter to submit diagnosis
        if ((e.ctrlKey || e.metaKey) && e.keyCode === 13) {
            e.preventDefault();
            $('#diagnosisForm').submit();
        }
        
        // Escape to clear selection
        if (e.keyCode === 27) {
            $('#clearSelection').click();
        }
    });

    // Smooth scroll for anchor links
    $('a[href^="#"]').on('click', function(e) {
        e.preventDefault();
        const target = $(this.getAttribute('href'));
        if (target.length) {
            $('html, body').animate({
                scrollTop: target.offset().top - 80
            }, 500);
        }
    });

    // Tooltip initialization
    $('[data-bs-toggle="tooltip"]').tooltip();

    // Print functionality
    $('.print-btn').on('click', function() {
        window.print();
    });

    // Copy to clipboard functionality
    $('.copy-btn').on('click', function() {
        const text = $(this).data('text');
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                Utils.showNotification('Đã sao chép vào clipboard', 'success');
            });
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            Utils.showNotification('Đã sao chép vào clipboard', 'success');
        }
    });

    // Note: Checkbox handling is now done in templates/index.html
    // This prevents conflicts between multiple event handlers

    // Don't restore selected symptoms on page load - start fresh each time
    // Clear any previously selected symptoms
    $('input[type="checkbox"]').prop('checked', false);
    currentSession.selectedSymptoms = [];
    SessionManager.save();
    
    // Clear the selected symptoms display
    updateSelectedSymptomsDisplay();
    
    // Hide diagnosis card on fresh load
    $('#diagnosisCard').hide();

    // Welcome message for first-time users
    if (!Utils.storage.get('has_visited')) {
        setTimeout(() => {
            Utils.showNotification(
                'Chào mừng bạn đến với Hệ Chuyên Gia Y Tế! Chọn các triệu chứng và nhấn "Chẩn Đoán" để bắt đầu.',
                'info'
            );
            Utils.storage.set('has_visited', true);
        }, 1000);
    }
    
    // Add click handler to hide loading modal if user clicks outside
    $(document).on('click', function(e) {
        if ($(e.target).closest('#loadingModal').length === 0 && $('#loadingModal').hasClass('show')) {
            $('#loadingModal').modal('hide');
        }
    });
    
    // Add escape key handler to hide loading modal
    $(document).on('keydown', function(e) {
        if (e.keyCode === 27 && $('#loadingModal').hasClass('show')) {
            $('#loadingModal').modal('hide');
        }
    });
    
    // Handle page reload/refresh - clear all selections
    $(window).on('beforeunload', function() {
        // Clear selected symptoms from session
        currentSession.selectedSymptoms = [];
        SessionManager.save();
        
        // Clear session storage
        if (typeof sessionStorage !== 'undefined') {
            sessionStorage.removeItem('selectedSymptoms');
        }
    });
    
    // Force clear on page load
    $(window).on('load', function() {
        // Ensure all checkboxes are unchecked
        $('input[type="checkbox"]').prop('checked', false);
        
        // Clear selected symptoms array
        selectedSymptoms = [];
        
        // Update display
        updateSelectedSymptomsDisplay();
        
        // Hide diagnosis card
        $('#diagnosisCard').hide();
    });
});

// Export for use in other scripts
window.MedicalExpertSystem = {
    Utils,
    API,
    SessionManager,
    UI,
    currentSession
}; 