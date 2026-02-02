from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from functools import lru_cache
import yaml
from pathlib import Path
from typing import Dict, Any
import time

class Settings(BaseSettings):
    """Application configuration settings"""
    
    tenant_id: str = "default_tenant"
    issuer: str = "https://login.microsoftonline.com/default_tenant/v2.0"
    audience: str = "api://default"

    redis_url: str = "redis://localhost:6379"

    log_level: str = "INFO"
    environment: str = "dev"
    debug: bool = False

    default_rate_limit: int = 100
    rate_limit_window: int = 60  # in seconds
    rate_limit_window_seconds: int = 3600  # 1 hour
    rate_limit_algorithm: str = "sliding_window"  # sliding_window or token_bucket
    rate_limit_burst_size: int = 10

    models_config_path: str = "./config/models.yaml"
    
    # JWT settings
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # Server settings
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    
    # Application metadata
    APP_VERSION: str = "1.0.0"
    START_TIME: float = Field(default_factory=time.time)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

class ModelConfig:
    """Model configuration loader"""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load model configurations from YAML file"""
        if not self.config_path.exists():
            return {"models": {}, "rate_limits": {}, "access_control": {}}
        with open(self.config_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}
        
    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """Get configuration for a specific model"""
        return self._config.get("models", {}).get(model_name, {})
    
    def get_all_models(self) -> Dict[str, Any]:
        """Get all model configurations"""
        return self._config.get("models", {})

    def get_rate_limits(self, model_name: str, group_id: str = None) -> int:
        """Get rate limit configurations"""
        rate_limits = self._config.get("rate_limits", {})
        if group_id:
            group_limits = rate_limits.get("by_group", {})
            if group_id in group_limits:
                return group_limits[group_id]
            
        model_config = self.get_model_config(model_name)
        if "rate_limit" in model_config:
            return model_config["rate_limit"]
        
        return rate_limits.get("default", 100)
    
    def get_access_control(self, model_name: str) -> Dict[str, Any]:
        """Get access control settings for a model"""
        access_control = self._config.get("access_control", {})
        return access_control.get(model_name, {})
    
    def reload(self):
        """Reload configuration from file"""
        self._config = self._load_config()

@lru_cache()
def get_model_config() -> ModelConfig:
    """Get cached ModelConfig instance"""
    settings = get_settings()
    return ModelConfig(settings.models_config_path)