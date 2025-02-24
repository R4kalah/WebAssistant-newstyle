from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import Docx2txtLoader
from langchain_community.document_loaders import CSVLoader
from langchain_community.document_loaders import UnstructuredPowerPointLoader
import pymupdf
import os

textSplit = RecursiveCharacterTextSplitter(chunk_size=150,
                                             chunk_overlap=15,
                                             length_function=len)
def get_pdf_split(path):
  
  
  document = pymupdf.open(path)
  
  text = ""
  for page_num in range(len(document)):
            page = document.load_page(page_num)
            text += page.get_text()
  
  document.close()  # Ensure the document is closed
  #Pages will be list of pages, so need to modify the loop
  
  textoSpliteado = textSplit.split_text(text)
  
  
  return textoSpliteado

def get_text_splits(text_file):
  """Function takes in the text data and returns the  
  splits so for further processing can be done."""
  with open(text_file,'r') as txt:
    data = txt.read()

  
  doc_list = textSplit.split_text(data)
  return doc_list

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings


def text_to_vector(doc_list,vector_path):
    if os.path.exists(vector_path):
      tempVector= FAISS.load_local(vector_path,OpenAIEmbeddings(),allow_dangerous_deserialization="true")
      vectorAdd =FAISS.from_texts(doc_list,OpenAIEmbeddings())
      tempVector.merge_from(vectorAdd)
      tempVector.save_local(vector_path)
    else:
      vectorAdd =FAISS.from_texts(doc_list,OpenAIEmbeddings())
      vectorAdd.save_local(vector_path)
        

def test_vector(vector_path,query):
    vector=FAISS.load_local(vector_path,OpenAIEmbeddings(),allow_dangerous_deserialization="true")
    print(vector.similarity_search(query))
# Se crean los vectorstores FAISS y los retrievers

def get_csv_splits(csv_file):
  """Function takes in the csv and returns the  
  splits so for further processing can be done."""
  csvLoader = CSVLoader(csv_file)
  csvdocs = csvLoader.load()
  return csvdocs
# vectorstore = FAISS.load_local("vectorstore_assistant_alfa")
# vectorstore.save_local("vectorstore_assistant_alfa")

def get_docx_splits(docx_path):
   doc= Docx2txtLoader(docx_path).load()[0].page_content
   
   
                                           
   doc_list= textSplit.split_text(doc)
   
   return doc_list

def get_ppt_splits(ppt_path):
   
   loader= UnstructuredPowerPointLoader(
        ppt_path, mode="single", strategy="fast",
    )
   ppt= loader.load()
   ppt_ext=ppt[0].page_content
   doc_list= textSplit.split_text(ppt_ext)

   
   return doc_list
   

