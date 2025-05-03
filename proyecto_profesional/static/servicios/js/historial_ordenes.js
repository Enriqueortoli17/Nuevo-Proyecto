// proyecto_profesional/static/js/historial_ordenes.js

$(document).ready(function(){
    // Funcionalidad de búsqueda en el historial
    $('#orderSearch').on('input', function() {
        var searchText = $(this).val().toLowerCase();
        var found = false;
        // Buscar dentro de cada .order-item
        $('.order-item').each(function() {
            var orderContent = $(this).text().toLowerCase();
            var match = orderContent.includes(searchText);
            $(this).toggle(match); // Muestra u oculta el item según la coincidencia
            if(match) found = true;
        });
        // Mostrar/ocultar el mensaje de "no resultados"
        // Se muestra si no se encontró nada Y hay items en la lista Y ninguno está visible
        $('#no-results-message').toggle(!found && $('.order-item').length > 0 && $('.order-item:visible').length === 0);
    });
});