_TEMPLATE = """Ти експерт з реєстрації транспортних засобів України (РТЗ).
Відповідай ТІЛЬКИ на основі наданого контексту.
Якщо інформації немає в контексті — скажи "Не знайдено в документах".
Відповідай українською мовою. Будь точним і лаконічним.

КОНТЕКСТ З ДОКУМЕНТІВ:
{context}

ПИТАННЯ:
{question}

ВІДПОВІДЬ:"""


def build_prompt():
    from langchain_core.prompts import PromptTemplate

    return PromptTemplate(input_variables=["context", "question"], template=_TEMPLATE)
