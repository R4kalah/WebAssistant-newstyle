from typing import Optional, Type
import requests
from rapidfuzz import process, fuzz
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
import os
from dotenv import dotenv_values
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.aiosqlite import AsyncSqliteSaver
from langchain.schema import SystemMessage, HumanMessage, AIMessage

# memoria
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.memory import MemorySaver

memory = SqliteSaver.from_conn_string(":memory:")

# para imprimir en terminal escribir logger("%s","tu mensaje")
import logging

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


# funciones de las herramienta para Pedir la info al servidor "http://192.168.31.120:8500/api/actions/set_current_state/"
def GetCurrentMap():
    logger.info("obteniendo lista de los mapas")
    # Obtener la lista de mapas desde el servidor
    mapa_server = requests.get("http://192.168.31.120:8500/api/indicators/")
    # Procesar los datos recibidos
    indicators = mapa_server.json()
    Map_List = {}

    # Crear el diccionario con nombres e IDs de los mapas
    for index, indicator in enumerate(indicators, start=1):
        name = indicator.get("name", "Sin nombre").lower()
        id = indicator.get("id", "Sin id")
        Map_List[name] = id
    return Map_List


# esta manda el estado a modificar
def SendCurrentState(modified_state):
    logger.info("%s", "enviando estado nuevo")
    # manda el nuevo estado de las placas
    pyload = {"state": modified_state}
    logger.info("%s", str(pyload))
    # Paso 4: Enviar el payload a la API
    url = "http://192.168.31.120:8500/api/actions/set_current_state/"
    try:
        r = requests.post(url, json=pyload)
        r.raise_for_status()
        logger.info("%s", "enviado el estado nuevo")

    except requests.exceptions.RequestException as e:
        logger.info("%s\nError al enviar los datos a la API:")


# esta pide el estado actual de las placas al servidor
def RequestCurrentState():
    logger.info("%s", "recompilando estado actual")
    try:
        response = requests.get(
            "http://192.168.31.120:8500/api/actions/get_global_variables/"
        )

        response.raise_for_status()
        actual = response.json()
        return actual
    except requests.exceptions.RequestException as e:
        return logger.info("%s", e)


# Variables, se definen como el modelo busca las variables, describes que es lo que quieres que entre como variable.


class fetchMapInput(BaseModel):
    mapa: str = Field(description="El nombre del mapa que quiere cambiar el usuario")


class UpdatePlacasInput(BaseModel):
    placa: str = Field(description="Placa que se quiere cambiar")
    estado: str = Field(
        description="Estado al que se quiere cambiar la placa, puede ser 0 para presente y 1 para futuro"
    )


class UpdateVariasPlacasInput(BaseModel):
    placas: list[str] = Field(description="Lista de placas que se quieren cambiar")
    estados: list[str] = Field(
        description="Lista de estados correspondientes a las placas"
    )


class MensajeUsuario(BaseModel):
    query: list[str] = Field(
        description="Obten La informacion que desea obtener el usuario que puede ser agrupa la informacion y deci: "
    )


class GetStatusInput(BaseModel):
    consulta: str = Field(
        description="Tipo de información solicitada: 'mapa', 'placas' o 'ambos'"
    )


# Herramientas, se definen las distintas herramientas donde name es el nombre de esta, ojo tiene que ir sin espacios.
# descripcion es cuando el modelo va a elegir usar la herramienta
# args_chema es el tipo de variables que usa.


