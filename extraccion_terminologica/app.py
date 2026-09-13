import io
import re
from collections import Counter, defaultdict

import pandas as pd
import spacy
import streamlit as st

st.set_page_config(page_title="Extracción terminológica", layout="wide")

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

@st.cache_resource
def cargar_modelo(idioma: str):
    modelo = "en_core_web_sm" if idioma == "en" else "es_core_news_sm"
    return spacy.load(modelo)


def extraer_texto(archivo) -> str:
    nombre = archivo.name.lower()
    if nombre.endswith(".pdf"):
        import pdfplumber

        texto = ""
        with pdfplumber.open(archivo) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texto += t + "\n"
        return texto
    elif nombre.endswith(".docx"):
        import docx

        d = docx.Document(archivo)
        return "\n".join(p.text for p in d.paragraphs)
    elif nombre.endswith(".txt"):
        return archivo.read().decode("utf-8", errors="ignore")
    else:
        raise ValueError("Formato no soportado. Usá .pdf, .docx o .txt")


def contar_todas_las_palabras(texto: str) -> tuple[int, int, pd.DataFrame]:
    palabras = re.findall(r"\b[a-zA-ZÀ-ÿñÑ]+\b", texto.lower())
    total = len(palabras)
    unicas = len(set(palabras))
    frecuencia = Counter(palabras)
    df = pd.DataFrame(frecuencia.most_common(), columns=["Palabra", "Frecuencia"])
    return total, unicas, df


def extraer_candidatos(
    nlp,
    texto: str,
    min_frecuencia: int,
    max_palabras_termino: int,
    stopwords_personalizadas: set[str],
    excluir_si_contiene: bool,
) -> pd.DataFrame:
    doc = nlp(texto[:1_000_000])  # límite de longitud de spaCy

    def es_candidato_valido(chunk) -> bool:
        texto_chunk = chunk.text.strip()
        clave = texto_chunk.lower()
        if len(texto_chunk) < 3:
            return False
        if chunk.root.pos_ not in ("NOUN", "PROPN"):
            return False
        if len(texto_chunk.split()) > max_palabras_termino:
            return False
        if all(tok.is_stop for tok in chunk):
            return False
        if clave in stopwords_personalizadas:
            return False
        if excluir_si_contiene and any(
            palabra in stopwords_personalizadas for palabra in clave.split()
        ):
            return False
        return True

    frecuencia = defaultdict(int)
    contexto = {}
    pos_tag = {}

    for chunk in doc.noun_chunks:
        if es_candidato_valido(chunk):
            clave = chunk.text.strip().lower()
            frecuencia[clave] += 1
            if clave not in contexto:
                contexto[clave] = chunk.sent.text.strip().replace("\n", " ")[:200]
                pos_tag[clave] = chunk.root.pos_

    filas = [
        {
            "Termino": termino,
            "Frecuencia": freq,
            "Categoria": pos_tag[termino],
            "Contexto": contexto[termino],
        }
        for termino, freq in frecuencia.items()
        if freq >= min_frecuencia
    ]

    return pd.DataFrame(filas).sort_values("Frecuencia", ascending=False).reset_index(drop=True)


def df_a_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


# ---------------------------------------------------------------------------
# Interfaz
# ---------------------------------------------------------------------------

st.title("Extracción y gestión terminológica asistida")
st.caption(
    "Módulo didáctico — versión simplificada de lo que hacen Sketch Engine / "
    "TermSuite, pensada para mostrar el mecanismo por dentro en clase."
)

with st.sidebar:
    st.header("Configuración")
    idioma = st.selectbox("Idioma del documento fuente", ["en", "es"], index=0)
    st.divider()
    st.subheader("Filtro de candidatos")
    min_frecuencia = st.slider("Frecuencia mínima", 1, 10, 2)
    max_palabras_termino = st.slider("Máx. palabras por término", 1, 8, 4)
    stopwords_texto = st.text_area(
        "Stopwords personalizadas (una por línea)",
        value="parte\nsistema\nmanera\ntipo\ncaso\nforma\nfigura\ntabla\npágina\ncapítulo\nsección",
        height=180,
    )
    excluir_si_contiene = st.checkbox(
        "Excluir también sintagmas que CONTIENEN una stopword personalizada",
        value=False,
        help='Ej.: si activás esto y "tipo" está en la lista, se descarta también "tipo de acero".',
    )

archivo = st.file_uploader("Subí un documento (.pdf, .docx o .txt)", type=["pdf", "docx", "txt"])

