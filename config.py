import streamlit as st
from database import TradingDatabase

class ConfigManager:
    def __init__(self, db: TradingDatabase):
        self.db = db
        self.default_settings = {
            'default_symbol': 'BTC-USD',
            'default_days': 30,
            'risk_level': 'medium',
            'auto_save': 'true',
            'chart_theme': 'dark',
            'notification_enabled': 'false'
        }
    
    def get_setting(self, setting_name: str) -> str:
        """Get user setting with fallback to default"""
        value = self.db.get_user_setting(setting_name)
        if value is None:
            value = self.default_settings.get(setting_name, '')
        return value
    
    def set_setting(self, setting_name: str, setting_value: str):
        """Set user setting"""
        self.db.save_user_setting(setting_name, setting_value)
    
    def get_all_settings(self) -> dict:
        """Get all user settings"""
        settings = {}
        for key in self.default_settings.keys():
            settings[key] = self.get_setting(key)
        return settings
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        for key, value in self.default_settings.items():
            self.set_setting(key, value)

def init_session_state():
    """Initialize Streamlit session state variables"""
    if 'current_symbol' not in st.session_state:
        st.session_state.current_symbol = 'BTC-USD'
    if 'current_days' not in st.session_state:
        st.session_state.current_days = 30
    if 'last_update' not in st.session_state:
        st.session_state.last_update = None
    if 'show_history' not in st.session_state:
        st.session_state.show_history = False
    if 'page' not in st.session_state:
        st.session_state.page = 'dashboard'

def get_available_symbols():
    """Get list of available trading symbols"""
    return [
        "BTC-USD", "ETH-USD", "SOL-USD",  # Cryptocurrencies
        "AAPL", "GOOGL", "MSFT", "AMZN",  # Tech stocks
        "TSLA", "META", "NVDA", "AMD"     # More tech stocks
    ]

def get_risk_levels():
    """Get available risk levels"""
    return [
        ("low", "Bajo Riesgo"),
        ("medium", "Riesgo Medio"),
        ("high", "Alto Riesgo")
    ]

def get_chart_themes():
    """Get available chart themes"""
    return [
        ("dark", "Oscuro"),
        ("light", "Claro"),
        ("plotly_dark", "Plotly Oscuro")
    ]
