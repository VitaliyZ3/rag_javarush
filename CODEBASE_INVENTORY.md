# CODEBASE_INVENTORY.md

Огляд поточного стану репозиторію: вихідного коду, `pyproject.toml`, `.env.example`, `.gitignore`, `README.md` і `CLAUDE.md`.

## Стек і технології

- **Python 3.12+**; залежностями керує `uv`, для розробки використовується `pytest`.
- **Streamlit** — вебінтерфейс запитань-відповідей.
- **LangChain integrations**, **ChromaDB** і **Hugging Face Sentence Transformers** — завантаження та розбиття документів, побудова гібридного retriever, збереження векторів та embeddings.
- **BM25** — лексичний пошук, корисний для точних термінів і кодів.
- **Ollama** через `langchain-ollama` — мовна модель для генерації відповіді.
- Значення за замовчуванням: embedding-модель `paraphrase-multilingual-MiniLM-L12-v2`, пристрій `cpu`, LLM `gemma2:2b`, `RETRIEVAL_K=6`, `BM25_WEIGHT=0.4`.
- `pyproject.toml` задає нижні межі версій залежностей; resolved версії зафіксовані в `uv.lock`.

## Модулі та відповідальність

- **`rag_verify/config.py`** — централізована конфігурація шляхів і налаштувань. `PROJECT_ROOT` визначається від розташування модуля; змінні середовища читаються через `python-dotenv`.
- **`rag_verify/ingestion/`** — loader registry, splitter та інкрементальна індексація. Підтримуються PDF, DOCX, XLS/XLSX і Markdown. Pipeline порівнює SHA-256 файлів із маніфестом та додає або видаляє chunk IDs у vector store.
- **`rag_verify/retrieval/`** — Chroma vector store, BM25 із текстів chunk-ів у маніфесті та гібридне об'єднання через LangChain `EnsembleRetriever`.
- **`rag_verify/generation/`** — створення Ollama chat-моделі та prompt template. Prompt просить відповідати українською лише на основі наданого контексту.
- **`rag_verify/pipeline.py`** — спільний query orchestration: пошук, обрізання результатів до K, форматування контексту, виклик LLM і повернення відповіді, джерел та кількості chunk-ів.
- **Публічний контракт:** `RagPipeline` вважається стабільним API для Streamlit UI та майбутніх зовнішніх клієнтів.

## Точки входу

- **Вебзастосунок:** `app.py`; створює `RagPipeline` як Streamlit cached resource, показує поле запитання, відповідь, кількість знайдених фрагментів і джерела.
- **CLI індексації:** `ingest.py`; при запуску як скрипт створює `Settings` і викликає ingestion pipeline.
- **Внутрішній query entry point:** `RagPipeline.ask(question)`. Окремої CLI-команди для запитів немає.
- **Розгортання поза локальним середовищем наразі не передбачене.**

## Корисні команди

| Призначення | Команда |
| --- | --- |
| Встановити runtime і dev залежності | `uv sync --group dev` |
| Запустити UI | `uv run streamlit run app.py` |
| Побудувати або оновити індекс | `uv run python ingest.py` |
| Запустити всі тести | `uv run pytest` |
| Запустити один тест | наразі недоступно — обидва test modules видалені; команду можна відновити, коли додадуться нові тести |

Для запитань через UI має працювати Ollama із завантаженою моделлю, що відповідає `LLM_MODEL` (за замовчуванням `gemma2:2b`).

## Тести й конфіги

- Test modules відсутні: `tests/test_ingestion.py` і `tests/test_generation.py` видалені, у `tests/` залишився лише `__init__.py`. `FakeVectorStore`, що раніше перевіряв diff-логіку без реальної Chroma та embeddings, більше не застосовується.
- Автоматизоване тестове покриття наразі відсутнє.
- Попередній запуск `uv run pytest` (Python 3.12.14) показував **8 passed**, але ці тести видалені; наразі `uv run pytest` нічого не зібере (0 tests).
- Конфігурація завантажується з `.env` через `python-dotenv`; приклад змінних наведено в `.env.example`, значення за замовчуванням — у `rag_verify/config.py`.
- `.gitignore` виключає `.env`, файли користувацьких документів і згенеровані індекси з Git; у відповідних data-каталогах залишаються `.gitkeep`.
- У репозиторії не виявлено окремих build, lint, formatter або type-checker команд.

