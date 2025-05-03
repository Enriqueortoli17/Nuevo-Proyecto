// proyecto_profesional/static/js/config_clientes.js

$(document).ready(function(){
    // Funcionalidad del buscador de clientes
    $("#buscarCliente").on("keyup", function() {
        var value = $(this).val().toLowerCase().trim(); // Añadido trim()
        var found = false; // Variable para rastrear si se encontró algo
        // Filtrar las filas de clientes
        $(".client-row").filter(function() {
            var rowText = $(this).text().toLowerCase().trim(); // Añadido trim()
            var match = rowText.includes(value);
            $(this).toggle(match);
            if (match) found = true;
        });

        // Gestionar mensaje de "no resultados"
        var noResultsRow = $("#no-results-message");
        if (!found && value !== "") {
            if (noResultsRow.length === 0) {
                // Crear y añadir fila si no existe
                $("table tbody").append( // Asegúrate que tu tabla tenga tbody
                    '<tr id="no-results-message"><td colspan="4" class="text-center py-3">' + // Ajusta colspan si es necesario
                    '<i class="fas fa-search fa-2x mb-2 text-muted"></i><br>' +
                    'No se encontraron resultados para "' + value + '"</td></tr>'
                );
            } else {
                // Actualizar y mostrar fila existente
                noResultsRow.find("td").html(
                    '<i class="fas fa-search fa-2x mb-2 text-muted"></i><br>' +
                    'No se encontraron resultados para "' + value + '"'
                );
                noResultsRow.show();
            }
        } else {
            // Ocultar o eliminar fila si hay resultados o el campo está vacío
            noResultsRow.remove();
        }
    });

    // Código para mostrar notificaciones de Django (requiere notifications.js cargado globalmente)
    // ESTA PARTE NO DEBE TENER TAGS DE DJANGO AQUI
    // Si necesitas mostrar mensajes que vienen del backend,
    // la función showNotification debería leerlos de algún lugar
    // (ej. atributos data-* en el HTML) o ser llamada desde el HTML.
    // Por ahora, dejamos el espacio por si necesitas añadir lógica JS pura
    // para notificaciones en esta página.

    // Ejemplo de cómo podrías leer un mensaje desde el HTML (si lo añades ahí)
    /*
    var backendMessages = $('#backend-messages'); // Suponiendo un div con este ID
    if (backendMessages.length > 0 && typeof showNotification === 'function') {
         backendMessages.find('.message-item').each(function() {
             var message = $(this).data('message');
             var tags = $(this).data('tags');
             showNotification(message, tags);
         });
    }
    */

    // Cargar theme.js si es necesario y no está en base.html
    // $.getScript("{% static 'js/theme.js' %}");

}); // Fin $(document).ready