# la siguiente herramienta realiza el cambio de mapas o indicadores, extrayendo la lista de indicadores desde el servidor.
class FetchMapTool(BaseTool):
    name = "Cambio_de_mapas"
    description = "Debes usar esta herramienta solo si mencionan cambiar a algun mapa."
    args_schema: Type[BaseModel] = fetchMapInput
    return_direct: bool = True

    def _run(
        self, mapa: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> None:
        """Usa la herramienta"""
        logger.info("usando herramienta:%s", self.name)
        mapa_min = mapa.lower()
        map_to_code = GetCurrentMap()

        try:
            if mapa_min in map_to_code:
                mapa_final = process.extractOne(mapa_min, map_to_code.keys())[0]
            else:
                logger.info("mapa min no encontrado en map to code")
                map_names = list(map_to_code.keys())
                map_names_str = ", ".join(map_names)
                return (
                    "El mapa no se encuentra en la lista, los mapas disponibles son: "
                    + map_names_str
                )

        except Exception:
            logger.info("error")

        mapa_id = map_to_code[mapa_final]  # Obtener el ID del mapa encontrado

        # Cambiar el estado del indicador en el servidor
        payload = {"indicator_id": mapa_id}
        url = "http://192.168.31.120:8500/api/actions/set_current_indicator/"

        try:
            print("mandando json")
            response = requests.post(url, json=payload)
            response.raise_for_status()  # Lanza excepción si el status no es 200
        except requests.exceptions.RequestException as e:
            print("Error al cambiar el estado del mapa:", str(e))
            return  # No hace nada más si hay error
        finally:
            return


# Herrmientas para cambiar las placas


class CambiarUnaPlaca(BaseTool):
    name = "Cambiar_estado_de_una_placa"
    description = "Usa esta herramienta cuando se te pida cambiar una sola placa."
    args_schema: Type[BaseModel] = UpdatePlacasInput
    return_direct: bool = True

    def _run(self, placa: str, estado: str) -> str:
        """Procesa el comando del usuario y actualiza las placa."""
        # Obtener el estado actual desde la API
        logger.info("usando herramienta:%s", self.name)

        try:
            if int(placa) > 7:
                return "las placa van del 1 al 7, dile al usuario que introdusca una placa valida"

        except ValueError:
            return "la placa debe ser un numero"

        try:
            actual = RequestCurrentState()
            modified_state = actual["indicator_state"]

        except Exception as eror:
            logger.info("%s", eror)

        try:
            # Actualizar el estado modificado
            for placa, estado in zip(placa, estado):
                modified_state[placa] = int(estado)
                SendCurrentState(modified_state)

        except Exception as e:
            logger.info("%s", e)

            return


class CambiarVariasPlacas(BaseTool):
    name = "Cambiar_estado_de_varias_placas"
    description = "Usa esta herramienta cuando se te pida cambiar más de una placa."
    args_schema: Type[BaseModel] = UpdateVariasPlacasInput
    return_direct: bool = True

    def _run(self, placas: list[str], estados: list[str]) -> str:
        """Procesa el comando del usuario y actualiza las placas especificadas."""
        if len(placas) != len(estados):
            return "El número de placas no coincide con el número de estados. Por favor verifica."

        try:
            actual = RequestCurrentState()
            modified_state = actual["indicator_state"]

            for placa, estado in zip(placas, estados):
                if not placa.isdigit() or int(placa) < 1 or int(placa) > 7:
                    return f"La placa {placa} no es válida. Las placas van del 1 al 7."
                if not estado.isdigit():
                    return f"El estado {estado} para la placa {placa} no es válido. Debe ser un número."
                modified_state[placa] = int(estado)

            SendCurrentState(modified_state)
            return "Las placas fueron actualizadas correctamente."

        except Exception as e:
            logger.info("Error al cambiar múltiples placas: %s", e)
            return (
                "Hubo un error al cambiar el estado de las placas. Intenta nuevamente."
            )


# Agregar después de las demás herramientas
class ContextRetrievalTool(BaseTool):
    name = "Obtener_Contexto_Relevante"
    description = """Usa esta herramienta cuando el usuario pregunte sobre:
    - Funcionamiento del sistema
    - Significado de placas/colores
    - Información sobre Citylab
    - Utilidad de la maqueta
    - Detalles de mapas/indicadores"""
    args_schema: Type[BaseModel] = MensajeUsuario

    # Diccionario con contextos específicos
    context_db = {
        "funcionamiento": "CityScope trabaja con placas interactivas que agrupan proyectos urbanos, las cuales son sensorizadas por un grupo de receptores que indican al sistema lógico qué calcular, qué proyectar y con qué tipología de mapa trabajar.",
        "placas": "Cada placa representa, un proyecto dentro de la costanera,se diferencia con los numeros y en estado presente representando el estado actual del sitio donde se ubica el proyecto y futuro a que el proyecto en estado finalizado.",
        "colores": "Claros, representa un indicador positivo como por ejemplo cercania al plazas o lugares culturales, colores oscuros representan indicadores negativos, como por ejemplo lejania a distintos lugares culturales o una densidad de poblacion alta",
        "citilab": "City Lab Biobío es un espacio de estudio e investigación creativa que utiliza la ciencia y tecnología para orientar el proceso de toma de decisión asociado al crecimiento y desarrollo de nuestras ciudades. La experiencia y percepción de las comunidades son ejes centrales que movilizan nuestra ciencia de ciudad, participando activamente en las diferentes etapas de análisis.",
        "maqueta": "La plataforma tiene como nombre CityScope y es una interfaz física de visualización integrada de proyectos urbanos. Se alimenta de grandes cantidades de datos, los que son analizados en macro indicadores relevantes para la calidad de vida urbana de un sector. Las variables son proyectadas sobre la interfaz física mediante la generación de mapas específicos que dan cuenta de los cambios producidos sobre el sector en los indicadores y escenarios que se quieren ver.",
        "nombre de la maqueta": "el nombre de la maqueta es CityScope",
        "mapas": "Indicador 1: Movilidad urbana...",
        "uso": "La ciencia detrás de CityScope nos permite ver cómo impacta en la ciudad cada proyecto estudiado y analizado previamente, permitiendo cientos de interacciones distintas entre situaciones actuales y futuras.",
    }

    def _run(self, query: str) -> str:
        logger.info("usando herrmienta contexto")

        # Buscar coincidencias con RapidFuzz
        matches = process.extract(
            query, self.context_db.keys(), scorer=fuzz.partial_ratio
        )

        logger.info(matches)

        # Tomar los 4 contextos más relevantes con score >70
        [self.context_db[key] for key, score, _ in matches if score > 70][:3]

        return


class ObtenerEstadoActualTool(BaseTool):
    name = "Obtener_estado_actual"
    description = "Usa esta herramienta cuando el usuario pregunte por el mapa activo actual o el estado de las placas."
    args_schema: Type[BaseModel] = GetStatusInput
    return_direct = True

    def _run(self, consulta: str) -> str:
        try:
            # Obtener datos actualizados
            map_data = GetCurrentMap()  # Ahora usa indicator_id como valor
            current_state = RequestCurrentState()

            # 1. Obtener nombre del mapa actual
            current_map_id = int(
                current_state["indicator_id"]
            )  # Usar indicator_id del estado
            inverted_map = {v: k for k, v in map_data.items()}

            current_map_name = inverted_map[current_map_id]

            # 2. Procesar estado de placas
            placas_state = current_state["indicator_state"]
            estado_formateado = "\n".join(
                [
                    f"Placa {k}: {'Futuro' if v == 1 else 'Presente'}"
                    for k, v in sorted(placas_state.items(), key=lambda x: int(x[0]))
                ]
            )

            # 3. Construir respuesta
            if consulta.lower() == "mapa":
                return f" Mapa activo: {current_map_name}"

            elif consulta.lower() == "placas":
                return f" Estado actual:\n{estado_formateado}"

            elif consulta.lower() == "ambos":
                return f"Mapa activo: {current_map_name}\n\n🔘 Estados:\n{estado_formateado}"

            return "Consulta no válida. Opciones: 'mapa', 'placas' o 'ambos'"

        except Exception as e:
            logger.error(f"Error en ObtenerEstadoActualTool: {str(e)}")
            return "No pude obtener la información solicitada"


class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]