if archivo is not None:
    with st.spinner("Extrayendo texto..."):
        texto_documento = extraer_texto(archivo)

    st.success(f"Documento cargado: {archivo.name} ({len(texto_documento):,} caracteres)")

    with st.expander("Ver muestra del texto extraído"):
        st.text(texto_documento[:1000])

    tab1, tab2, tab3 = st.tabs(
        ["1. Conteo total de palabras", "2. Candidatos terminológicos", "3. Traducción (Claude, opcional)"]
    )

    # --- Tab 1: conteo total ---
    with tab1:
        total, unicas, df_frecuencia_total = contar_todas_las_palabras(texto_documento)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de palabras (con repeticiones)", f"{total:,}")
        c2.metric("Palabras únicas (vocabulario)", f"{unicas:,}")
        c3.metric("Promedio de repeticiones", f"{total / unicas:.2f}" if unicas else "—")
        st.dataframe(df_frecuencia_total.head(50), use_container_width=True)
        st.caption("Conteo en bruto, sin filtrar stopwords ni categoría gramatical.")

    # --- Tab 2: candidatos terminológicos ---
    with tab2:
        if st.button("Extraer candidatos terminológicos", type="primary"):
            with st.spinner("Cargando modelo de lenguaje y analizando el documento..."):
                nlp = cargar_modelo(idioma)
                stopwords_personalizadas = {
                    s.strip().lower() for s in stopwords_texto.splitlines() if s.strip()
                }
                df_terminos = extraer_candidatos(
                    nlp,
                    texto_documento,
                    min_frecuencia,
                    max_palabras_termino,
                    stopwords_personalizadas,
                    excluir_si_contiene,
                )
                st.session_state["df_terminos"] = df_terminos

        if "df_terminos" in st.session_state:
            df_terminos = st.session_state["df_terminos"]
            st.write(f"**{len(df_terminos)} candidatos encontrados.**")
            st.dataframe(df_terminos, use_container_width=True)

            idioma_col = "EN-US" if idioma == "en" else "ES-ES"
            df_export = pd.DataFrame(
                {
                    idioma_col: df_terminos["Termino"],
                    "Traduccion": "",
                    "Definicion": "",
                    "Dominio": "",
                    "Frecuencia": df_terminos["Frecuencia"],
                    "Contexto_fuente": df_terminos["Contexto"],
                }
            )
            st.download_button(
                "Descargar glosario_candidatos.csv (formato memoQ/MultiTerm)",
                data=df_a_csv_bytes(df_export),
                file_name="glosario_candidatos.csv",
                mime="text/csv",
            )
        else:
            st.info("Configurá los filtros en la barra lateral y presioná el botón para extraer candidatos.")

    # --- Tab 3: traducción con Claude (opcional) ---
    with tab3:
        st.warning(
            "No ingreses datos sensibles o confidenciales del cliente sin anonimizar antes."
        )
        if "df_terminos" not in st.session_state:
            st.info("Primero extraé candidatos en la pestaña anterior.")
        else:
            api_key = st.text_input("API key de Anthropic", type="password")
            dominio = st.text_input("Dominio del proyecto", value="ingeniería mecánica")
            top_n = st.slider("Cantidad de términos a traducir (los más frecuentes)", 5, 50, 20)

            if st.button("Proponer traducciones con Claude"):
                if not api_key:
                    st.error("Ingresá una API key válida.")
                else:
                    import anthropic

                    client = anthropic.Anthropic(api_key=api_key)
                    df_terminos = st.session_state["df_terminos"]
                    terminos_top = df_terminos.head(top_n)["Termino"].tolist()
                    lista_terminos = "\n".join(f"- {t}" for t in terminos_top)

                    prompt = f"""Sos un terminólogo especializado en traducción técnica.
Dominio del proyecto: {dominio}.

Para cada término de la lista, proponé la traducción al español más usada
en normativa y bibliografía técnica del dominio indicado.
Si el término es ambiguo o tiene más de una traducción posible según contexto,
indicalo brevemente y aclará cuál es la más frecuente.

Devolvé SOLO una tabla en formato CSV con columnas:
Termino,Traduccion,Ambiguo(si/no),Nota

Lista de términos:
{lista_terminos}
"""
                    with st.spinner("Consultando a Claude..."):
                        response = client.messages.create(
                            model="claude-sonnet-4-6",
                            max_tokens=2000,
                            messages=[{"role": "user", "content": prompt}],
                        )
                        resultado = response.content[0].text

                    try:
                        df_traducido = pd.read_csv(io.StringIO(resultado))
                        st.session_state["df_traducido"] = df_traducido
                    except Exception:
                        st.error("No se pudo interpretar la respuesta como CSV. Respuesta cruda:")
                        st.text(resultado)

            if "df_traducido" in st.session_state:
                st.dataframe(st.session_state["df_traducido"], use_container_width=True)
                st.download_button(
                    "Descargar glosario_con_traduccion.csv",
                    data=df_a_csv_bytes(st.session_state["df_traducido"]),
                    file_name="glosario_con_traduccion.csv",
                    mime="text/csv",
                )
else:
    st.info("Subí un documento para empezar.")
