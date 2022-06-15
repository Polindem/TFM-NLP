#-------------------------------------------------------------------------------
#Proceso de creación de Indice para búsqueda Léxica y Semántica en Elasticsearch
#Recibe como parámetro Tipo 1: Busqueda léxica, 2:Busqueda Semántica
#-------------------------------------------------------------------------------
#Declaracion de librerias
from sentence_transformers import SentenceTransformer, util
from elasticsearch import Elasticsearch, helpers
import csv
import os
import tqdm.autonotebook
import sys

#Recibe parametro desde el exterior
#Tipo 1: Busqueda léxica, 2:Busqueda Semántica
tipoindice = sys.argv[1]

#Conexión a Elasticsearch
es = Elasticsearch(['localhost:9200'],http_auth=('elastic', 'ruben2022'))
#Referencia al modelo transformer
model = SentenceTransformer('multi-qa-distilbert-dot-v1')

#Datos del archivo Csv a leer
if tipoindice == '1': #Para Busqueda léxica
    name_file = 'movies_bus_lexica'
    name_idx  = 'idx-bus-lex'
else: #Para Busqueda Semántica
    name_file = 'movies_bus_semantica'
    name_idx  = 'idx-bus-sem'
    
ext_file = '.csv'
name_file_input = name_file + ext_file
max_corpus_size = 1000000

#Prepara y lee la data para la indexación
nro_fila = 1
long_cadena = 0
cadena_traduccion = ''
cadena_traduccion_limpia = ''
cadena_titulo= ''
cadena_link  = ''
campo_traduccion = {}
campo_traduccion_limpia = {}
campo_titulo = {}
campo_link = {}
num_leidos = 0
encontro_error = 0
with open(name_file_input, encoding="utf8") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:        
        try:
            cadena_titulo = row['titulo']
            cadena_link = row['link']
            cadena_traduccion = row['traduccion']
            cadena_traduccion_limpia = row['traduccion_limpia']
                
            if (cadena_titulo != '') and (cadena_link != '') and (cadena_traduccion != ''):
                #Se quita comilla simple al inicio y final de la cadena de texto
                long_cadena = len(cadena_traduccion)-1
                cadena_traduccion = cadena_traduccion[1:long_cadena]
                #Convierte nro fila a string
                nro_fila_char = str(nro_fila)
                #Asigna a cada lista su correspondiente campo
                campo_traduccion[nro_fila_char] = cadena_traduccion
                campo_traduccion_limpia[nro_fila_char] = cadena_traduccion_limpia                    
                campo_titulo[nro_fila_char]     = cadena_titulo
                campo_link[nro_fila_char]       = cadena_link
                #Valida si se superó el tamaño del corpus                                
                if len(campo_traduccion_limpia) >= max_corpus_size:
                    encontro_error = 1
                    break
                nro_fila = nro_fila + 1
        except ValueError:
            encontro_error = 2

        num_leidos = num_leidos + 1

if encontro_error == 0:
    #Asigna ids y descripciones de cada campo
    ids_traduccion = list(campo_traduccion.keys())
    desc_traduccion = [campo_traduccion[qid] for qid in ids_traduccion]
    ids_traduccion_limpia = list(campo_traduccion_limpia.keys())
    desc_traduccion_limpia = [campo_traduccion_limpia[qid] for qid in ids_traduccion_limpia]        
    ids_titulo = list(campo_titulo.keys())
    desc_titulo = [campo_titulo[qid] for qid in ids_titulo]
    ids_link = list(campo_link.keys())
    desc_link = [campo_link[qid] for qid in ids_link]
    print('                                                   ')
    print('***** PASO 1: Proceso de lectura de archivo terminado *****')
    print('Nro. de registros leidos  : ' + str(num_leidos))
    print('Nro. de registros cargados: ' + str(nro_fila-1))
    print('                                                   ')
        
    #Borra indice si existe
    if es.indices.exists(index=name_idx):
        print('Borrando indice: ' + name_idx)
        es.indices.delete(index=name_idx)
    
    #Crea Indice:
    try:
        es_index = {
            "mappings": {
              "properties": {
                "field_traduccion_limpia": { "type": "text", "index": "true" },
                "field_traduccion": { "type": "text", "index": "false" },
                "field_titulo": { "type": "text", "index": "false" },
                "field_link": { "type": "text", "index": "false" },
                "field_traduccion_vector": { "type": "dense_vector", "dims": 768 }
              }
            }
        }

        es.indices.create(index=name_idx, body=es_index, ignore=[400])
        chunk_size = 500
        with tqdm.tqdm(total=len(ids_traduccion)) as pbar:
            for start_idx in range(0, len(ids_traduccion), chunk_size):
                end_idx = start_idx + chunk_size
                embeddings = model.encode(desc_traduccion[start_idx:end_idx], show_progress_bar=False)
                bulk_data = []
                for ids, traduccion, titulo, link, traduccion_limpia, embedding  in zip(ids_traduccion[start_idx:end_idx], desc_traduccion[start_idx:end_idx], desc_titulo[start_idx:end_idx], desc_link[start_idx:end_idx], desc_traduccion_limpia[start_idx:end_idx], embeddings):
                    bulk_data.append({
                            "_index": name_idx,
                            "_id": ids,
                            "_source": {
                                "field_traduccion_limpia": traduccion_limpia,
                                "field_traduccion": traduccion,
                                "field_titulo": titulo,
                                "field_link": link,
                                "field_traduccion_vector": embedding
                            }
                        })
                    
                helpers.bulk(es, bulk_data)
                pbar.update(chunk_size)

        print('                                                   ')
        print('***** PASO 2: Proceso de generación de índice terminado correctamente *****')
        print('                                                   ')
    except:
        print('¡Error durante el proceso de indexación!: ', sys.exc_info()[0])

elif encontro_error == 1:
    print('¡Error en el Proceso de lectura de archivo csv, se superó el max_corpus_size!')
else:
    print('¡Error en el proceso de lectura de archivo csv!, fila: ' + str(nro_fila))