# aqui se arma el grafo
class modelov2:
    def __init__(self):
        # Cargar variables de entorno
        self.env_values = dotenv_values(".env")
        self.openai_key = self.env_values["OPENAI_API_KEY"]

        # Contexto persistente del sistema
        self.system_context = """Eres un asistente de  especializado en gestión de mapas y placas. 
        Responde de forma concisa. Si No sabes la respuesta o necesitas información adicional, usa las herramientas."""

        # Configurar herramientas
        self.toolmap = FetchMapTool()
        self.toolsingleplaca = CambiarUnaPlaca()
        self.toolmultipleplaca = CambiarVariasPlacas()
        self.context_tool = ContextRetrievalTool()
        self.status_tool = ObtenerEstadoActualTool()

        self.herramientas = [
            self.toolmap,
            self.toolsingleplaca,
            self.toolmultipleplaca,
            self.context_tool,
            self.status_tool,
        ]

        # Configurar LLM con el contexto persistente
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", api_key=self.openai_key)
        self.llm_with_tools = self.llm.bind_tools(self.herramientas)

        # Crear un gráfico de estados
        self.graph_builder = StateGraph(State)
        self.graph_builder.add_node("chatbot", self.chatbot)
        self.tool_node = ToolNode(tools=self.herramientas)
        self.graph_builder.add_node("tools", self.tool_node)
        self.graph_builder.add_conditional_edges("chatbot", tools_condition)
        self.graph_builder.add_edge("tools", "chatbot")
        self.graph_builder.set_entry_point("chatbot")
        self.graph = self.graph_builder.compile(checkpointer=MemorySaver())

    # esta funcion llama al modelo para correr con el mensaje del usuario y retornar el mensaje

    async def chatbot(self, state: State):
        # Obtener mensajes actuales del estado
        current_messages = state["messages"]

        # 1. Fuerza el contexto del sistema al inicio de los mensajes
        system_message = SystemMessage(content=self.system_context)

        # Filtrar cualquier otro mensaje de sistema existente
        filtered_messages = [
            msg for msg in current_messages if not isinstance(msg, SystemMessage)
        ]

        # Crear nueva lista de mensajes con el contexto primero
        processed_messages = [system_message] + filtered_messages

        # 2. Llamar al LLM con el contexto garantizado
        try:
            response = await self.llm_with_tools.ainvoke(processed_messages)

        except Exception as e:
            logger.error("Error en LLM: %s", e)
            response = AIMessage(content="Lo siento, hubo un error en el sistema")

        # 3. Mantener historial completo (incluyendo contexto en cada iteración)
        new_messages = current_messages + [response]

        return {"messages": new_messages}
