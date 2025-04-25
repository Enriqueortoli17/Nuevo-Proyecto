// proyecto_profesional/static/js/editar_orden.js

$(document).ready(function(){
    // Función para mostrar notificaciones (podría ser global)
    function showNotification(message) {
        var notification = $('<div class="alert alert-success alert-dismissible fade show position-fixed" style="top: 70px; right: 10px; z-index: 9999;">' +
            '<i class="fas fa-check-circle mr-2"></i>' + message +
            '<button type="button" class="close" data-dismiss="alert" aria-label="Close">' +
            '<span aria-hidden="true">&times;</span>' +
            '</button></div>');
        $("body").append(notification);
        setTimeout(function() {
            notification.alert('close');
        }, 3000);
    }

    // Funciones opcionales para guardar datos en los modales
    $("#guardarInventario").click(function(){
        console.log("Inventario guardado (simulado).");
        // Aquí iría la lógica real si guardaras con AJAX desde el modal
        showNotification("Selección de inventario actualizada.");
    });

    $("#guardarServicios").click(function(){
        console.log("Servicios guardados (simulado).");
        // Aquí iría la lógica real si guardaras con AJAX desde el modal
        showNotification("Selección de servicios actualizada.");
    });

    // Mostrar el nombre del archivo seleccionado en el input file
    $(".custom-file-input").on("change", function() {
        var fileName = $(this).val().split("\\").pop();
        $(this).siblings(".custom-file-label").addClass("selected").html(fileName || "Seleccionar archivo");
    });

    // Cambio de tema (claro/oscuro) - (Podría ir en un JS global)
    const toggleSwitch = document.querySelector('#checkbox'); // Asegúrate que el ID sea correcto
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

    // Cargar Sincronizacion.js si es necesario aquí o en base.html
    // (Asegúrate de que sincronizacion.js se cargue solo una vez)
    // $.getScript("{% static 'js/sincronizacion.js' %}"); // Cuidado con cargar scripts duplicados

}); // Fin $(document).ready