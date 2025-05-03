// proyecto_profesional/static/js/config_modelos.js (VERSIÓN FINAL - SIN TAGS DJANGO)

$(document).ready(function(){
    // console.log("config_modelos.js cargado y document ready!"); // Log opcional

    // --- Buscador de motores ---
    $("#buscarMotor").on("keyup", function() {
        var value = $(this).val().toLowerCase().trim();
        var found = false;
        var $tableBody = $("#tablaMotores tbody");
        var $rows = $tableBody.find(".motor-row");

        $("#no-results-message").remove(); // Limpiar mensaje previo

        $rows.each(function() {
            var $row = $(this);
            var motorNameCell = $row.find('td:first'); // Buscar en la primera celda
            var rowText = motorNameCell.text().toLowerCase().trim();
            var match = rowText.includes(value);
            $row.toggle(match);
            if (match) {
                found = true;
            }
        });

        if (!found && value !== "") {
            $tableBody.append(
                '<tr id="no-results-message"><td colspan="2" class="text-center py-3">' +
                '<i class="fas fa-search fa-2x mb-2 text-muted"></i><br>' +
                'No se encontraron resultados para "' + value + '"</td></tr>'
            );
        }
    });
    // --- Fin Buscador ---


    // --- Código para Modales (Restaurado del original) ---
    $('.modal').on('hidden.bs.modal', function (e) {
        if ($('.modal:visible').length) {
             $('body').addClass('modal-open');
         } else {
             $('.modal-backdrop').remove();
             $('body').removeClass('modal-open').css('padding-right', '');
         }
    });
    $(document).on('show.bs.modal', '.modal', function (e) {
        var zIndex = 1040 + (10 * $('.modal:visible').length);
        $(this).css('z-index', zIndex);
        setTimeout(function() {
            $('.modal-backdrop').not('.modal-stack').css('z-index', zIndex - 1).addClass('modal-stack');
        }, 0);
    });
    // --- Fin Código Modales ---

    // NOTA: El código para mostrar mensajes de Django con {% if messages %}
    // NO PUEDE estar aquí. Debe estar en el HTML o manejarse de otra forma
    // si se necesitan notificaciones generadas por JS puro.
    // La función showNotification() sí puede estar aquí si la defines,
    // o mejor aún, en un archivo JS global como notifications.js

}); // Fin $(document).ready