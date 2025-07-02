/**
 * Frontend расширение для Jupyter AI для автоматической передачи контекста notebook.
 * Это расширение перехватывает сообщения чата и добавляет текущий контекст notebook.
 */

define([
    'base/js/namespace',
    'jquery',
    'base/js/events'
], function(Jupyter, $, events) {
    'use strict';

    /**
     * Получает все ячейки кода из текущего notebook
     */
    function getCurrentNotebookCode() {
        if (!Jupyter.notebook) {
            return '';
        }

        const cells = Jupyter.notebook.get_cells();
        const codeCells = cells
            .filter(cell => cell.cell_type === 'code')
            .map(cell => cell.get_text())
            .filter(text => text.trim() !== '');

        return codeCells.join('\n\n');
    }

    /**
     * Получает код текущей активной ячейки
     */
    function getActiveCell() {
        if (!Jupyter.notebook) {
            return '';
        }

        const cell = Jupyter.notebook.get_selected_cell();
        if (cell && cell.cell_type === 'code') {
            return cell.get_text();
        }

        return '';
    }

    /**
     * Патчит отправку сообщений в Jupyter AI Chat
     */
    function patchJupyterAIChat() {
        // Ждем загрузки Jupyter AI
        const checkInterval = setInterval(function() {
            // Проверяем наличие Jupyter AI chat widget
            const chatWidget = document.querySelector('.jp-ai-chat-panel');
            if (!chatWidget) {
                return;
            }

            clearInterval(checkInterval);

            // Перехватываем отправку сообщений
            const originalSend = window.jupyterAIChat?.sendMessage;
            if (originalSend) {
                window.jupyterAIChat.sendMessage = function(message, options) {
                    // Добавляем контекст notebook к сообщению
                    const enhancedOptions = {
                        ...options,
                        notebook_context: {
                            current_code: getCurrentNotebookCode(),
                            active_cell: getActiveCell(),
                            notebook_path: Jupyter.notebook.notebook_path,
                            notebook_name: Jupyter.notebook.notebook_name
                        }
                    };

                    // Вызываем оригинальную функцию с дополненными опциями
                    return originalSend.call(this, message, enhancedOptions);
                };
            }

            // Альтернативный способ - перехват через события
            events.on('jupyter-ai:send-message', function(evt, data) {
                if (!data.context) {
                    data.context = {};
                }
                
                data.context.notebook = {
                    current_code: getCurrentNotebookCode(),
                    active_cell: getActiveCell(),
                    notebook_path: Jupyter.notebook.notebook_path,
                    notebook_name: Jupyter.notebook.notebook_name
                };
            });

        }, 1000);
    }

    /**
     * Инициализация расширения
     */
    function load_extension() {
        console.log('Loading Jupyter AI Context Extension...');

        // Запускаем патчинг после загрузки notebook
        if (Jupyter.notebook) {
            patchJupyterAIChat();
        } else {
            events.on('notebook_loaded.Notebook', function() {
                patchJupyterAIChat();
            });
        }

        // Добавляем обработчик для обновления контекста при изменении ячеек
        events.on('set_dirty.Notebook', function() {
            // Можно добавить логику для обновления контекста в реальном времени
        });

        console.log('Jupyter AI Context Extension loaded');
    }

    return {
        load_ipython_extension: load_extension,
        load_jupyter_extension: load_extension
    };
});