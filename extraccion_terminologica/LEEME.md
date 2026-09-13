# Extracción terminológica — versión web (Streamlit)

## Correrla en tu computadora

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -m spacy download es_core_news_sm
streamlit run app.py
```

Se abre sola en el navegador en `http://localhost:8501`.

## Publicarla con una URL (gratis, para compartir con la clase)

**Opción recomendada: Streamlit Community Cloud**
1. Subí estos 3 archivos (`app.py`, `requirements.txt`, este LEEME) a un repositorio de GitHub.
2. Entrá a share.streamlit.io, conectá tu cuenta de GitHub.
3. Elegí el repo y el archivo `app.py`.
4. En segundos te da una URL pública (tipo `tuapp.streamlit.app`) que podés compartir
   con los estudiantes — cada uno la abre desde su navegador, sin instalar nada.

**Nota**: los modelos de spaCy (`en_core_web_sm`, `es_core_news_sm`) hay que agregarlos
al `requirements.txt` como URL directa si el despliegue no corre el comando de descarga
automáticamente. Si da error de modelo no encontrado al desplegar, agregá esta línea al
`requirements.txt`:

```
https://github.com/explosion/spacy-models/releases/download/es_core_news_sm-3.7.0/es_core_news_sm-3.7.0-py3-none-any.whl
```//tar
(y la equivalente en_core_web_sm si usás inglés)

## Qué cambia respecto al notebook de Colab

- Mismo motor y misma lógica (extracción, stopwords personalizadas, conteo total,
  traducción opcional con Claude).
- Acá los estudiantes interactúan con controles (sliders, checkbox, área de texto)
  en vez de editar código Python directamente.
- La API key de Claude se ingresa en un campo de contraseña en la propia interfaz,
  no queda guardada en el código.
