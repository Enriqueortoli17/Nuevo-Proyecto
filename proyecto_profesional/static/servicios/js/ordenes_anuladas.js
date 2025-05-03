// proyecto_profesional/static/js/ordenes_anuladas.js

$(document).ready(function(){
    // Funcionalidad de búsqueda
    $('#orderSearch').on('input', function() {
        var searchText = $(this).val().toLowerCase();
        var found = false;
        // Asegúrate que el selector '.order-card' coincida con tu HTML
        $('.order-card').each(function() {
            var orderContent = $(this).text().toLowerCase();
            var match = orderContent.includes(searchText);
            $(this).toggle(match);
             if(match) found = true;
        });
        // Mostrar/ocultar mensaje de "no resultados"
         $('#no-results-message').toggle(!found && $('.order-card').length > 0 && $('.order-card:visible').length === 0);
    });
});