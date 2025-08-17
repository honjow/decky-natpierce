from typing import Any
import decky
from decky import logger
from settings import SettingsManager


class Settings:
    def __init__(self):
        self.settings = SettingsManager(
            name="config", settings_directory=decky.DECKY_PLUGIN_SETTINGS_DIR
        )

    def getSetting(self, key: str) -> Any:
        value = self.settings.getSetting(key)
        logger.debug(f"getSetting: {key} => {value}")
        return value
    
    def setSetting(self, key: str, value: Any) -> None:
        logger.debug(f"setSetting: {key} => {value}")
        self.settings.setSetting(key, value)
