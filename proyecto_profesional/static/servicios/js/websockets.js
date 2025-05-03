/**
 * WebSockets.js - Manejo de conexiones y eventos WebSocket
 * 
 * Este archivo contiene la configuración y gestión de conexiones
 * WebSocket para actualizaciones en tiempo real.
 */

/**
 * Módulo para gestionar WebSockets en la aplicación
 */
const AppWebSockets = (function() {
    'use strict';
    
    // Objetos de conexión WebSocket
    let socket_servicios = null;
    let socket_ordenes = null;
    
    // Callbacks de eventos
    const callbacks = {
        servicios: {},
        ordenes: {}
    };
    
    /**
     * Inicializa las conexiones WebSocket
     */
    function init() {
        const ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
        const host = window.location.host;
        
        // Inicializar conexión para servicios
        initServiciosSocket(ws_scheme, host);
        
        // Inicializar conexión para órdenes
        initOrdenesSocket(ws_scheme, host);
    }
    
    /**
     * Inicializa el WebSocket para servicios
     * @param {string} scheme - Esquema de conexión (ws o wss)
     * @param {string} host - Host para la conexión
     */
    function initServiciosSocket(scheme, host) {
        try {
            socket_servicios = new WebSocket(`${scheme}://${host}/ws/servicios/`);
            
            socket_servicios.onmessage = function(e) {
                const data = JSON.parse(e.data);
                
                // Invocar callbacks registrados para este tipo de mensaje
                if (data.type && callbacks.servicios[data.type]) {
                    callbacks.servicios[data.type].forEach(callback => callback(data));
                }
                
                // Actualizar visualización de servicios en la UI
                updateServiceDisplay(data);
            };
            
            socket_servicios.onclose = function(e) {
                console.warn("La conexión WebSocket de servicios se cerró. Intentando reconectar...");
                
                // Reconectar después de un tiempo
                setTimeout(function() {
                    initServiciosSocket(scheme, host);
                }, 3000);
            };
            
            socket_servicios.onerror = function(e) {
                console.error("Error en la conexión WebSocket de servicios:", e);
            };
        } catch (error) {
            console.error("Error al inicializar WebSocket de servicios:", error);
        }
    }
    
    /**
     * Inicializa el WebSocket para órdenes
     * @param {string} scheme - Esquema de conexión (ws o wss)
     * @param {string} host - Host para la conexión
     */
    function initOrdenesSocket(scheme, host) {
        try {
            socket_ordenes = new WebSocket(`${scheme}://${host}/ws/ordenes/`);
            
            socket_ordenes.onmessage = function(e) {
                const data = JSON.parse(e.data);
                
                // Invocar callbacks registrados para este tipo de mensaje
                if (data.type && callbacks.ordenes[data.type]) {
                    callbacks.ordenes[data.type].forEach(callback => callback(data));
                }
                
                // Manejar actualizaciones específicas
                handleOrdenUpdate(data);
            };
            
            socket_ordenes.onclose = function(e) {
                console.warn("La conexión WebSocket de órdenes se cerró. Intentando reconectar...");
                
                // Reconectar después de un tiempo
                setTimeout(function() {
                    initOrdenesSocket(scheme, host);
                }, 3000);
            };
            
            socket_ordenes.onerror = function(e) {
                console.error("Error en la conexión WebSocket de órdenes:", e);
            };
        } catch (error) {
            console.error("Error al inicializar WebSocket de órdenes:", error);
        }
    }
    
    /**
     * Actualiza la visualización de servicios en la UI
     * @param {Object} data - Datos recibidos por WebSocket
     */
    function updateServiceDisplay(data) {
        if (data.service_id) {
            const elementos = document.querySelectorAll(`[data-service-id="${data.service_id}"]`);
            
            elementos.forEach(function(elem) {
                // Limpiar clases de estado anteriores
                elem.classList.remove('estado-pendiente', 'estado-proceso', 'estado-terminado', 'estado-no-realizado');
                
                // Aplicar nueva clase según el estado
                if (data.estado === "TERMINADO") {
                    elem.classList.add('estado-terminado');
                } else if (data.estado === "NO_REALIZADO") {
                    elem.classList.add('estado-no-realizado');
                } else if (data.estado === "PROCESO") {
                    elem.classList.add('estado-proceso');
                } else {
                    elem.classList.add('estado-pendiente');
                }
            });
        }
    }
    
    /**
     * Maneja actualizaciones de órdenes
     * @param {Object} data - Datos recibidos por WebSocket
     */
    function handleOrdenUpdate(data) {
        // Orden terminada - eliminar de la vista
        if (data.type === "orden_terminada" && data.order_id) {
            const orderCard = document.getElementById(`order-card-${data.order_id}`);
            
            if (orderCard) {
                // Animación de desvanecimiento
                $(orderCard).fadeOut(300, function() {
                    $(this).remove();
                });
            }
        }
        
        // Actualización de estado de orden
        if (data.type === "orden_update" && data.order_id) {
            const orderCard = document.getElementById(`order-card-${data.order_id}`);
            
            if (orderCard) {
                // Actualizar atributo de estado
                orderCard.setAttribute("data-status", "proceso");
                
                // Actualizar etiqueta de estado
                const statusLabel = orderCard.querySelector(".orden-estado");
                if (statusLabel && data.nuevo_estado) {
                    statusLabel.textContent = data.nuevo_estado;
                    statusLabel.className = "orden-estado badge badge-warning";
                }
            }
        }
    }
    
    /**
     * Registra un callback para un tipo de mensaje específico
     * @param {string} socketType - Tipo de socket ('servicios' o 'ordenes')
     * @param {string} messageType - Tipo de mensaje a escuchar
     * @param {Function} callback - Función a ejecutar cuando se reciba el mensaje
     */
    function on(socketType, messageType, callback) {
        if (!callbacks[socketType][messageType]) {
            callbacks[socketType][messageType] = [];
        }
        
        callbacks[socketType][messageType].push(callback);
    }
    
    /**
     * Envía un mensaje a través del WebSocket
     * @param {string} socketType - Tipo de socket ('servicios' o 'ordenes')
     * @param {Object} data - Datos a enviar
     */
    function send(socketType, data) {
        const socket = socketType === 'servicios' ? socket_servicios : socket_ordenes;
        
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(data));
            return true;
        }
        
        console.warn(`WebSocket ${socketType} no está disponible para enviar.`);
        return false;
    }
    
    // API pública
    return {
        init: init,
        on: on,
        send: send
    };
})();

// Inicializar WebSockets al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    AppWebSockets.init();
});