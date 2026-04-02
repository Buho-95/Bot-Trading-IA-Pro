# 🤖 Bot de Trading IA - Professional Edition

Una aplicación profesional de trading inteligente desarrollada con Streamlit, que utiliza machine learning para generar señales de trading y análisis técnico avanzado.

## 🚀 Características Principales

### 📊 Análisis de Mercado en Tiempo Real
- Conexión con Yahoo Finance para datos en tiempo real
- Soporte para criptomonedas (BTC, ETH, SOL) y acciones tecnológicas
- Indicadores técnicos: RSI, SMA 20/50, Volatilidad
- Análisis de tendencias y momentum

### 🤖 Inteligencia Artificial
- Modelo Random Forest para predicción de movimientos de precio
- Backtesting automático de estrategias
- Comparación de rendimiento: Bot IA vs Mercado (Hold)
- Métricas de precisión y estadísticas del modelo

### 💾 Base de Datos SQLite
- Historial completo de operaciones de trading
- Registro de datos de mercado y rendimiento
- Configuración persistente de usuario
- Gestión automática de datos antiguos

### 🎨 Interfaz Profesional
- Diseño moderno con CSS personalizado
- Gráficos interactivos con Plotly
- Navegación intuitiva entre secciones
- Temas personalizables y responsive design

## 📋 Estructura del Proyecto

```
📁 Trading IA/
├── 📄 app.py              # Aplicación principal
├── 📄 database.py         # Gestión de base de datos SQLite
├── 📄 utils.py            # Utilidades y funciones de trading
├── 📄 config.py           # Gestión de configuración
├── 📄 requirements.txt    # Dependencias del proyecto
└── 📄 README.md           # Documentación
```

## 🛠️ Instalación y Configuración

### Prerrequisitos
- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos de Instalación

1. **Clonar o descargar el proyecto**
   ```bash
   cd "c:\Users\USUARIO\Desktop\Traiding IA"
   ```

2. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

3. **Ejecutar la aplicación**
   ```bash
   streamlit run app.py
   ```

La aplicación se abrirá automáticamente en tu navegador web en `http://localhost:8501`

## 🎯 Uso de la Aplicación

### 1. Dashboard Principal
- **Métricas en tiempo real**: Precio actual, capital del bot, capital del mercado
- **Señales de trading**: Compra/Venta generadas por IA
- **Gráfico comparativo**: Rendimiento del bot vs mercado
- **Indicadores técnicos**: RSI, medias móviles, volatilidad

### 2. Análisis Técnico
- **Gráfico de precios interactivo** con medias móviles
- **Indicador RSI** con zonas de sobrecompra/sobreventa
- **Resumen de análisis**: Tendencia, momentum, volatilidad

### 3. Historial de Operaciones
- **Registro completo** de todas las operaciones ejecutadas
- **Tabla de operaciones** con detalles de precio, monto y estado
- **Estadísticas de rendimiento**: Retorno promedio, sesiones totales

### 4. Configuración
- **Parámetros de trading**: Símbolo por defecto, días de análisis, nivel de riesgo
- **Configuración de interfaz**: Auto-guardado, temas de gráficos
- **Gestión de base de datos**: Limpieza de datos, estadísticas

## 📊 Indicadores Técnicos Implementados

### RSI (Relative Strength Index)
- Período: 14
- Zonas: Sobrecompra (>70), Sobreventa (<30)
- Usado para identificar momentum y posibles reversiones

### SMA (Simple Moving Average)
- SMA 20: Tendencia a corto plazo
- SMA 50: Tendencia a mediano plazo
- Cruces de medias móviles como señales

### Volatilidad
- Calculada como desviación estándar de 20 períodos
- Usada para evaluar el riesgo del mercado

## 🤖 Modelo de Machine Learning

### Random Forest Classifier
- **100 estimadores** para robustez
- **Profundidad máxima: 7** para evitar overfitting
- **Features**: Precio OHLC, volumen, indicadores técnicos
- **Target**: Dirección del siguiente movimiento de precio

### Backtesting
- **Capital inicial**: $1,000
- **Estrategia**: Seguir señales del modelo
- **Comparación**: Buy and hold vs Bot IA
- **Métricas**: Retorno total, precisión, tasa de aciertos

## 💾 Base de Datos

### Tablas Principales

1. **trading_operations**: Historial de operaciones
2. **market_data**: Datos de mercado históricos
3. **bot_performance**: Métricas de rendimiento
4. **user_settings**: Configuración personalizada

### Gestión Automática
- Limpieza de datos antiguos (30 días por defecto)
- Backup automático de configuración
- Optimización de consultas

## 🔧 Personalización

### Agregar Nuevos Símbolos
Edita `config.py` en la función `get_available_symbols()`:
```python
def get_available_symbols():
    return [
        "BTC-USD", "ETH-USD", "SOL-USD",  # Existing
        "AAPL", "GOOGL", "MSFT",          # Existing
        "NUEVO-SIMBOLO"                   # Add your symbol
    ]
```

### Modificar Parámetros del Modelo
En `utils.py`, ajusta los parámetros del Random Forest:
```python
model = RandomForestClassifier(
    n_estimators=100,  # Adjust
    max_depth=7,       # Adjust
    random_state=42
)
```

### Personalizar Indicadores
Agrega nuevos indicadores en la función `calculate_indicators()` de `utils.py`.

## 🐛 Solución de Problemas

### Problemas Comunes

1. **Error de conexión a Yahoo Finance**
   - Verifica tu conexión a internet
   - Intenta con otro símbolo
   - Espera unos minutos y reintenta

2. **Error en la base de datos**
   - Elimina el archivo `trading_bot.db`
   - Reinicia la aplicación
   - Se creará una nueva base de datos automáticamente

3. **Gráficos no se muestran**
   - Actualiza la página (F5)
   - Limpia el caché del navegador
   - Verifica la consola de errores

### Registro de Errores
La aplicación incluye manejo de errores y mostrará mensajes descriptivos cuando ocurran problemas.

## 📈 Mejoras Futuras

- [ ] Integración con más exchanges (Binance, Coinbase)
- [ ] Notificaciones por email/Telegram
- [ ] Portfolio multi-activo
- [ ] Estrategias de trading avanzadas
- [ ] API REST para integración externa
- [ ] Modo paper trading con datos en vivo

## 📄 Licencia

Este proyecto es para fines educativos y de demostración. El trading real conlleva riesgos significativos.

## ⚠️ Descargo de Responsabilidad

Esta aplicación es para propósitos educativos y demostrativos. No constituye asesoramiento financiero. El trading de criptomonedas y acciones involucra riesgo sustancial y puede no ser adecuado para todos los inversores. Siempre realiza tu propia investigación (DYOR) antes de tomar decisiones de inversión.

## 📞 Soporte

Si encuentras algún problema o tienes sugerencias, por favor:
1. Revisa la sección de solución de problemas
2. Verifica que todas las dependencias estén instaladas
3. Reporta el issue con detalles del error

---

**Desarrollado con ❤️ usando Streamlit, Python y Machine Learning**
