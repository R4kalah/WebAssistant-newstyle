from fastapi import FastAPI, WebSocket, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from vectorstore_maker import (
    get_pdf_split,
    text_to_vector,
    test_vector,
    get_text_splits,
    get_docx_splits,
    get_ppt_splits,
)
import aiofiles
import os
from uuid import uuid4
from typing import List

from chatModelv2 import modelov2
import asyncio
from voice_to_text import voice2text

# configuracion logging
import logging

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)
requests_logger = logging.getLogger("requests")
requests_logger.setLevel(logging.WARNING)
documento = []


model = modelov2()


# CUMPLE LA MISMA FUNCION QUE RESPUESTA_LLM PERO LAS PREGUNTAS VAN AL MODELO CON HERRAMIENTAS
async def command_LLM(command: str, connect_id):
    mensaje = "sin asignar"
    try:
        logger.info("%s %s", command, type(command))

        res = await asyncio.wait_for(
            model.graph.ainvoke(
                {"messages": [("user", command)]},
                config={"configurable": {"thread_id": connect_id}},
                stream_mode="values",
            ),
            timeout=60,
        )

        mensaje = res["messages"][-1].content

    except Exception as e:
        logger.info("el error esta en commandlm")
        mensaje = str(e)
    return mensaje


v2t = voice2text()


# ESTA FUNCION TRANSCRIBE EL .WAV A TEXTO
def transcribe(filename: str):
    try:
        # Usar el reconocedor de Google para transcribir el audio
        text = v2t.transcribe_audio_file(filename)
        logger.info("intendo print del texto")
        logger.info(text)
        logger.info("%s", text)

    except Exception as e:
        logger.info(e)
        logger.warning("   %s", e)

    finally:
        os.remove(filename)
        return text


app = FastAPI()
ws_connections = {}
connection_id = str(uuid4())


# AQUI LLEGAN LOS COMANDOS POR VOZ, SE CONVIERTEN A UN .WAV, SE TRANSCRIBEN Y SE LLAMA A COMMAND_LLM
@app.post("/command/")
async def voice2text(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="File not provided")

    try:
        ws_connections[connection_id] = ws_connections
        filename = file.filename
        file_path = filename
        logger.info("empezando carga de archivo")
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())
        logger.info("archivo cargado")
        return JSONResponse(
            status_code=200, content={"message": "File uploaded successfully!"}
        )

    except Exception as e:
        if connection_id in ws_connections:
            del ws_connections[connection_id]
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        logger.info("transcribiendo")
        transcription = transcribe(file_path)
        logger.info("%s %s", transcription, type(transcription))
        respuesta = await command_LLM(transcription, connection_id)
        return JSONResponse(
            content={
                "transcripcion": transcription,  # Añadir transcripción
                "respuesta": respuesta,
            },
            status_code=200,
        )


@app.get("/")
async def home():
    return FileResponse("indexAdmin.html")


@app.get("/archivos")
async def paginaCargaArchivos():
    return FileResponse("vectorUpdater.html")


# AQUI LLEGAN LOS ARCHIVOS QUE SE QUIEREN AGREGAR AL VECTORSTORE, PUEDEN SER MULTIPLES
@app.post("/upload")
async def extract_text_from_pdf(files: List[UploadFile] = File(...)):
    # Ensure the uploaded file is a PDF
    results = []
    cantidad = len(files)
    current = 1
    logger.info("     Empezando procesamiento de archivos")
    # print("Empezando procesamiento de archivos")
    for file in files:
        print(f"{file.filename} : Archivo {current}/{cantidad}")

        try:
            logger.info("     Archivo del tipo correcto, iniciando procesamiento ...")
            # print("Archivo del tipo correcto, iniciando procesamiento ...")
            # Read the PDF file contents
            contents = await file.read()

            # Save the PDF file temporarily
            async with aiofiles.open(file.filename, "wb") as f:
                await f.write(contents)

            if file.content_type == "application/pdf":
                texto_splitted = get_pdf_split(file.filename)

                # Clean up (remove the temporary file)
                os.remove(file.filename)

                text_to_vector(texto_splitted, "vectorstorev2")

            elif file.content_type == "text/plain":
                texto_splitted = get_text_splits(file.filename)
                text_to_vector(texto_splitted, "vectorstorev2")

                os.remove(file.filename)
            elif (
                file.content_type
                == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ):
                texto_splitted = get_docx_splits(file.filename)

                text_to_vector(texto_splitted, "vectorstorev2")

                #  test_vector("vectorstorev2","simulacion")
                os.remove(file.filename)

            elif (
                file.content_type
                == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            ):
                texto_splitted = get_ppt_splits(file.filename)
                text_to_vector(texto_splitted, "vectorstorev2")
                os.remove(file.filename)
            else:
                logger.warning(
                    "      Este tipo de archivo no es compatible por el momento"
                )
                # print("Este tipo de archivo no es compatible por el momento")

            logger.info("   Archivo añadido al vectorstore")
            # print("Archivo añadido al vectorstore")
            current += 1

            results.append({"filename": file.filename, "text": texto_splitted})

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"There was an error processing the file: {str(e)}",
            )

        finally:
            await file.close()

    return {"message": "Files processed successfully"}


@app.get("/upload")
async def show_files():
    return documento


@app.websocket("/wsadmin")
async def websocket_admin(websocket: WebSocket):
    try:
        await websocket.accept()
        logger.info("     WebSocket connection accepted to admin")

        ws_connections[connection_id] = websocket
        logger.info("     Connection ID: %s", connection_id)

        # Enter the loop to continuously receive and send messages
        while True:
            # SE RECIBE PREGUNTA
            data = await websocket.receive_text()
            logger.info("    %s", data)

            # SE CREA RESPUESTA ASINCRONICA

            respuesta = await command_LLM(data, connection_id)

            await websocket.send_text(respuesta)
            logger.info("   %s", respuesta)
    except Exception as e:
        logger.error("  Error in Websocket handler: %s", e)


# AQUI SE MONTA LA CARPETA "STATIC" EN EL ENDPOINT "/STATIC"
app.mount("/static", StaticFiles(directory="static"), name="static")

# SE ACEPTAN TODAS LAS CONEXIONES
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
