import sys
import requests
import json
from time import sleep
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import pygame
import os

# Configuración de Notion - REEMPLAZAR CON TUS DATOS REALES
NOTION_TOKEN = "tu_token_real_de_notion"
CLIENTES_DB_ID = "id_base_datos_clientes"
VISITAS_DB_ID = "id_base_datos_visitas"

# Configuración de rutas
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SOUND_PATH = "/home/pi/sounds/"

# Inicializar sonidos
pygame.mixer.init()
beep_sound = pygame.mixer.Sound(os.path.join(SOUND_PATH, "beep.wav"))
success_sound = pygame.mixer.Sound(os.path.join(SOUND_PATH, "success.wav"))
error_sound = pygame.mixer.Sound(os.path.join(SOUND_PATH, "error.wav"))

def mostrar_formulario(card_id):
    """Muestra formulario de registro para nueva tarjeta"""
    try:
        # Crear imagen con formulario
        img = Image.new('RGB', (800, 480), color='white')
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(FONT_PATH, 24)
        
        draw.text((50, 50), "REGISTRO NUEVO CLIENTE", fill="black", font=font)
        draw.text((50, 100), f"ID Tarjeta: {card_id}", fill="black", font=font)
        draw.text((50, 150), "Nombre:", fill="black", font=font)
        draw.text((50, 200), "Teléfono:", fill="black", font=font)
        draw.text((50, 250), "Correo:", fill="black", font=font)
        
        # Mostrar en pantalla
        img.save("/tmp/formulario.png")
        os.system("pkill fbi; fbi -T 1 -a /tmp/formulario.png")
        
        # Datos simulados para demo
        return {
            "nombre": "Juan Pérez",
            "telefono": "555-1234",
            "correo": "juan@ejemplo.com"
        }
    except Exception as e:
        print(f"Error en formulario: {e}")
        return None

def registrar_cliente(card_id, datos):
    """Registra nuevo cliente en Notion"""
    if not datos:
        return False
        
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    payload = {
        "parent": {"database_id": CLIENTES_DB_ID},
        "properties": {
            "Nombre": {"title": [{"text": {"content": datos["nombre"]}}]},
            "Teléfono": {"rich_text": [{"text": {"content": datos["telefono"]}}]},
            "Correo": {"email": datos["correo"]},
            "ID Tarjeta": {"rich_text": [{"text": {"content": card_id}}]},
            "Visitas": {"number": 0}
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"Error registro cliente: {e}")
        return False

def obtener_cliente(card_id):
    """Busca cliente por ID de tarjeta"""
    url = f"https://api.notion.com/v1/databases/{CLIENTES_DB_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    payload = {
        "filter": {
            "property": "ID Tarjeta",
            "rich_text": {"equals": card_id}
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        results = response.json().get("results", [])
        return results[0] if results else None
    except Exception as e:
        print(f"Error obteniendo cliente: {e}")
        return None

def actualizar_visitas(cliente_id, nuevas_visitas):
    """Actualiza el contador de visitas"""
    url = f"https://api.notion.com/v1/pages/{cliente_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    payload = {
        "properties": {"Visitas": {"number": nuevas_visitas}}
    }
    
    try:
        requests.patch(url, headers=headers, json=payload)
        return True
    except Exception as e:
        print(f"Error actualizando visitas: {e}")
        return False

def crear_registro_visita(cliente_id):
    """Crea un registro de visita"""
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    payload = {
        "parent": {"database_id": VISITAS_DB_ID},
        "properties": {
            "Cliente": {"relation": [{"id": cliente_id}]},
            "Fecha": {"date": {"start": datetime.now().isoformat()}}
        }
    }
    
    try:
        requests.post(url, headers=headers, json=payload)
        return True
    except Exception as e:
        print(f"Error creando visita: {e}")
        return False

def registrar_visita(card_id):
    """Registra una visita en Notion"""
    cliente = obtener_cliente(card_id)
    if not cliente:
        return False
    
    visitas_actuales = cliente["properties"]["Visitas"]["number"] or 0
    if not actualizar_visitas(cliente["id"], visitas_actuales + 1):
        return False
    
    return crear_registro_visita(cliente["id"])

def mostrar_mensaje(titulo, mensaje, tipo="info"):
    """Muestra mensaje en pantalla"""
    try:
        img = Image.new('RGB', (800, 480), color='white')
        draw = ImageDraw.Draw(img)
        font_titulo = ImageFont.truetype(FONT_PATH, 32)
        font_texto = ImageFont.truetype(FONT_PATH, 24)
        
        color = "black"
        if tipo == "success":
            color = "green"
        elif tipo == "error":
            color = "red"
        
        draw.text((50, 50), titulo, fill=color, font=font_titulo)
        draw.text((50, 120), mensaje, fill="black", font=font_texto)
        
        img.save("/tmp/mensaje.png")
        os.system("pkill fbi; fbi -T 1 -t 2 -a /tmp/mensaje.png")
    except Exception as e:
        print(f"Error mostrando mensaje: {e}")

def leer_tarjeta_nfc():
    """Simula lectura de tarjeta NFC"""
    print("\nAcerca una tarjeta NFC al lector...")
    card_id = input("Ingresa ID de tarjeta: ").strip()
    
    # Simulación de diferentes estados de tarjeta
    registradas = ["A1B2C3D4", "E5F6G7H8"]
    nuevas = ["X9Y8Z7W6", "I1J2K3L4"]
    
    if card_id in registradas:
        return card_id, True
    elif card_id in nuevas:
        return card_id, False
    else:
        return card_id, None

def main():
    print("Sistema de Fidelidad NFC Iniciado")
    
    while True:
        card_id, registrada = leer_tarjeta_nfc()
        
        if registrada is None:
            beep_sound.play()
            mostrar_mensaje("ERROR", "Tarjeta no reconocida", "error")
            sleep(2)
            continue
        
        if registrada:
            # Tarjeta registrada - Registrar visita
            if registrar_visita(card_id):
                success_sound.play()
                mostrar_mensaje("BIENVENIDO", "¡Visita registrada!", "success")
            else:
                error_sound.play()
                mostrar_mensaje("ERROR", "Error en registro", "error")
        else:
            # Nueva tarjeta - Registrar cliente
            beep_sound.play()
            datos = mostrar_formulario(card_id)
            
            if datos and registrar_cliente(card_id, datos):
                success_sound.play()
                mostrar_mensaje("REGISTRADO", "Cliente registrado", "success")
            else:
                error_sound.play()
                mostrar_mensaje("ERROR", "Error en registro", "error")
        
        sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSistema detenido")
        sys.exit(0)