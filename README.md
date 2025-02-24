# **DOCUMENTACIÓN DEL ASISTENTE VIRTUAL DE CITYLAB**

El html de la página principal es **index.html**, en este se importan **conexion.js** y **style.css**, estos últimos están en la carpeta static. Si prefieren, pueden mover **index.html** a static, pero tendrían que cambiar el endpoint **"/"** en **main.py**. Por alguna razón FastAPI no reconoce el favicon.

## LLM

En los momentos de escribir esta documentación el vectorstore que se está utilizando es **vectorstorev2**, el cual contiene unos 6 boletines y un par de archivos más, se pueden agregar documentos mediante el endpoint **"/archivos"**, donde simplemente cargan los archivos que quieran y los suben, estos se agregaran directamente a **vectorstorev2**. Si por alguna razón quisieran crear otro vectorstore tendrían que actualizar el código en **chatModel.py** alrededor de la línea **43** y en el endpoint **"/archivos"** cada vez que se llama a la función _text_to_vector_. Si necesitan habilitar más tipos de archivos para subirse al vector store se recomienda crear una función que lea el contenido y lo parta en chunks de texto como las funciones análogas en **vectorstore_maker.py** y se recomienda seguir la "convencion" _get\_{tipo_de_archivo}\_splits_ para el nombre de la función.

- chatModel.py:
  - chat: Aquí se establece el modelo que responderá las preguntas. Si se quiere usar un modelo local, se tiene que hacer mediante LangChain: [How to run local models](https://python.langchain.com/docs/how_to/local_llms/)
  - embeddings: Modelo de embeddings, tienen que coincidir cuando se carga y guarda el vectorstore
  - vectorstore: sin _allow_dangerous_deserialization="true"_ no funciona
    -promptContextualizador: Sirve para que el modelo tenga en cuenta el historial del chat al responder, lo saque directo del tutorial de Langchain solo que traducido al español
    -qaSystemPrompt: Prompt general para darle un contexto de cómo debe comportarse al LLM
    El resto es la forma estándar de cómo se crea la chain, por lo que no deberían cambiarlo. [llm with chat history](https://python.langchain.com/v0.1/docs/use_cases/question_answering/chat_history/)

## Server

Si se quieren hacer logs, usar el logger, no print, si no, no se verá en el contenedor.

- respuesta*LLM: toma una pregunta como parámetro y se llama al método \_ainvoke* del modelo de **chatModel.py**.
- command*LLM: lo mismo que \_respuesta_LLM*, pero con el modelo de **chatModel2.py**, el cual tiene acceso a herramientas.
- transcribe: se usa whisper de OpenAI, si se quisiera usar otro modelo tendría que cambiar la lógica en el archivo **voice_to_text.py**

**endpoints**:

- _/command_: Aquí llegan los comandos por voz del cliente, se convierten en un archivo .wav, este se transcribe a texto y llama a la funcion **command_LLM**
- _/upload_: Aquí llegan los archivos que se quieren subir al vectorstore. Los archivos llegan como una lista y para cada archivo se saca el content*type y se llama a la función correspondiente. Si se quiere agregar otro tipo de archivo, tienen que buscar su content_type para crear el \_elif* y además crear la función para hacer los chunks de texto.
- _/ws_ y _/wsadmin_: hacen lo mismo, pero el primero usa el modelo normal y el otro usa el modelo con herramientas.

**static**: la carpeta static está montada en el servidor. Si el cliente necesita acceder a algún archivo, tendra que hacerlo mediante _static/{nombre del archivo}_, por ejemplo: el html del cliente importa un archivo que está en static debe hacerlo de esta forma.

> [!IMPORTANT]
> SI SE NECESITA CAMBIAR LA IP DEL SERVER ES NECESARIO CAMBIARLA EN LOS SIGUIENTES ARCHIVOS:
>
> - _conexion.js_ linea 1
> - _vectorUpdater.html_ linea 19
> - _indexAdmin.html_ linea 167

## Cliente

Partes importantes:

- **conexion.js**: Se establece el websocket y sus metodos onopen, onmessage y onclose. en el onmessage se maneja la lógica de mostrar la respuesta en el chat y, si se quisiera, se puede usar la función _speak_ con la respuesta del LLM como argumento para que se escuche en la página . La función _onSubmit_ manda la pregunta del usuario al back. El resto de cosas se pueden mejorar.

Tanto **indexAdmin.html** como **vectorUpdater.html** necesitan una contraseña para acceder al contenido. Las contraseñas son _citilabs_ y _citylab123_ respectivamente, están hasheadas por lo que, si quieren cambiarlas, deberán hashear la contraseña que desean y cambiarla en las funciones que checkean las contraseñas, línea 118 en **indexAdmin.html** y línea 40 en **vectorUpdater.html**. La codificación es [SHA256](https://emn178.github.io/online-tools/sha256.html). Si no se necesitan contraseñas para estas páginas pueden simplemente borrar las divisiones que contienen las forms y cambiar el display de _.chatbot_ y _dropdown-menu_

## LANGGRAPH

> [!IMPORTANT]
> El nombre de las herramientas no puede tener espacios. Deben seguir este regex: '^[a-zA-Z0-9_-]+$'."

El modelo con herramientas usa la librería langgraph para su creación, actualmente no cuenta con memoria porque se pensó usar este solo para interactuar con el Cityscope. Si se quisiera añadir memoria, seguir el siguiente tutorial: [Memoria](https://langchain-ai.github.io/langgraph/tutorials/introduction/#part-3-adding-memory-to-the-chatbot).

Si se quieren agregar herramientas, tienen que seguir la misma forma de las que ya están en **chatModelv2.py**:

Se debe crear una clase que represente los argumentos que recibirá la herramienta y después usar esta clase en el args_schema de la herramienta, siguiendo esta estructura: [tooling](https://python.langchain.com/v0.1/docs/modules/tools/custom_tools/) en el apartado Subclass BaseTool.

Una vez se haya creado una nueva herramienta, se debe crear una instancia de la clase en el _**init**_ de la clase _modelov2_ de la misma forma que ya está hecha para las herramientas existentes y después se deben añadir a la lista de herramientas que está más abajo. De este modo, el modelo debería tener acceso a las nuevas herramientas.

## Docker

> [!TIP]
> docker compose up --build

El contenedor tiene toda esta carpeta como volumen, por lo que cualquier cambio se deberia ver reflejado en Docker. Si cambian algo de los requisitos tienen que botar el contenedor y levantarlo denuevo.

