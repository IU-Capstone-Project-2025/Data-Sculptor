# Jupyter AI Adviser с автоматическим контекстом Notebook

Это расширение автоматически передает текущее состояние Jupyter notebook в микросервис Adviser через поле `current_code`.

## Как это работает

1. **Backend патч**: Перехватывает сообщения чата и добавляет контекст notebook
2. **Frontend расширение**: Собирает код из всех ячеек notebook при отправке сообщения
3. **API endpoint**: Предоставляет REST API для получения контекста notebook
4. **Автоматическая передача**: Контекст автоматически добавляется в поле `current_code` при каждом запросе к Adviser

## Установка

1. Создайте правильную структуру директорий:
```bash
llm_custom_providers/
├── __init__.py
├── adviser_llm.py
├── adviser_provider.py
├── adviser_plugin.py
├── chat_handler_patch.py
├── context_handler.py
├── static/
│   └── frontend_extension.js
└── jupyter-config/
    ├── jupyter_notebook_config.d/
    │   └── jupyter_ai_context.json
    └── jupyter_server_config.d/
        └── jupyter_ai_context.json
```

2. Установите пакет:
```bash
pip install -e .
```

3. Включите frontend расширение:
```bash
jupyter nbextension install --py llm_custom_providers --sys-prefix
jupyter nbextension enable --py llm_custom_providers --sys-prefix
```

4. Включите server расширение:
```bash
jupyter server extension enable llm_custom_providers --sys-prefix
```

## Конфигурация

В `jupyterhub_config.py` добавьте:

```python
# Передача URL микросервиса в окружение
c.Spawner.environment.update({
    'ADVISER_API_URL': os.getenv('ADVISER_API_URL', 'http://adviser:9353'),
})

# Включение расширения
c.ServerApp.jpserver_extensions = {
    "llm_custom_providers": True
}
```

## Использование

После установки контекст notebook будет автоматически передаваться в Adviser:

1. Откройте Jupyter notebook
2. Откройте панель Jupyter AI Chat
3. При отправке сообщения весь код из notebook автоматически передается в поле `current_code`

## Отладка

### Проверка работы контекста

1. **Проверка API endpoint**:
```bash
# Получить контекст notebook через API
curl -H "Authorization: token YOUR_TOKEN" \
     "http://localhost:8888/api/ai/context?path=path/to/notebook.ipynb"
```

2. **Логирование в adviser_llm.py**:
```python
# Добавьте логирование для отладки
import logging
logger = logging.getLogger(__name__)

# В методе _call
logger.info(f"Sending request with current_code length: {len(final_request.get('current_code', ''))}")
logger.debug(f"Full request: {final_request}")
```

3. **Проверка в браузере**:
```javascript
// Откройте консоль браузера и выполните:
console.log(getCurrentNotebookCode());
```

### Альтернативный метод через метаданные сообщения

Если автоматический перехват не работает, можно использовать альтернативный подход через метаданные:

```python
# В chat_handler_patch.py добавьте:
from jupyter_ai.models import ChatMessage
import json

async def process_message_with_context(self, message: HumanChatMessage):
    """Обработка сообщения с добавлением контекста notebook."""
    
    # Проверяем, есть ли метаданные с путем к notebook
    metadata = message.metadata or {}
    notebook_path = metadata.get('notebook_path')
    
    if notebook_path and hasattr(self, 'contents_manager'):
        try:
            # Получаем содержимое notebook
            notebook = await self.contents_manager.get(notebook_path, content=True)
            if notebook['type'] == 'notebook':
                # Извлекаем код
                from .context_handler import NotebookContextExtractor
                extractor = NotebookContextExtractor()
                current_code = extractor.extract_notebook_cells(notebook['content'])
                
                # Добавляем в kwargs для LLM
                if hasattr(self, 'llm'):
                    if not hasattr(self.llm, '_current_context'):
                        self.llm._current_context = {}
                    self.llm._current_context['current_code'] = current_code
                    
        except Exception as e:
            self.log.error(f"Failed to extract notebook context: {e}")
    
    # Вызываем оригинальный обработчик
    return await original_process_message(message)
```

## Расширенная конфигурация

### Настройка размера контекста

Можно ограничить размер передаваемого контекста:

```python
# В context_handler.py
class NotebookContextExtractor:
    MAX_CONTEXT_LENGTH = 10000  # Максимум символов
    MAX_CELLS = 50  # Максимум ячеек
    
    @staticmethod
    def extract_notebook_cells(notebook_data: Dict[str, Any], 
                             max_length: int = None,
                             max_cells: int = None) -> str:
        """Извлекает ячейки с ограничениями."""
        max_length = max_length or NotebookContextExtractor.MAX_CONTEXT_LENGTH
        max_cells = max_cells or NotebookContextExtractor.MAX_CELLS
        
        # ... остальная логика с учетом ограничений
```

### Фильтрация контекста

Можно добавить фильтрацию для исключения определенных ячеек:

```python
# В context_handler.py
@staticmethod
def should_include_cell(cell: Dict[str, Any]) -> bool:
    """Определяет, нужно ли включать ячейку в контекст."""
    # Пропускаем ячейки с определенными тегами
    tags = cell.get('metadata', {}).get('tags', [])
    if 'skip-context' in tags:
        return False
    
    # Пропускаем пустые ячейки
    source = cell.get('source', '')
    if isinstance(source, list):
        source = ''.join(source)
    if not source.strip():
        return False
    
    return True
```

## Интеграция с Docker

Обновите `docker-compose.yml`:

```yaml
services:
  jupyterhub:
    environment:
      - ADVISER_API_URL=http://adviser:9353
    volumes:
      - ./llm_custom_providers:/opt/conda/lib/python3.11/site-packages/llm_custom_providers
```

## Известные проблемы и решения

1. **Контекст не передается**: Проверьте, что расширение правильно установлено и включено
2. **Большие notebook**: Используйте ограничения размера контекста
3. **Производительность**: Кешируйте контекст между запросами, если notebook не изменялся

## Дополнительные возможности

### Передача дополнительной информации

Помимо кода, можно передавать:
- Вывод ячеек
- Метаданные notebook
- История выполнения
- Переменные из namespace

### Пример расширенного контекста:

```python
context = {
    "current_code": all_code,
    "active_cell": active_cell_code,
    "cell_outputs": cell_outputs,
    "notebook_metadata": notebook.get('metadata', {}),
    "kernel_info": kernel_info
}
```