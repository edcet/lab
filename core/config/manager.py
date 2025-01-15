"""Configuration Management System with validation and dynamic updates"""

import asyncio
from typing import Dict, Any, Optional, List, Set, Union
from datetime import datetime
import logging
from dataclasses import dataclass
import json
from pathlib import Path
import yaml
from pydantic import BaseModel, validator
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration Models
class ModelConfig(BaseModel):
    """Model configuration validation"""
    name: str
    endpoint: str
    capabilities: List[str]
    max_tokens: int
    temperature: float = 0.1
    top_p: float = 0.9
    batch_size: Optional[int] = None
    priority: int = 1
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Temperature must be between 0 and 1')
        return v
    
    @validator('top_p')
    def validate_top_p(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Top_p must be between 0 and 1')
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        if not 1 <= v <= 10:
            raise ValueError('Priority must be between 1 and 10')
        return v

class ToolConfig(BaseModel):
    """Tool configuration validation"""
    name: str
    capabilities: List[str]
    auto_approve: bool = False
    max_retries: int = 3
    timeout: int = 300
    priority: int = 1
    
    @validator('max_retries')
    def validate_max_retries(cls, v):
        if not 0 <= v <= 10:
            raise ValueError('Max retries must be between 0 and 10')
        return v
    
    @validator('timeout')
    def validate_timeout(cls, v):
        if not 0 <= v <= 3600:
            raise ValueError('Timeout must be between 0 and 3600 seconds')
        return v

class SystemConfig(BaseModel):
    """System-wide configuration validation"""
    version: str
    max_parallel_tasks: int = 8
    memory_limit_gb: float = 32.0
    snapshot_interval: int = 60
    log_level: str = "INFO"
    metrics_enabled: bool = True
    
    @validator('max_parallel_tasks')
    def validate_max_parallel(cls, v):
        if not 1 <= v <= 32:
            raise ValueError('Max parallel tasks must be between 1 and 32')
        return v
    
    @validator('memory_limit_gb')
    def validate_memory_limit(cls, v):
        if not 1 <= v <= 128:
            raise ValueError('Memory limit must be between 1 and 128 GB')
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}')
        return v

