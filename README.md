# **DOCUMENTACIÓN DEL ASISTENTE VIRTUAL DE CITYLAB 03/02/2025**

El Presente documento se explican los cambios realizados en el modelo para chatbot de CityScope

## LLM

- chatModelv2.py:
  -Se realizaron cambios al chatModelv2, donde se cambiaron los datos hardcodeados como por ejemplo los indicadores o placas a peticiones a la api del servidor.
  -Se agrego historial, actualmente no tiene ningun limite de cuantos mensajes puede mantener en historial, esto puede ser perjudicial, ya que mensajes muy largos consumiria muchos token de la api de CHATgpt

  -Actualmente el modelo no uas vectorUpdater, le entrega la info atraves de una herramienta, se recomienda buscar el aplicar vectorstore con la documentacion necesaria para el modelo.

## Server

Si se quieren hacer logs o print, usar el logger, no print, si no, no se verá en el contenedor.


**endpoints**:

- _/command_: Aquí llegan los comandos por voz del cliente, se convierten en un archivo .wav, este se transcribe a texto y llama a la funcion **command_LLM**
- _/upload_: Aquí llegan los archivos que se quieren subir al vectorstore. Los archivos llegan como una lista y para cada archivo se saca el content*type y se llama a la función correspondiente. Si se quiere agregar otro tipo de archivo, tienen que buscar su content_type para crear el \_elif* y además crear la función para hacer los chunks de texto.


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

T **vectorUpdater.html** necesita una contraseña para acceder al contenido. Las contraseñas son _citylab123_ respectivamente, están hasheadas por lo que, si quieren cambiarlas, deberán hashear la contraseña que desean y cambiarla en las funciones que checkean las contraseñas, línea 118 en **indexAdmin.html** y línea 40 en **vectorUpdater.html**. La codificación es [SHA256](https://emn178.github.io/online-tools/sha256.html). Si no se necesitan contraseñas para estas páginas pueden simplemente borrar las divisiones que contienen las forms y cambiar el display de _.chatbot_ y _dropdown-menu_

## LANGGRAPH

> [!IMPORTANT]
> El nombre de las herramientas no puede tener espacios. Deben seguir este regex: '^[a-zA-Z0-9_-]+$'."

Si se quieren agregar herramientas, tienen que seguir la misma forma de las que ya están en **chatModelv2.py**:

Se debe crear una clase que represente los argumentos que recibirá la herramienta y después usar esta clase en el args_schema de la herramienta, siguiendo esta estructura: [tooling](https://python.langchain.com/v0.1/docs/modules/tools/custom_tools/) en el apartado Subclass BaseTool.

Una vez se haya creado una nueva herramienta, se debe crear una instancia de la clase en el _**init**_ de la clase _modelov2_ de la misma forma que ya está hecha para las herramientas existentes y después se deben añadir a la lista de herramientas que está más abajo. De este modo, el modelo debería tener acceso a las nuevas herramientas.

## Docker

> [!TIP]
> docker compose up --build

El contenedor tiene toda esta carpeta como volumen, por lo que cualquier cambio se deberia ver reflejado en Docker. Si cambian algo de los requisitos tienen que botar el contenedor y levantarlo denuevo.


El proyecto original fue creado por Kevin L., modificado por Ricardo H. y Bastian N.
el proyecto original se encuentra en  https://github.com/quebin132/WebAssistant/tree/newstyle