"""
Обработчик контекста для передачи состояния notebook в Adviser.
Этот модуль расширяет функциональность Jupyter AI для автоматического
сбора и передачи контекста notebook.
"""

from typing import Dict, Any, Optional, List
from jupyter_server.base.handlers import APIHandler
from jupyter_server.utils import ensure_async
import json
import tornado
from notebook.services.contents.manager import ContentsManager


class NotebookContextExtractor:
    """Извлекает контекст из текущего notebook."""
    
    @staticmethod
    def extract_notebook_cells(notebook_data: Dict[str, Any]) -> str:
        """
        Извлекает все ячейки кода из notebook.
        
        Args:
            notebook_data: Данные notebook в формате JSON
            
        Returns:
            Строка с объединенным кодом всех ячеек
        """
        if not notebook_data or 'cells' not in notebook_data:
            return ""
        
        code_cells = []
        for cell in notebook_data.get('cells', []):
            if cell.get('cell_type') == 'code':
                source = cell.get('source', '')
                if isinstance(source, list):
                    source = ''.join(source)
                if source.strip():
                    code_cells.append(source)
        
        return '\n\n'.join(code_cells)
    
    @staticmethod
    def get_active_cell(notebook_data: Dict[str, Any], cell_index: Optional[int] = None) -> str:
        """
        Получает код активной ячейки.
        
        Args:
            notebook_data: Данные notebook
            cell_index: Индекс активной ячейки (если известен)
            
        Returns:
            Код активной ячейки
        """
        if not notebook_data or 'cells' not in notebook_data:
            return ""
        
        cells = notebook_data.get('cells', [])
        
        # Если индекс не указан, берем последнюю ячейку кода
        if cell_index is None:
            for cell in reversed(cells):
                if cell.get('cell_type') == 'code':
                    source = cell.get('source', '')
                    if isinstance(source, list):
                        source = ''.join(source)
                    return source
            return ""
        
        # Если индекс указан, берем конкретную ячейку
        if 0 <= cell_index < len(cells):
            cell = cells[cell_index]
            if cell.get('cell_type') == 'code':
                source = cell.get('source', '')
                if isinstance(source, list):
                    source = ''.join(source)
                return source
        
        return ""


class JupyterAIContextHandler(APIHandler):
    """
    HTTP обработчик для получения контекста notebook через API.
    Может быть использован для отладки и тестирования.
    """
    
    @tornado.web.authenticated
    async def get(self):
        """GET /api/ai/context - получить текущий контекст notebook."""
        notebook_path = self.get_query_argument('path', default='')
        
        if not notebook_path:
            self.set_status(400)
            self.finish(json.dumps({'error': 'No notebook path provided'}))
            return
        
        try:
            # Получаем содержимое notebook
            cm = self.contents_manager
            notebook = await ensure_async(cm.get(notebook_path, content=True))
            
            if notebook['type'] != 'notebook':
                self.set_status(400)
                self.finish(json.dumps({'error': 'Path does not point to a notebook'}))
                return
            
            # Извлекаем контекст
            extractor = NotebookContextExtractor()
            current_code = extractor.extract_notebook_cells(notebook['content'])
            
            context = {
                'current_code': current_code,
                'notebook_path': notebook_path,
                'notebook_name': notebook['name']
            }
            
            self.finish(json.dumps(context))
            
        except Exception as e:
            self.set_status(500)
            self.finish(json.dumps({'error': str(e)}))


def setup_handlers(web_app):
    """Регистрирует обработчики в Jupyter Server."""
    host_pattern = ".*$"
    base_url = web_app.settings["base_url"]
    
    handlers = [
        (f"{base_url}api/ai/context", JupyterAIContextHandler)
    ]
    
    web_app.add_handlers(host_pattern, handlers)