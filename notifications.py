"""
Telegram Notifications Module for Trading Bot
Handles all communication with Telegram Bot API
"""

import requests
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import os
import json
from pathlib import Path

logger = logging.getLogger(__name__)

def load_env_from_file(env_file: str = "tokenTel.env"):
    """Load environment variables from custom env file"""
    env_path = Path(env_file)
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        logger.info(f"✅ Loaded environment variables from {env_file}")
    else:
        logger.warning(f"⚠️ Environment file {env_file} not found")

# Load environment variables at module import
load_env_from_file()

class TelegramNotifier:
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize Telegram Notifier
        
        Args:
            bot_token: Telegram bot token (can be set via environment variable TELEGRAM_BOT_TOKEN)
            chat_id: Telegram chat ID (can be set via environment variable TELEGRAM_CHAT_ID)
        """
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        # Validate configuration
        if not self.bot_token or not self.chat_id:
            logger.warning("⚠️ Telegram credentials not configured. Notifications will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            self.test_connection()
    
    def test_connection(self):
        """Test Telegram bot connection"""
        if not self.enabled:
            return False
        
        try:
            response = requests.get(f"{self.base_url}/getMe")
            if response.status_code == 200:
                bot_info = response.json()
                logger.info(f"✅ Telegram bot connected: @{bot_info['result']['username']}")
                return True
            else:
                logger.error(f"❌ Telegram bot connection failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Telegram connection error: {str(e)}")
            return False
    
    def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """
        Send message to Telegram
        
        Args:
            message: Message text to send
            parse_mode: Parse mode (Markdown or HTML)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.warning("Telegram notifications disabled - skipping message")
            return False
        
        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': False
            }
            
            response = requests.post(f"{self.base_url}/sendMessage", json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Telegram message sent successfully")
                return True
            else:
                logger.error(f"❌ Failed to send Telegram message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending Telegram message: {str(e)}")
            return False
    
    def send_notification(self, message: str) -> bool:
        """Send general notification"""
        return self.send_message(f"🤖 **Trading Bot Notification**\n\n{message}")
    
    def send_error_notification(self, error_message: str) -> bool:
        """Send error notification"""
        return self.send_message(f"🚨 **Trading Bot Error**\n\n❌ {error_message}")
    
    def send_trading_signal(self, decision: Dict) -> bool:
        """
        Send trading signal notification
        
        Args:
            decision: Trading decision dictionary with all relevant data
        """
        if not self.enabled:
            return False
        
        # Determine emoji for signal
        signal_emoji = "🟢" if decision['signal'] == 'BUY' else "🔴"
        
        # Format confidence
        confidence_pct = decision['confidence'] * 100
        
        # Format Kelly recommendation
        kelly_pct = decision.get('kelly_fraction', 0) * 100
        investment = decision.get('suggested_investment', 0)
        
        # Create message
        message = f"""
{signal_emoji} Alerta de Senal de Trading

📊 Simbolo: {decision['symbol']}
💰 Senal: {decision['signal']}
💵 Precio: ${decision['price']:.2f}
🎯 Confianza: {confidence_pct:.1f}%

📈 Tamano de Posicion (Criterio Kelly):
• Recomendado: ${investment:.2f}
• Fraccion: {kelly_pct:.1f}%
• Nivel de Riesgo: {decision.get('risk_level', 'Desconocido')}

🛡️ Gestion de Riesgo:
• Stop Loss: ${decision.get('stop_loss', 'N/A'):.2f}
• Take Profit: ${decision.get('take_profit', 'N/A'):.2f}
• ATR: {decision.get('atr', 0):.4f}

🧠 Sentimiento del Mercado: {decision.get('fear_greed_index', 50)}
📊 Precision del Modelo: {decision.get('model_accuracy', 0):.1f}%
⏰ Hora: {decision['timestamp'].strftime('%H:%M:%S')}
        """
        
        return self.send_message(message)
    
    def send_daily_summary(self, summary_data: Dict) -> bool:
        """
        Send daily performance summary
        
        Args:
            summary_data: Dictionary with daily performance metrics
        """
        if not self.enabled:
            return False
        
        message = f"""
📊 **Daily Trading Summary** - {datetime.now().strftime('%Y-%m-%d')}

🤖 **Performance Metrics:**
• **Total Return:** {summary_data.get('total_return', 0):.2%}
• **Win Rate:** {summary_data.get('win_rate', 0):.1f}%
• **Total Trades:** {summary_data.get('total_trades', 0)}
• **Profitable Trades:** {summary_data.get('profitable_trades', 0)}

💰 **Portfolio:**
• **Current Capital:** ${summary_data.get('current_capital', 0):,.2f}
• **Initial Capital:** ${summary_data.get('initial_capital', 0):,.2f}
• **Daily P&L:** ${summary_data.get('daily_pnl', 0):,.2f}

📈 **Strategy:**
• **Model:** {summary_data.get('strategy', 'RandomForest')}
• **Last Retraining:** {summary_data.get('last_retraining', 'Never')}
• **Active Symbols:** {summary_data.get('active_symbols', 0)}

⏰ **Next Update:** {(datetime.now().replace(hour=8, minute=0, second=0) + timedelta(days=1)).strftime('%Y-%m-%d %H:%M')}
        """
        
        return self.send_message(message)
    
    def send_model_retraining_notification(self, retraining_data: Dict) -> bool:
        """
        Send model retraining notification
        
        Args:
            retraining_data: Dictionary with retraining results
        """
        if not self.enabled:
            return False
        
        message = f"""
🔄 Reentrenamiento del Modelo Completado

📊 Resumen del Reentrenamiento:
• Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Duración: {retraining_data.get('duration', 'Desconocido')}
• Puntos de Datos: {retraining_data.get('data_points', 'Desconocido')}

🎯 Nuevo Rendimiento:
• Precisión: {retraining_data.get('accuracy', 0):.1%}
• Mejores Parámetros: {retraining_data.get('best_params', 'Predeterminado')}
• Puntuación Cross-Validation: {retraining_data.get('cv_score', 0):.1%}

📈 Mejora:
• Precisión Anterior: {retraining_data.get('previous_accuracy', 0):.1%}
• Mejora: {retraining_data.get('improvement', 0):.2%}
• Estado: {'✅ Mejorado' if retraining_data.get('improvement', 0) > 0 else '⚠️ Sin Mejora'}

🔄 Próximo Reentrenamiento: {(datetime.now() + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M')}
        """
        
        return self.send_message(message)
    
    def send_startup_notification(self) -> bool:
        """Send bot startup notification"""
        message = f"""
🚀 Bot de Trading Iniciado

🤖 Estado del Bot: En línea y Funcionando
⏰ Hora de Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔄 Modo: Permanente Autónomo
📊 Frecuencia de Actualización: Cada 5 minutos
🔄 Reentrenamiento: Cada 24 horas

📈 Símbolos Monitoreados:
• BTC-USD
• ETH-USD  
• SOL-USD

✅ Todos los sistemas operativos
        """
        
        return self.send_message(message)
    
    def send_shutdown_notification(self) -> bool:
        """Send bot shutdown notification"""
        message = f"""
⏹️ Bot de Trading Detenido

🤖 Estado del Bot: Desconectado
⏰ Hora de Detención: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📊 Sesión Finalizada

� Próximo Inicio: Programado automático
        """
        
        return self.send_message(message)
    
    def send_risk_alert(self, alert_data: Dict) -> bool:
        """
        Send risk management alert
        
        Args:
            alert_data: Dictionary with alert information
        """
        if not self.enabled:
            return False
        
        alert_type = alert_data.get('type', 'Unknown')
        severity = alert_data.get('severity', 'Medium')
        
        severity_emoji = {
            'Low': '🟡',
            'Medium': '🟠', 
            'High': '🔴',
            'Critical': '🚨'
        }.get(severity, '⚠️')
        
        message = f"""
{severity_emoji} Alerta de Gestión de Riesgo

⚠️ Tipo de Alerta: {alert_type}
📊 Severidad: {severity}
🕐 Hora: {datetime.now().strftime('%H:%M:%S')}

📈 Detalles:
{alert_data.get('details', 'No hay detalles adicionales disponibles')}

🎯 Acción Recomendada:
{alert_data.get('recommendation', 'Monitorear de cerca')}
        """
        
        return self.send_message(message)
    
    def send_portfolio_update(self, portfolio_data: Dict) -> bool:
        """
        Send portfolio update notification
        
        Args:
            portfolio_data: Dictionary with portfolio information
        """
        if not self.enabled:
            return False
        
        total_value = portfolio_data.get('total_value', 0)
        daily_change = portfolio_data.get('daily_change', 0)
        daily_change_pct = portfolio_data.get('daily_change_pct', 0)
        
        # Determine emoji for performance
        if daily_change_pct > 2:
            emoji = "🚀"
        elif daily_change_pct > 0:
            emoji = "📈"
        elif daily_change_pct > -2:
            emoji = "📊"
        else:
            emoji = "📉"
        
        message = f"""
{emoji} Actualización de Portafolio

💰 Valor Total: ${total_value:,.2f}
📊 Cambio Diario: ${daily_change:+,.2f} ({daily_change_pct:+.2f}%)

📈 Posiciones:
{portfolio_data.get('positions_summary', 'No hay posiciones activas')}

🎯 Rendimiento:
• Retorno Semanal: {portfolio_data.get('weekly_return', 0):.2%}
• Retorno Mensual: {portfolio_data.get('monthly_return', 0):.2%}
• Retorno YTD: {portfolio_data.get('ytd_return', 0):.2%}

⏰ Última Actualización: {datetime.now().strftime('%H:%M:%S')}
        """
        
        return self.send_message(message)

# Configuration helper
def setup_telegram_config():
    """
    Helper function to guide users through Telegram setup
    """
    print("""
🤖 **Telegram Bot Setup Guide**

1. **Create a Telegram Bot:**
   • Open Telegram and search for @BotFather
   • Send /newbot command
   • Choose a name (e.g., "My Trading Bot")
   • Choose a username (must end with 'bot')
   • Copy the bot token

2. **Get Your Chat ID:**
   • Start a conversation with your bot
   • Send any message
   • Visit: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   • Find your chat_id in the response (usually a large number)

3. **Set Environment Variables:**
   • Windows: set TELEGRAM_BOT_TOKEN=your_token
   • Windows: set TELEGRAM_CHAT_ID=your_chat_id
   • Or add them to your .env file

4. **Test Connection:**
   • Run: python -c "from notifications import TelegramNotifier; TelegramNotifier().test_connection()"

✅ Once configured, your bot will send real-time notifications!
    """)

# Example usage
if __name__ == "__main__":
    # Test the notifier
    notifier = TelegramNotifier()
    
    if notifier.enabled:
        notifier.send_notification("🧪 Test notification from Trading Bot")
        print("✅ Test notification sent!")
    else:
        print("❌ Telegram not configured. Run setup_telegram_config() for help.")
