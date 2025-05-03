function sincronizarOrdenes() {
    var ordenesCapturadas = JSON.parse(localStorage.getItem("ordenesOffline")) || [];
    if (ordenesCapturadas.length === 0) {
        alert("No hay órdenes para sincronizar.");
        return;
    }
    
    $.ajax({
        url: "/servicios/sincronizar_ordenes/",
        method: "POST",
        data: JSON.stringify({ ordenes: ordenesCapturadas }),
        contentType: "application/json",
        dataType: "json",
        headers: { "X-CSRFToken": csrfToken },  // Asegúrate de definir csrfToken o utilizar la variable del template
        success: function(response) {
            if (response.status === "ok") {
                alert("Sincronización exitosa.");
                localStorage.removeItem("ordenesOffline");
            } else {
                alert("Error en la sincronización: " + response.error);
            }
        },
        error: function(xhr, status, error) {
            alert("Error al sincronizar: " + error);
        }
    });
}
