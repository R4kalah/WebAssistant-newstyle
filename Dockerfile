# Usa una imagen base de Python
FROM python:3.12.2

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos de requisitos y los instala
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copia el contenido del proyecto al directorio de trabajo
COPY . /app/

# Exponer el puerto en el que se ejecutará la aplicación
EXPOSE 12500

# Comando para ejecutar la aplicación
# PONER IP DEL COMPUTADOR DE CITYLAB PARA QUE OTRAS PERSONAS PUEDAN CONECTARSE
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "12500"]