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

    // Reemplaza tu función onmessage existente con TODO este bloque:
    socket_ordenes.onmessage = function(e) {
        var data = JSON.parse(e.data);
        // --- Debugging General ---
        console.log("DEBUG [JS]: Mensaje WS recibido:", data);
        // --- Fin Debugging ---

        // Si el mensaje indica que se agregó un servicio, actualizar la tarjeta específica
        if (data.type === "servicio_agregado") {
        console.log("DEBUG [JS]: Procesando 'servicio_agregado'"); // Log adicional
        actualizarTarjetaOrden(data.order_id);
        }
        // Manejar reordenamiento si es necesario (¡Ojo! tu código anterior podría tener 'tipo' en vez de 'type')
        else if (data.type === "orden_reorder" || data.tipo === "orden_reorder") {
        console.log("DEBUG [JS]: Procesando 'orden_reorder', actualizando tablero..."); // Log adicional
        actualizarTableroServicios(); // Actualizar para reflejar nuevo orden
        }
        // ====> Bloque para Orden Terminada con Debugging <====
        else if (data.type === "orden_terminada") {
        // --- Debugging ---
        console.log("DEBUG [JS]: Recibido 'orden_terminada' para ID:", data.order_id);
        // --- Fin Debugging ---

        const orderId = data.order_id;

        // Intenta encontrar el elemento (Selector original de tu código)
        const cardElement = $("#order-card-" + orderId); // Usando jQuery como en tu código

        if (cardElement.length > 0) { // jQuery usa .length > 0 para verificar
            // --- Debugging ---
            console.log("DEBUG [JS]: Elemento encontrado para eliminar:", cardElement[0]); // Muestra el elemento DOM
            // --- Fin Debugging ---

            // Usa la animación que ya tenías
            cardElement.fadeOut(300, function() {
                $(this).remove();
                // --- Debugging ---
                console.log("DEBUG [JS]: Elemento eliminado del DOM.");
                // --- Fin Debugging ---
            });

        } else {
            // --- Debugging ---
            console.warn("DEBUG [JS]: Elemento de orden terminada NO encontrado en el DOM del tablero para ID:", orderId);
            // --- Fin Debugging ---
        }
        }
        // ====> Fin Bloque Orden Terminada <====

        // Si una orden es aceptada, actualizar toda la vista para que aparezca
        else if (data.type === "orden_aceptada") {
            console.log("DEBUG [JS]: Procesando 'orden_aceptada', actualizando tablero..."); // Log adicional
            actualizarTableroServicios(); // Recarga el contenido parcial
        }
        // Si el estado general de una orden cambia (ej. a PROCESO)
        else if (data.type === "orden_update") {
            // --- Debugging ---
            console.log("DEBUG [JS]: Recibido 'orden_update' para ID:", data.order_id, "Nuevo estado:", data.nuevo_estado);
            // --- Fin Debugging ---

            // Lógica existente para actualizar visualmente la tarjeta (badge)
            var $orderCard = $("#order-card-" + data.order_id);
            if ($orderCard.length > 0) {
                $orderCard.attr("data-status", "proceso"); // Asumiendo que el update es a proceso
                var $statusLabel = $orderCard.find(".orden-estado");
                if ($statusLabel.length > 0 && data.nuevo_estado) {
                    console.log("DEBUG [JS]: Actualizando badge de estado para", data.order_id); // Log adicional
                    let badgeClass = 'badge-secondary'; // default
                    // Ajustar el texto y la clase según el estado recibido
                    let textoEstado = data.nuevo_estado; // Usar el estado recibido
                    if (textoEstado === 'PROCESO' || textoEstado.toLowerCase().includes('proceso')) {
                        badgeClass = 'badge-warning';
                        textoEstado = 'En Proceso'; // Estandarizar texto si es necesario
                    } else if (textoEstado === 'LISTO') {
                        badgeClass = 'badge-success';
                        textoEstado = 'Listo';
                    } else if (textoEstado === 'ACEPTADA') {
                        badgeClass = 'badge-primary';
                        textoEstado = 'Aceptada';
                    }
                    $statusLabel.text(textoEstado); // Actualiza texto
                    $statusLabel.attr('class', 'orden-estado badge ' + badgeClass); // Reemplaza clases de badge
                }
            } else {
                console.warn("DEBUG [JS]: Elemento para 'orden_update' NO encontrado en DOM para ID:", data.order_id); // Log adicional
            }
        } else {
            // Mensaje para tipos no reconocidos (útil para depurar)
            console.log("DEBUG [JS]: Tipo de mensaje WS no manejado:", data.type);
        }
    }; // Fin de socket_ordenes.onmessage

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