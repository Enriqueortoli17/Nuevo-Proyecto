/**
 * Notifications.js - Sistema de notificaciones
 * 
 * Este archivo contiene funciones para mostrar notificaciones toast
 * o mensajes de alerta al usuario.
 */

/**
 * Sistema de notificaciones para toda la aplicación
 */
const AppNotifications = (function() {
    'use strict';
    
    /**
     * Muestra una notificación toast
     * @param {string} message - Mensaje a mostrar
     * @param {string} type - Tipo de notificación: 'success', 'error', 'warning', 'info'
     * @param {number} duration - Duración en ms (por defecto 3000ms)
     */
    function showNotification(message, type = "success", duration = 3000) {
        // Remover notificaciones existentes
        $('.notification').remove();
        
        // Determinar icono y color según el tipo
        let icon, bgColor;
        
        switch(type) {
            case 'success':
                icon = 'check-circle';
                bgColor = 'var(--success-color)';
                break;
            case 'error':
                icon = 'exclamation-triangle';
                bgColor = 'var(--danger-color)';
                break;
            case 'warning':
                icon = 'exclamation-circle';
                bgColor = 'var(--warning-color)';
                break;
            case 'info':
            default:
                icon = 'info-circle';
                bgColor = 'var(--info-color)';
                break;
        }
        
        // Crear elemento de notificación
        const notification = $('<div class="notification"></div>')
            .css('background-color', bgColor)
            .html('<i class="fas fa-' + icon + '"></i> ' + message);
        
        // Agregar al DOM
        $('body').append(notification);
        
        // Configurar desaparición automática
        setTimeout(function() {
            notification.css('animation', 'fadeOut 0.5s forwards');
            setTimeout(function() {
                notification.remove();
            }, 500);
        }, duration);
    }
    
    /**
     * Muestra una confirmación modal para acciones importantes
     * @param {string} message - Mensaje de confirmación
     * @param {Function} onConfirm - Función a ejecutar si se confirma
     * @param {string} confirmText - Texto del botón de confirmación
     * @param {string} cancelText - Texto del botón de cancelación
     */
    function showConfirmation(message, onConfirm, confirmText = "Confirmar", cancelText = "Cancelar") {
        // Verificar si ya existe un modal de confirmación
        let confirmModal = $('#confirmationModal');
        
        // Crear el modal si no existe
        if (confirmModal.length === 0) {
            confirmModal = $(
                '<div class="modal fade" id="confirmationModal" tabindex="-1" role="dialog">' +
                    '<div class="modal-dialog" role="document">' +
                        '<div class="modal-content">' +
                            '<div class="modal-header">' +
                                '<h5 class="modal-title">' +
                                    '<i class="fas fa-question-circle mr-2"></i> Confirmación' +
                                '</h5>' +
                                '<button type="button" class="close" data-dismiss="modal" aria-label="Cerrar">' +
                                    '<span aria-hidden="true">&times;</span>' +
                                '</button>' +
                            '</div>' +
                            '<div class="modal-body">' +
                                '<p class="confirmation-message"></p>' +
                            '</div>' +
                            '<div class="modal-footer">' +
                                '<button type="button" class="btn btn-secondary" data-dismiss="modal">' +
                                    '<i class="fas fa-times mr-1"></i> <span class="cancel-text"></span>' +
                                '</button>' +
                                '<button type="button" class="btn btn-primary confirm-btn">' +
                                    '<i class="fas fa-check mr-1"></i> <span class="confirm-text"></span>' +
                                '</button>' +
                            '</div>' +
                        '</div>' +
                    '</div>' +
                '</div>'
            );
            
            $('body').append(confirmModal);
        }
        
        // Actualizar contenido del modal
        confirmModal.find('.confirmation-message').html(message);
        confirmModal.find('.confirm-text').text(confirmText);
        confirmModal.find('.cancel-text').text(cancelText);
        
        // Manejar acción de confirmación
        confirmModal.find('.confirm-btn').off('click').on('click', function() {
            if (typeof onConfirm === 'function') {
                onConfirm();
            }
            confirmModal.modal('hide');
        });
        
        // Mostrar modal
        confirmModal.modal('show');
    }
    
    // API pública
    return {
        showNotification: showNotification,
        showConfirmation: showConfirmation
    };
})();

// Compatibilidad con código existente
function showNotification(message, type = "success", duration = 3000) {
    AppNotifications.showNotification(message, type, duration);
}