class ConfigurationManager:
    """Manages system configuration with validation and hot reloading"""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self.config: Dict[str, Any] = {}
        self.validators = {
            'model': ModelConfig,
            'tool': ToolConfig,
            'system': SystemConfig
        }
        self.subscribers: Dict[str, Set[callable]] = {
            'model': set(),
            'tool': set(),
            'system': set()
        }
        self.observer = Observer()
        self.watch_handler = ConfigFileHandler(self._handle_config_change)
        self._lock = asyncio.Lock()

    async def initialize(self) -> bool:
        """Initialize configuration management"""
        try:
            # Create config directory if needed
            self.config_path.mkdir(parents=True, exist_ok=True)
            
            # Load all configurations
            await self._load_all_configs()
            
            # Start file watching
            self.observer.schedule(
                self.watch_handler,
                str(self.config_path),
                recursive=False
            )
            self.observer.start()
            
            self.logger.info("Configuration Manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration initialization failed: {e}")
            return False

    async def _load_all_configs(self):
        """Load all configuration files"""
        async with self._lock:
            # Load system config
            system_config = await self._load_config_file('system.yml')
            if system_config:
                self.config['system'] = self._validate_config(
                    'system',
                    system_config
                )
            
            # Load model configs
            model_config = await self._load_config_file('models.yml')
            if model_config:
                self.config['models'] = {
                    name: self._validate_config('model', cfg)
                    for name, cfg in model_config.items()
                }
            
            # Load tool configs
            tool_config = await self._load_config_file('tools.yml')
            if tool_config:
                self.config['tools'] = {
                    name: self._validate_config('tool', cfg)
                    for name, cfg in tool_config.items()
                }

    async def _load_config_file(self, filename: str) -> Optional[Dict]:
        """Load and parse configuration file"""
        try:
            file_path = self.config_path / filename
            if not file_path.exists():
                return None
            
            with open(file_path) as f:
                return yaml.safe_load(f)
                
        except Exception as e:
            self.logger.error(f"Error loading config file {filename}: {e}")
            return None

    def _validate_config(self, 
                      config_type: str, 
                      config: Dict) -> Dict:
        """Validate configuration against schema"""
        validator = self.validators.get(config_type)
        if not validator:
            raise ValueError(f"Unknown config type: {config_type}")
            
        # Validate through pydantic model
        validated = validator(**config)
        return validated.dict()

    def subscribe(self, 
               config_type: str, 
               callback: callable):
        """Subscribe to configuration changes"""
        if config_type not in self.subscribers:
            raise ValueError(f"Unknown config type: {config_type}")
        self.subscribers[config_type].add(callback)

    def unsubscribe(self, 
                 config_type: str, 
                 callback: callable):
        """Unsubscribe from configuration changes"""
        if config_type in self.subscribers:
            self.subscribers[config_type].discard(callback)

    async def _handle_config_change(self, 
                                 filename: str):
        """Handle configuration file changes"""
        try:
            # Determine config type
            config_type = filename.split('.')[0]
            
            # Reload configuration
            new_config = await self._load_config_file(filename)
            if not new_config:
                return
            
            # Validate new configuration
            if config_type in ['models', 'tools']:
                validated_config = {
                    name: self._validate_config(config_type.rstrip('s'), cfg)
                    for name, cfg in new_config.items()
                }
            else:
                validated_config = self._validate_config(
                    config_type,
                    new_config
                )
            
            # Update configuration
            async with self._lock:
                self.config[config_type] = validated_config
            
            # Notify subscribers
            await self._notify_subscribers(config_type, validated_config)
            
        except Exception as e:
            self.logger.error(f"Error handling config change: {e}")

    async def _notify_subscribers(self, 
                               config_type: str, 
                               new_config: Dict):
        """Notify subscribers of configuration changes"""
        for callback in self.subscribers.get(config_type, set()):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(new_config)
                else:
                    callback(new_config)
            except Exception as e:
                self.logger.error(f"Error in config change callback: {e}")

    def get_config(self, 
                config_type: str, 
                name: Optional[str] = None) -> Dict:
        """Get configuration"""
        if config_type not in self.config:
            raise ValueError(f"Unknown config type: {config_type}")
            
        if name:
            if name not in self.config[config_type]:
                raise ValueError(f"Unknown {config_type} config: {name}")
            return self.config[config_type][name]
        
        return self.config[config_type]

    async def update_config(self, 
                         config_type: str,
                         updates: Dict,
                         name: Optional[str] = None):
        """Update configuration"""
        async with self._lock:
            if name:
                # Update specific named configuration
                current = self.config[config_type].get(name, {})
                updated = {**current, **updates}
                validated = self._validate_config(
                    config_type.rstrip('s'),
                    updated
                )
                self.config[config_type][name] = validated
            else:
                # Update entire configuration section
                current = self.config[config_type]
                updated = {**current, **updates}
                validated = self._validate_config(config_type, updated)
                self.config[config_type] = validated
            
            # Save to file
            await self._save_config(config_type, name)
            
            # Notify subscribers
            await self._notify_subscribers(
                config_type,
                validated if name else self.config[config_type]
            )

    async def _save_config(self, 
                        config_type: str,
                        name: Optional[str] = None):
        """Save configuration to file"""
        try:
            filename = f"{config_type}.yml"
            file_path = self.config_path / filename
            
            with open(file_path, 'w') as f:
                yaml.safe_dump(
                    self.config[config_type],
                    f,
                    default_flow_style=False
                )
                
        except Exception as e:
            self.logger.error(f"Error saving config file: {e}")
            raise

    async def cleanup(self):
        """Cleanup configuration management"""
        try:
            # Stop file watching
            self.observer.stop()
            self.observer.join()
            
            # Clear subscribers
            for subscribers in self.subscribers.values():
                subscribers.clear()
            
            self.logger.info("Configuration Manager cleanup completed")
        except Exception as e:
            self.logger.error(f"Configuration cleanup error: {e}")
            raise

class ConfigFileHandler(FileSystemEventHandler):
    """Handles configuration file changes"""
    
    def __init__(self, callback):
        self.callback = callback
        super().__init__()

    def on_modified(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('.yml'):
            asyncio.create_task(
                self.callback(Path(event.src_path).name)
            )
