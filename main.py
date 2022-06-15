#-----------------------------------------------------------------------------------
#Proceso de creación de la página web para búsqueda Léxica y Semántica con streamlit
#-----------------------------------------------------------------------------------
from sentence_transformers import SentenceTransformer, util
from elasticsearch import Elasticsearch, helpers
import streamlit as st
import pandas as pd
import spacy
import re
from PIL import Image

#Declara diccionario
nlp = spacy.load("es_core_news_sm")
#añadimos stop words
nlp.Defaults.stop_words |= {"él","película","historia"}

#Conexión a Elasticsearch
es = Elasticsearch(['localhost:9200'],http_auth=('elastic', 'ruben2022'))
model = SentenceTransformer('multi-qa-distilbert-dot-v1')

#Declara funcion para normalizar texto
def normaliza(texto):
    #separamos después de ciertos signos de puntuación
    texto = re.sub(r"([\.\?])", r"\1 ", texto)
    doc = nlp(texto)
    # quitamos puntuación/espacios y stopwords
    tokens = [t for t in doc if not t.is_punct and not t.is_stop and not t.is_space and len(t.text)>1]
    palabras = []
    for t in tokens:
        palabras.append(t.lemma_.lower())
    # juntamos de nuevo en una cadena
    salida = ' '.join(palabras)
    return salida

#Declara funcion principal
def run():
    st.title('Búsqueda semántica de peliculas')
    image = Image.open('Imagen.PNG')
    st.image(image, use_column_width='auto', caption='')    
    
    ranker = st.sidebar.radio('Opciones:', ["Léxica", "Semántica"], index=0)
    st.text('')
    input_text = []
    comment = st.text_input('Ingrese texto de pelicula a buscar !')
    input_text.append(comment)
    
    df_result = pd.DataFrame()
    df_result['Titulo'] = ''
    df_result['Descripcion'] = ''
    df_result['Link'] = ''

    if st.button('SEARCH'):
        with st.spinner('Searching ......'):
            if (input_text != ''):
                print(f'INPUT: ', input_text)
                if ranker == 'Léxica':
                    #print('Busqueda lexica....')
                    cadena_input = normaliza(input_text[0])
                    bm25 = es.search(index="idx-bus-lex", body={"query": {"match": {"field_traduccion_limpia": cadena_input }}})
                    for hit in bm25['hits']['hits'][0:5]:
                        xtitulo = hit['_source']['field_titulo']
                        xlink   = hit['_source']['field_link']
                        xdescripcion = hit['_source']['field_traduccion']
                        df_result = df_result.append({'Titulo': xtitulo, 'Descripcion': xdescripcion, 'Link': xlink} , ignore_index=True)
                else:
                    #print('Busqueda semántica....')
                    question_embedding = model.encode(input_text[0])
                    sem_search = es.search(index="idx-bus-sem", body={
                          "query": {
                            "script_score": {
                              "query": {
                                "match_all": {}
                              },
                              "script": {
                                "source": "cosineSimilarity(params.queryVector, doc['field_traduccion_vector']) + 1.0",
                                "params": {
                                  "queryVector": question_embedding
                                }
                              }
                            }
                          }
                        })
                    for hit in sem_search['hits']['hits'][0:5]:
                        xtitulo = hit['_source']['field_titulo']
                        xlink   = hit['_source']['field_link']
                        xdescripcion = hit['_source']['field_traduccion']
                        df_result = df_result.append({'Titulo': xtitulo, 'Descripcion': xdescripcion, 'Link': xlink} , ignore_index=True)
                                        
                st.dataframe(df_result)

if __name__ == '__main__':
    run()
