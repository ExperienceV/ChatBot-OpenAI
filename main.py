from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI
from pathlib import Path
import markdown
import uvicorn
import os

# Configurar la API key y base_url de DeepSeek
# Se usa un cliente asincrónico para manejar las respuestas del chatbot
client = AsyncOpenAI(api_key=os.getenv("API_KEY"), base_url="https://api.deepseek.com")

# Crear una instancia de la aplicación FastAPI
app = FastAPI()

# Montar archivos estáticos en la ruta '/static' (para servir HTML, CSS, JS, etc.)
app.mount('/static', StaticFiles(directory='static'), name='static')

@app.get('/', response_class=HTMLResponse)
async def chat_page():
    """
    Carga y devuelve el contenido del archivo HTML principal.
    Este archivo debe estar en la carpeta 'static'.
    """
    path = Path('static/index.html')
    return path.read_text(encoding='utf-8')

class ChatBot:
    """
    Clase que maneja la lógica del chatbot, incluyendo el historial de mensajes
    y la interacción con la API de DeepSeek.
    """
    def __init__(self, system_message="Eres un asistente útil."):
        """
        Inicializa el chatbot con un mensaje del sistema opcional.
        :param system_message: Mensaje inicial que define el comportamiento del bot.
        """
        self.historial = []  # Lista para almacenar el historial de conversación
        if system_message:
            self.historial.append({"role": "system", "content": system_message})
        
    async def enviar_mensaje(self, mensaje_usuario):
        """
        Envía un mensaje del usuario al chatbot y obtiene una respuesta.
        :param mensaje_usuario: Texto ingresado por el usuario.
        :return: Mensaje de respuesta del chatbot en formato Markdown.
        """
        self.historial.append({"role": "user", "content": mensaje_usuario})

        try:
            # Solicita una respuesta a la API de DeepSeek
            respuesta = await client.chat.completions.create(
                model="deepseek-chat",  # Modelo de IA utilizado
                messages=self.historial,  # Historial de la conversación
                stream=False  # Se solicita la respuesta completa de una vez
            )

            # Extraer el contenido de la respuesta
            respuesta_asistente = respuesta.choices[0].message.content
            self.historial.append({"role": "assistant", "content": respuesta_asistente})

            # Convertir la respuesta a formato Markdown para mejorar la presentación
            texto_formateado = markdown.markdown(respuesta_asistente, extensions=["extra"])

            # Devolver la respuesta en formato procesado
            yield texto_formateado

        except Exception as e:
            # En caso de error, devolver el mensaje de error formateado
            yield markdown.markdown(f"Error: {str(e)}")

# Crear una instancia del chatbot con una personalidad personalizada
chatbot = ChatBot(system_message="Eres una IA que habla español y respondes de la forma más virgen posible, usando emojis como uwu 7w7 >///<, dices nya onichan y otras vainas de vírgenes")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Maneja la conexión WebSocket para comunicación en tiempo real entre el cliente y el chatbot.
    :param websocket: Conexión WebSocket establecida con el cliente.
    """
    await websocket.accept()  # Aceptar la conexión WebSocket
    try:
        while True:
            mensaje_usuario = await websocket.receive_text()  # Recibir mensaje del usuario
            async for chunk in chatbot.enviar_mensaje(mensaje_usuario):
                await websocket.send_text(chunk)  # Enviar la respuesta del chatbot al cliente
    except WebSocketDisconnect:
        print("Cliente desconectado")  # Registrar la desconexión en la consola
    except Exception as e:
        print(f"Error en la conexión WebSocket: {str(e)}")  # Registrar errores

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))  # Usa el puerto 8000 como fallback
    uvicorn.run(app, host="0.0.0.0", port=port)