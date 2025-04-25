// proyecto_profesional/static/js/tablero_ordenes.js

$(document).ready(function(){
    // --- Código JS para Sortable y WebSockets ---
    function initSortable() {
        $('.ordenes-row').sortable({
            connectWith: ".ordenes-row",
            handle: ".orden-header",
            placeholder: "ui-sortable-placeholder",
            forcePlaceholderSize: true,
            tolerance: "pointer",
            revert: 300,
            update: function(event, ui) {
                // Solo procesar si el item se soltó en este contenedor
                if (this === ui.item.parent()[0]) {
                    var grupo = $(this).closest('.seccion-dia').find('.seccion-header').text().trim();
                    var nuevoOrden = [];
                    $(this).children('.orden-card').each(function(index) {
                        var orderId = $(this).data('order-id');
                        nuevoOrden.push({ id: orderId, newPos: (index + 1) * 10 });
                    });
                    console.log("Enviando actualización para grupo:", grupo, "Nuevo orden:", nuevoOrden);
                    $.ajax({
                        url: "/servicios/actualizar-orden-manual/", // Asegúrate que esta URL sea correcta
                        method: "POST",
                        data: JSON.stringify({ grupo: grupo, nuevo_orden: nuevoOrden }),
                        contentType: "application/json",
                        dataType: "json",
                        headers: { "X-CSRFToken": $('input[name="csrfmiddlewaretoken"]').val() || "{{ csrf_token }}" }, // Obtener CSRF token
                        success: function(response) {
                            console.log("Orden actualizado", response);
                            // Aquí podrías usar AppNotifications si está cargado globalmente
                            // AppNotifications.showNotification("Orden del tablero actualizado.");
                        },
                        error: function(xhr, status, error) {
                            console.error("Error al actualizar el orden:", error);
                            // Revertir visualmente si falla
                            $(ui.sender).sortable('cancel');
                            // AppNotifications.showNotification("Error al actualizar orden.", "error");
                        }
                    });
                }
            }
        }).disableSelection();
    }
    initSortable();

    var ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
    var socket_servicios = new WebSocket(ws_scheme + '://' + window.location.host + '/ws/servicios/');
    var socket_ordenes = new WebSocket(ws_scheme + '://' + window.location.host + '/ws/ordenes/');

    socket_servicios.onmessage = function(e) {
        var data = JSON.parse(e.data);
        var elementos = document.querySelectorAll('[data-service-id="' + data.service_id + '"]');
        elementos.forEach(function(elem) {
            elem.classList.remove('estado-pendiente', 'estado-proceso', 'estado-no-realizado', 'estado-terminado');
            if (data.estado === "TERMINADO") elem.classList.add('estado-terminado');
            else if (data.estado === "NO_REALIZADO") elem.classList.add('estado-no-realizado');
            else if (data.estado === "PROCESO") elem.classList.add('estado-proceso');
            else elem.classList.add('estado-pendiente');
        });
    };

    socket_servicios.onclose = function(e) {
        console.error("Socket servicios cerrado. Intentando reconectar...");
         // Implementar lógica de reconexión si es necesario
        setTimeout(function() {
           socket_servicios = new WebSocket(ws_scheme + '://' + window.location.host + '/ws/servicios/');
        }, 5000); // Intenta reconectar cada 5 segundos
    };
    socket_servicios.onerror = function(err) {
        console.error('Error en socket de servicios:', err);
    };


    socket_ordenes.onmessage = function(e) {
        var data = JSON.parse(e.data);
        console.log("WS Órdenes:", data);
        if (data.type === "orden_terminada") {
            $("#order-card-" + data.order_id).fadeOut(300, function() { $(this).remove(); });
        } else if (data.type === "orden_reorder" || data.tipo === "orden_reorder") {
             // Evitar bucles: Solo actualizar si el mensaje NO fue originado por este cliente (si es posible)
            // O simplemente confiar en que el backend maneja la consistencia
            console.log("Recibido orden_reorder, actualizando tablero parcial.");
            actualizarTableroParcial();
        } else if (data.type === "servicio_agregado") {
            console.log("Recibido servicio_agregado, actualizando tablero parcial.");
            actualizarTableroParcial();
        } else if (data.type === "orden_aceptada") {
             console.log("Recibido orden_aceptada, actualizando tablero parcial.");
            actualizarTableroParcial();
        } else if (data.type === "orden_update") {
            var $card = $("#order-card-" + data.order_id);
            if($card.length > 0) {
                var $statusBadge = $card.find('.orden-estado');
                if (data.nuevo_estado) $statusBadge.text(data.nuevo_estado);
                // Aquí podrías actualizar más datos de la tarjeta si vienen en el mensaje WS
            }
        }
    };

    socket_ordenes.onclose = function(e) {
        console.error("Socket órdenes cerrado. Intentando reconectar...");
        // Implementar lógica de reconexión si es necesario
         setTimeout(function() {
           socket_ordenes = new WebSocket(ws_scheme + '://' + window.location.host + '/ws/ordenes/');
        }, 5000); // Intenta reconectar cada 5 segundos
    };
     socket_ordenes.onerror = function(err) {
        console.error('Error en socket de órdenes:', err);
    };

    function actualizarTableroParcial() {
        console.log("Solicitando tablero parcial...");
        $.ajax({
            url: "/servicios/tablero-parcial/?t=" + new Date().getTime(), // URL correcta y cache busting
            method: "GET",
            success: function(response) {
                $("#tablero-container").html(response);
                initSortable(); // Re-inicializar sortable después de cargar nuevo HTML
                console.log("Tablero parcial actualizado.");
            },
            error: function(xhr, status, error) {
                console.error("Error al actualizar tablero parcial:", error);
                 // AppNotifications.showNotification("Error al actualizar tablero.", "error");
            }
        });
    }
});