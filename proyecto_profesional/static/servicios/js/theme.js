/**
 * Theme.js - Manejo del cambio de tema claro/oscuro
 */

(function() {
    'use strict';
    
    // Elementos DOM
    const toggleSwitch = document.querySelector('#theme-checkbox');
    
    // Verificar si hay una preferencia guardada
    const currentTheme = localStorage.getItem('theme') ? localStorage.getItem('theme') : null;

    /**
     * Inicializa el tema basado en preferencias guardadas
     */
    function initTheme() {
        if (currentTheme) {
            document.documentElement.setAttribute('data-theme', currentTheme);
            
            if (currentTheme === 'dark') {
                toggleSwitch.checked = true;
            }
        }
    }
    
    /**
     * Cambia el tema y guarda la preferencia
     * @param {Event} e - Evento de cambio
     */
    function switchTheme(e) {
        if (e.target.checked) {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
        }
    }
    
    /**
     * Detecta preferencia del sistema operativo para tema oscuro/claro
     * y lo aplica si no hay preferencia guardada
     */
    function detectSystemPreference() {
        if (currentTheme === null) {
            const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
            
            if (prefersDarkScheme.matches) {
                document.documentElement.setAttribute('data-theme', 'dark');
                toggleSwitch.checked = true;
                localStorage.setItem('theme', 'dark');
            }
        }
    }
    
    // Inicializar
    document.addEventListener('DOMContentLoaded', function() {
        initTheme();
        detectSystemPreference();
        
        // Agregar listener para el switch
        if (toggleSwitch) {
            toggleSwitch.addEventListener('change', switchTheme);
        }
    });
})();