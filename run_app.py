#!/usr/bin/env python3
"""
Script simplificado para ejecutar la aplicación de trading
"""

import subprocess
import sys
import webbrowser
import time
from threading import Thread

def start_streamlit():
    """Inicia Streamlit en segundo plano"""
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", "8503",
            "--server.headless", "true"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error al iniciar Streamlit: {e}")

def open_browser():
    """Abre el navegador después de unos segundos"""
    time.sleep(8)  # Esperar a que Streamlit inicie
    webbrowser.open("http://localhost:8503")

if __name__ == "__main__":
    print("🚀 Iniciando Bot de Trading IA...")
    print("📊 La aplicación se abrirá en tu navegador en unos segundos...")
    
    # Iniciar Streamlit en un hilo separado
    streamlit_thread = Thread(target=start_streamlit, daemon=True)
    streamlit_thread.start()
    
    # Abrir navegador después de unos segundos
    browser_thread = Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    print("✅ Aplicación iniciada. Esperando conexión...")
    print("🌐 URL: http://localhost:8503")
    print("⏹️ Presiona Ctrl+C para detener la aplicación")
    
    try:
        # Mantener el script corriendo
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo la aplicación...")
        sys.exit(0)
