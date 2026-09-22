import streamlit as st

from rag_verify.pipeline import RagPipeline

st.set_page_config(page_title="RAG — Нормативна база РТЗ", page_icon="📋", layout="wide")


@st.cache_resource(show_spinner="Завантажую модель...")
def get_pipeline() -> RagPipeline:
    return RagPipeline()


pipeline = get_pipeline()

st.title("📋 RAG — Нормативна база РТЗ")
st.caption("Гібридний пошук (BM25 + вектори) по нормативних документах")

with st.sidebar:
    st.header("⚙️ Інформація")
    st.info("📁 Документи: data/raw/")
    st.info(f"🤖 Модель: {pipeline.settings.llm_model}")
    st.warning("Для оновлення бази: python ingest.py (індексує лише нове/змінене)")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🔍 Задай питання")
    question = st.text_area(
        "Питання:",
        value=st.session_state.get("question", ""),
        placeholder="Наприклад: Які поля обов'язкові в операції 02302?",
        height=100,
    )

    if st.button("🚀 Знайти відповідь", type="primary"):
        if question.strip():
            try:
                with st.spinner("⏳ Шукаю відповідь..."):
                    result = pipeline.ask(question)
            except Exception as exc:
                st.error(
                    "Не вдалося отримати відповідь. Перевір, що Ollama запущена "
                    f"(`ollama serve`) і модель `{pipeline.settings.llm_model}` завантажена.\n\n"
                    f"Деталі: {exc}"
                )
            else:
                st.subheader("📝 Відповідь")
                st.markdown(result["answer"])
                st.divider()
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("🔎 Знайдено шматків", result["chunks_found"])
                with col_b:
                    st.info(f"📄 Джерела: {', '.join(result['sources']) or 'немає'}")
        else:
            st.warning("Введи питання")

with col2:
    st.subheader("💡 Приклади питань")
    examples = [
        "Які поля обов'язкові в операції 02302?",
        "Яка правова підстава операції 02302?",
        "Які поля змінюються в реєстрі після переобладнання?",
        "Що таке vehicleState?",
        "Які документи-підстави потрібні?",
    ]
    for example in examples:
        if st.button(example, key=example):
            st.session_state["question"] = example
            st.rerun()
