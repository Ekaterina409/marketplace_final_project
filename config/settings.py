import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

class Settings:
    """Класс для хранения настроек проекта"""
    
    # API настройки
    API_URL = os.getenv("MARKETPLACE_API_URL")
    
    # Настройки базы данных
    DB_CONFIG = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "database": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD")
    }
    
    @property
    def db_url(self):
        """Возвращает URL подключения к БД для SQLAlchemy"""
        return (
            f"postgresql://{self.DB_CONFIG['user']}:{self.DB_CONFIG['password']}"
            f"@{self.DB_CONFIG['host']}:{self.DB_CONFIG['port']}/{self.DB_CONFIG['database']}"
        )

# Создаём глобальный экземпляр настроек
settings = Settings()