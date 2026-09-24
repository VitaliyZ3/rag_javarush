from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.prompts import PromptTemplate


_TEMPLATE = """Ти експерт з реєстрації транспортних засобів України (РТЗ).
Відповідай ТІЛЬКИ на основі наданого контексту.
Якщо інформації немає в контексті — скажи "Не знайдено в документах".
Відповідай українською мовою. Будь точним і лаконічним.

КОНТЕКСТ З ДОКУМЕНТІВ:
{context}

ПИТАННЯ:
{question}

ВІДПОВІДЬ:"""


def build_prompt() -> PromptTemplate:
    from langchain_core.prompts import PromptTemplate

    return PromptTemplate(input_variables=["context", "question"], template=_TEMPLATE)
