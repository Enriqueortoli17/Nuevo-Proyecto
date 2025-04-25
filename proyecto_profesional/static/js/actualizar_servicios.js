// proyecto_profesional/static/js/actualizar_servicios.js

$(document).ready(function(){
    // Función para mostrar notificaciones (puede ser global o definida aquí)
    function showNotification(message, type = "success") {
      $('.notification').remove();
      var icon = type === "success" ? "check-circle" : "exclamation-triangle";
      var bgColor = type === "success" ? "var(--success-color)" : "var(--danger-color)";

      var notification = $('<div class="notification"></div>')
        .css('background-color', bgColor)
        .html('<i class="fas fa-' + icon + '"></i> ' + message);

      $('body').append(notification);

      setTimeout(function() {
        notification.css('animation', 'fadeOut 0.5s forwards');
        setTimeout(function() {
          notification.remove();
        }, 500);
      }, 3000);
    }

    // Inicializar sortable para cada contenedor individualmente
    function initSortable() {
      $('.sortable-group').each(function() {
          var grupo = $(this).data('grupo');
          if (grupo === "Pendientes") {
              $(this).sortable({
                  disabled: true,
                  placeholder: "ui-state-highlight" // Aún definir el placeholder es útil visualmente
              });
          } else {
              $(this).sortable({
                  connectWith: ".sortable-group",
                  placeholder: "ui-state-highlight",
                  handle: ".orden-basica", // El elemento que inicia el arrastre
                  helper: 'clone', // Usar un clon visual mientras se arrastra
                  forcePlaceholderSize: true,
                  // Función update para enviar el nuevo orden vía AJAX
                  update: function(event, ui) {
                      // Solo procesar si el item se soltó en este contenedor
                      if (this === ui.item.parent()[0]) {
                          var grupo = $(this).data('grupo');
                          var nuevoOrden = [];
                          $(this).children('.orden-card').each(function(index) {
                              var orderId = $(this).data('order-id');
                              // Asigna una posición basada en el índice (por ejemplo, 10, 20, 30, ...)
                              nuevoOrden.push({
                                  id: orderId,
                                  newPos: (index + 1) * 10
                              });
                          });

                          $.ajax({
                              url: "/servicios/actualizar-orden-manual/", // URL a tu endpoint
                              method: "POST",
                              data: JSON.stringify({
                                  grupo: grupo,
                                  nuevo_orden: nuevoOrden
                              }),
                              contentType: "application/json",
                              dataType: "json",
                              headers: {
                                  "X-CSRFToken": $('input[name="csrfmiddlewaretoken"]').val() // Obtener CSRF
                              },
                              success: function(response) {
                                  showNotification("Orden actualizado correctamente");
                                  // Actualizar data-old-pos para consistencia si es necesario
                                  $(this).children('.orden-card').each(function(index) {
                                      $(this).attr('data-old-pos', (index + 1) * 10);
                                  });
                              }.bind(this), // Asegurar 'this' correcto en success
                              error: function(xhr, status, error) {
                                  showNotification("Error al actualizar el orden: " + error, "error");
                                  // Revertir visualmente si falla
                                  $(ui.sender).sortable('cancel');
                              }
                          });
                      }
                  }
              });
          }
      });
    } // fin initSortable

    // Delegar el clic del botón Agregar Servicio
    $(document).on('click', '.agregar-servicio-btn', function(){
      var orderId = $(this).data('order-id');
      $('#order_id').val(orderId); // Poner el ID en el campo oculto del modal
      $('#formAgregarServicio')[0].reset(); // Limpiar el formulario
      $('#div_nombre_custom').hide(); // Ocultar campo custom por defecto
      $('#modalAgregarServicio').modal('show'); // Mostrar el modal
    });

    // Actualización de estado de servicios vía AJAX
    $(document).on('change', '.estado-select', function(){
      var serviceId = $(this).data('service-id');
      var nuevoEstado = $(this).val();
      var select = $(this); // Guardar referencia al select

      select.prop('disabled', true); // Deshabilitar mientras se guarda

      $.ajax({
        url: "/servicios/ajax/actualizar_estado_servicio/", // URL a tu endpoint
        method: "POST",
        data: JSON.stringify({
          service_id: serviceId,
          estado: nuevoEstado
        }),
        contentType: "application/json",
        dataType: "json",
        headers: {
          "X-CSRFToken": $('input[name="csrfmiddlewaretoken"]').val() // Obtener CSRF
        },
        success: function(response){
          select.prop('disabled', false); // Habilitar de nuevo
          showNotification("Estado actualizado correctamente");

          // Actualizar la clase del contenedor del servicio para reflejar el estado visualmente
          var servicioItem = select.closest('.servicio-item');
          servicioItem.removeClass('estado-pendiente estado-proceso estado-terminado estado-no-realizado');
          if (nuevoEstado === 'TERMINADO') {
            servicioItem.addClass('estado-terminado');
          } else if (nuevoEstado === 'PROCESO') {
            servicioItem.addClass('estado-proceso');
          } else if (nuevoEstado === 'NO_REALIZADO') {
            servicioItem.addClass('estado-no-realizado');
          } else {
            servicioItem.addClass('estado-pendiente');
          }

          // Opcional: Actualizar el estado general de la orden visualmente si cambia
          var orderCard = select.closest('.orden-card');
          var statusBadge = orderCard.find('.orden-estado');
          if (statusBadge.length > 0 && response.orden_estado) {
               let badgeClass = 'badge-secondary'; // default
               if (response.orden_estado === 'PROCESO') badgeClass = 'badge-warning';
               else if (response.orden_estado === 'LISTO') badgeClass = 'badge-success';
               else if (response.orden_estado === 'ACEPTADA') badgeClass = 'badge-primary';
               // Actualizar texto y clase
               statusBadge.text(response.orden_estado); // Asume que response.orden_estado es el texto display
               statusBadge.attr('class', 'orden-estado badge ' + badgeClass); // Reemplaza todas las clases de badge
          }

        },
        error: function(xhr, status, error){
          select.prop('disabled', false); // Habilitar de nuevo en caso de error
          showNotification("Error en la actualización: " + error, "error");
          // Opcional: revertir el select al valor anterior si falla
          // select.val(select.find('option[selected]').val());
        }
      });
    });

    // Conexión WebSocket para notificaciones en tiempo real
    var ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
    var socket_ordenes = new WebSocket(ws_scheme + '://' + window.location.host + '/ws/ordenes/');

    socket_ordenes.onmessage = function(e) {
      var data = JSON.parse(e.data);
      // Si el mensaje indica que se agregó un servicio, actualizar la tarjeta específica
      if (data.type === "servicio_agregado") {
        actualizarTarjetaOrden(data.order_id);
      }
      // Ignorar reorder aquí si esta página no debe reflejarlo en tiempo real,
      // o llamar a actualizarTableroServicios() si sí debe.
      else if (data.tipo === "orden_reorder") {
        console.log("Orden reordenada por WebSocket, actualizando tablero...");
        actualizarTableroServicios(); // Actualizar para reflejar nuevo orden
      }
      // Si una orden termina, quitarla de esta vista
      else if (data.type === "orden_terminada") {
        $("#order-card-" + data.order_id).fadeOut(300, function() {
          $(this).remove();
        });
      }
      // Si una orden es aceptada, actualizar toda la vista para que aparezca
      else if (data.type === "orden_aceptada") {
          console.log("Orden aceptada recibida:", data);
          actualizarTableroServicios(); // Recarga el contenido parcial
      }
      // Si el estado general de una orden cambia (ej. a PROCESO)
      else if (data.type === "orden_update") {
          var $orderCard = $("#order-card-" + data.order_id);
          if ($orderCard.length > 0) {
              $orderCard.attr("data-status", "proceso"); // Asumiendo que el update es a proceso
              var $statusLabel = $orderCard.find(".orden-estado");
              if ($statusLabel.length > 0 && data.nuevo_estado) {
                   let badgeClass = 'badge-secondary'; // default
                   if (data.nuevo_estado === 'En proceso') badgeClass = 'badge-warning'; // Ajustar texto si es necesario
                   else if (data.nuevo_estado === 'Listo') badgeClass = 'badge-success';
                   else if (data.nuevo_estado === 'Aceptada') badgeClass = 'badge-primary';
                   $statusLabel.text(data.nuevo_estado);
                   $statusLabel.attr('class', 'orden-estado badge ' + badgeClass);
              }
          }
      }
    };

    socket_ordenes.onclose = function(e) {
      console.error("La conexión WebSocket de órdenes se cerró inesperadamente. Intentando reconectar...");
      setTimeout(function() {
         socket_ordenes = new WebSocket(ws_scheme + '://' + window.location.host + '/ws/ordenes/');
      }, 3000); // Reintentar conexión
    };
    socket_ordenes.onerror = function(err) {
        console.error('Error en socket de órdenes:', err);
    };


    // Función para actualizar la tarjeta de una orden mediante AJAX
    function actualizarTarjetaOrden(orderId) {
      $.ajax({
        url: "/servicios/orden_parcial/" + orderId + "/", // URL a la vista parcial
        method: "GET",
        success: function(response) {
          // Reemplaza el contenido de la tarjeta específica
          var $card = $("#order-card-" + orderId);
          if($card.length > 0){
              var $newCard = $(response); // Convertir la respuesta HTML en objeto jQuery
              $card.html($newCard.html()); // Reemplazar solo el contenido interno
              // Opcional: Re-adjuntar eventos si es necesario, aunque la delegación debería funcionar
          } else {
               console.warn("No se encontró la tarjeta para actualizar:", orderId);
               actualizarTableroServicios(); // Si no se encuentra, recargar todo
          }

        },
        error: function(xhr, status, error) {
          showNotification("Error al actualizar la tarjeta de orden", "error");
        }
      });
    }

    // Función para actualizar el tablero parcial vía AJAX
    // (Esta función ahora recarga el contenido específico de esta página)
    function actualizarTableroServicios() {
        $.ajax({
            url: "/servicios/actualizar_servicios_parcial/?t=" + new Date().getTime(), // URL a la vista parcial de servicios
            method: "GET",
            success: function(response) {
                $("#tablero-container").html(response); // Reemplaza el contenido del tablero
                initSortable(); // Reinicializa sortable
            },
            error: function(xhr, status, error) {
                showNotification("Error al actualizar servicios: " + error, "error");
            }
        });
    }


    // Funcionalidad del modal para agregar servicio
    $('#servicio_select').change(function(){
      if ($(this).val() == "custom") {
        $('#div_nombre_custom').show(); // Mostrar campo nombre custom
      } else {
        $('#div_nombre_custom').hide(); // Ocultar campo nombre custom
      }
    });

    $('#btnGuardarServicio').click(function(){
      var data = {
        order_id: $('#order_id').val(),
        servicio_id: $('#servicio_select').val(),
        nombre_custom: $('#nombre_custom').val(),
        cantidad: $('#cantidad_servicio').val(),
        observacion: $('#observacion_servicio').val()
      };

      // Validaciones básicas
      if (data.servicio_id === "") {
        showNotification("Debe seleccionar un servicio", "error");
        return;
      }
      if (data.servicio_id === "custom" && !data.nombre_custom.trim()) {
        showNotification("Debe ingresar el nombre del servicio personalizado", "error");
        return;
      }

      var btnGuardar = $(this);
      btnGuardar.prop('disabled', true).html('<i class="fas fa-spinner fa-spin mr-1"></i> Guardando...');

      $.ajax({
        url: "/servicios/ajax/agregar_servicio/", // URL endpoint API
        method: "POST",
        data: JSON.stringify(data),
        contentType: "application/json",
        dataType: "json",
        headers: {
          "X-CSRFToken": $('input[name="csrfmiddlewaretoken"]').val() // Obtener CSRF
        },
        success: function(response){
          if(response.status == "ok"){
            $('#modalAgregarServicio').modal('hide'); // Ocultar modal
            actualizarTarjetaOrden(data.order_id); // Actualizar solo la tarjeta afectada
            showNotification("Servicio agregado correctamente");
          } else {
            showNotification("Error: " + response.error, "error");
          }
          btnGuardar.prop('disabled', false).html('<i class="fas fa-save mr-1"></i> Guardar Servicio');
        },
        error: function(xhr, status, error){
          showNotification("Error al agregar el servicio: " + error, "error");
          btnGuardar.prop('disabled', false).html('<i class="fas fa-save mr-1"></i> Guardar Servicio');
        }
      });
    });

    // Inicializar sortable al cargar la página
    initSortable();
  }); // Fin $(document).ready