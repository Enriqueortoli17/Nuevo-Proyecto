// proyecto_profesional/static/js/ordenes_terminadas.js

$(document).ready(function(){
    var orderIdParaEntregar = null;

    // Función para mostrar notificaciones (puede ser global o definida aquí)
    function showNotification(message, type = "success") {
      // Crear el elemento de notificación (igual que antes)
      var notification = $('<div class="alert alert-' + type + ' alert-dismissible fade show position-fixed" style="top: 70px; right: 10px; z-index: 9999;">' +
          '<i class="fas fa-' + (type === "success" ? "check-circle" : "exclamation-circle") + ' mr-2"></i>' + message +
          '<button type="button" class="close" data-dismiss="alert" aria-label="Close">' +
          '<span aria-hidden="true">&times;</span>' +
          '</button></div>');
      $("body").append(notification);
      // Desaparecer automáticamente
      setTimeout(function() {
        notification.alert('close');
      }, 3000);
    }

    // Al hacer clic en el botón "Entregada", abre el modal de confirmación
    // Usamos delegación de eventos por si las órdenes se actualizan dinámicamente
    $(document).on('click', '.btn-entregada', function(){
      orderIdParaEntregar = $(this).data('order-id');
      $('#modalEntregada').modal('show');
    });

    // Al confirmar en el modal, enviar AJAX para marcar la orden como entregada
    $('#btnConfirmEntregada').click(function(){
      if(orderIdParaEntregar){
        var button = $(this); // Guardar referencia al botón
        button.prop('disabled', true).html('<i class="fas fa-spinner fa-spin mr-2"></i> Confirmando...'); // Deshabilitar y mostrar spinner

        $.ajax({
          url: "/servicios/marcar_entregada/", // URL del endpoint (asegúrate que sea correcta)
          method: "POST",
          data: JSON.stringify({ order_id: orderIdParaEntregar }),
          contentType: "application/json",
          dataType: "json",
          // Asegúrate de que el token CSRF esté disponible globalmente o pásalo de otra forma
          headers: { "X-CSRFToken": $('input[name="csrfmiddlewaretoken"]').val() },
          success: function(response){
            if(response.status === "ok"){
              // Animación de desvanecimiento antes de eliminar
              $("#order-card-" + orderIdParaEntregar).fadeOut(300, function() {
                $(this).remove();
                // Si no quedan órdenes, mostrar mensaje (puedes crear un div para este mensaje)
                if ($('.order-item').length === 0) {
                  $('.order-list').html('<div class="no-orders"><i class="fas fa-clipboard-check"></i><h4>No hay órdenes terminadas</h4><p class="text-muted">No se encontraron órdenes listas para entrega</p></div>');
                }
              });
              $('#modalEntregada').modal('hide');
              showNotification("Orden marcada como entregada correctamente");
            } else {
              showNotification("Error: " + (response.message || response.error || "Error desconocido"), "danger");
            }
          },
          error: function(xhr, status, error){
            showNotification("Error al marcar como entregada: " + error, "danger");
          },
          complete: function() {
             // Volver a habilitar el botón
             button.prop('disabled', false).html('<i class="fas fa-check mr-2"></i> Confirmar');
             orderIdParaEntregar = null; // Resetear ID
          }
        });
      }
    });

    // Conexión WebSocket para notificaciones en tiempo real
    // (Solo si esta página necesita actualizarse cuando otra orden termina)
    var ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
    var socket_ordenes = new WebSocket(ws_scheme + '://' + window.location.host + '/ws/ordenes/');

    socket_ordenes.onmessage = function(e) {
      var data = JSON.parse(e.data);
      // Si el mensaje indica que una orden ha terminado Y NO está ya en la página, recargar.
      if (data.type === "orden_terminada") {
          // Podrías hacer una llamada AJAX para cargar solo la nueva tarjeta
          // o simplemente recargar la página para mantenerlo simple.
          console.log("Nueva orden terminada detectada, recargando...");
          location.reload();
      }
    };

    socket_ordenes.onclose = function(e) {
      console.error("La conexión WebSocket de órdenes se cerró inesperadamente. Intentando reconectar...");
       // Lógica de reconexión (opcional pero recomendada)
       setTimeout(function() {
         socket_ordenes = new WebSocket(ws_scheme + '://' + window.location.host + '/ws/ordenes/');
       }, 5000);
    };
    socket_ordenes.onerror = function(err) {
       console.error('Error en socket de órdenes:', err);
    };

    // Cambio de tema (claro/oscuro)
    const toggleSwitch = document.querySelector('#checkbox'); // ID del switch
    const currentTheme = localStorage.getItem('theme');

    if (currentTheme) {
        document.documentElement.setAttribute('data-theme', currentTheme);
        if (currentTheme === 'dark' && toggleSwitch) {
            toggleSwitch.checked = true;
        }
    }

    function switchTheme(e) {
        if (e.target.checked) {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
        }
    }

    if (toggleSwitch) {
       toggleSwitch.addEventListener('change', switchTheme);
    }

  }); // Fin $(document).ready