## Карта залежностей

```text
app.py ───────────────┐
                      ├──> rag_verify.pipeline.RagPipeline
                      │      ├──> retrieval.hybrid ──> retrieval.bm25
                      │      │                     └─> retrieval.vectorstore ─> embeddings
                      │      ├──> generation.model ───> langchain_ollama / Ollama
                      │      └──> generation.template
                      │
ingest.py ────────────┴──> ingestion.pipeline
                             ├──> ingestion.loaders
                             ├──> ingestion.splitter
                             └──> retrieval.vectorstore ─> embeddings
```

- UI залежить від `RagPipeline`, CLI індексації — від `ingest()`.
- Query pipeline будує retriever, LLM та prompt.
- Hybrid retriever поєднує BM25 та vector backend.
- Ingestion використовує loaders, splitter і vectorstore; vectorstore обчислює embeddings через embedding factory.

## Runtime-потоки

### Індексація

1. `ingest.py` створює `Settings` і викликає `ingest()`.
2. Pipeline створює `data/raw/`, відкриває Chroma і splitter (якщо не передані), читає маніфест та перелічує файли верхнього рівня.
3. Для кожного файлу обчислюється SHA-256. Незмінені файли пропускаються; для видалених або змінених файлів видаляються старі chunk IDs. Новий вміст завантажується, ділиться на chunk-и, отримує стабільні IDs і додається до Chroma.
4. Після обходу файлів pipeline записує JSON маніфест і повертає статистику.
5. `data/processed/manifest.json` зберігає file hashes, текст chunk-ів, metadata та IDs; він також є джерелом документів для BM25.

### Запитання-відповідь

1. Streamlit створює cached `RagPipeline`; його constructor готує settings, retriever, LLM і prompt.
2. Retriever створює vector retriever та BM25 із маніфесту. Якщо BM25-корпус порожній, використовується лише vector retriever.
3. `ask()` викликає пошук, обрізає список до `retrieval_k`, форматує контекст і передає його разом із питанням до LLM.
4. UI показує відповідь, кількість chunk-ів і source filenames.

## Зони підвищеного ризику

1. **Маніфест записується неатомарно після змін у Chroma.** Векторний індекс оновлюється під час обходу файлів, а JSON manifest перезаписується пізніше прямим записом. Різке переривання між цими операціями може залишити індекс і маніфест у різних станах; обрив самого запису може пошкодити JSON.
2. **Підтримка розширень чутлива до регістру, індексація нерекурсивна.** Loader registry зіставляє точні lowercase suffix-и, а пошук файлів проходить лише по файлах безпосередньо в `data/raw/`. Наприклад, `.PDF` та файли у піддиректоріях поточним проходом не індексуються.
3. **Файли цілком читаються в пам'ять для хешування та обробки.** Хеш обчислюється через `Path.read_bytes()`, а loaders викликають `load()` для документа; обмежень розміру файлу в конфігурації немає.
4. **Prompt не є механізмом верифікації відповіді.** Він інструктує модель відповідати лише з контексту, але код не перевіряє твердження, цитати або відповідність відповіді джерелам. Результат повертає імена файлів, а не посилання на конкретні сторінки чи chunk-и.
5. **Обробка помилок UI не охоплює стартову ініціалізацію.** `pipeline = get_pipeline()` виконується до обробника `try/except`, який огортає тільки `pipeline.ask()`. Крім того, текст помилки в UI насамперед вказує на Ollama незалежно від фактичного джерела помилки.
6. **Налаштування типізуються, але не перевіряються на діапазони.** `RETRIEVAL_K`, `BM25_WEIGHT`, розмір та overlap chunk-ів читаються з environment без перевірки допустимих меж.
7. **Автоматизоване тестове покриття відсутнє.** Файли `tests/test_ingestion.py` і `tests/test_generation.py` видалені без заміни; `uv run pytest` наразі нічого не перевіряє.

