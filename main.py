from typing import Any, Optional, Tuple
import decky
from core import CoreController
from setting import Settings
from decky import logger
from metadata import PACKAGE_NAME
import upgrade
import utils

import logging


class Plugin:
    async def _main(self):
        self.settings = Settings()
        logger.info(f"starting {PACKAGE_NAME} ...")

        self._set_default("timeout", 15.0)
        self._set_default("debounce_time", 10.0)
        self._set_default("autostart", False)
        self._set_default("controller_port", 33272)
        self._set_default("auto_check_update", True)
        self._set_default("disable_verify", False)
        self._set_default("core_version", "")
        self._set_default("log_level", logging.getLevelName(logging.INFO))

        level = self._get("log_level")
        logger.setLevel(logging.getLevelNamesMapping()[level])
        logger.info(f"log level set to {level}")

        utils.init_ssl_context(self._get("disable_verify"))

        self.core = CoreController()
        self.core.set_exit_callback(lambda x: decky.emit("core_exit", x))
        if self._get("autostart"):
            await self.core.start()

    async def _unload(self):
        if self.core.is_running:
            await self.core.stop()

    async def _uninstall(self):
        if self.core.is_running:
            await self.core.stop()

    async def get_core_status(self) -> bool:
        is_running = self.core.is_running
        logger.debug(f"get_core_status: {is_running}")
        return is_running

    async def set_core_status(self, status: bool) -> Tuple[bool, Optional[str]]:
        try:
            if status:
                await self.core.start()
            else:
                await self.core.stop()
        except Exception as e:
            logger.error(f"set_core_status: failed with {e}")
            return False, str(e)
        return True, None
    
    async def upgrade(self, res: str, version: str) -> Tuple[bool, Optional[str]]:
        if res not in upgrade.RESOURCE_TYPE_VALUES:
            logger.error(f"upgrade: invalid resource {res}")
            return False, "invalid resource"
        res_type = upgrade.ResourceType(res)
        try:
            await upgrade.upgrade(res_type, version)
        except Exception as e:
            logger.error(f"upgrade: failed with {e}")
            return False, str(e)
        return True, None
    
    async def cancel_upgrade(self, res: str) -> None:
        if res not in upgrade.RESOURCE_TYPE_VALUES:
            logger.error(f"cancel_upgrade: invalid resource {res}")
            return
        res_type = upgrade.ResourceType(res)
        upgrade.cancel_upgrade(res_type)

    async def get_config(self) -> dict:
        config = {
            "status": self.core.is_running,
            "autostart": self._get("autostart"),
            "controller_port": self._get("controller_port"),
        }
        logger.info(f"get_config: {config}")
        return config

    async def get_config_value(self, key: str):
        logger.info(f"get_config_value: {key}")
        value = self.settings.getSetting(key)
        logger.info(f"get_config_value: {key} => {value}")
        return value

    async def set_config_value(self, key: str, value: Any):
        self.settings.setSetting(key, value)
        logger.info(f"set_config_value: {key} => {value}")

    async def get_version(self, res: str) -> str:
        if res not in upgrade.RESOURCE_TYPE_VALUES:
            logger.error(f"get_version: invalid resource {res}")
            return ""
        res_type = upgrade.ResourceType(res)
        try:
            match res_type:
                case upgrade.ResourceType.PLUGIN:
                    version = decky.DECKY_PLUGIN_VERSION
                    if version[0].isdigit():
                        version = "v" + version
                case upgrade.ResourceType.CORE:
                    version = await self.core.get_version()
        except Exception as e:
            logger.error(f"get_version: {res} failed with {type(e)} {e}")
            return ""
        logger.debug(f"get_version: {res} {version}")
        return version

    async def get_latest_version(self, res: str) -> str:
        if res not in upgrade.RESOURCE_TYPE_VALUES:
            logger.error(f"get_latest_version: invalid resource {res}")
            return ""
        res_type = upgrade.ResourceType(res)
        try:
            version = await upgrade.get_latest_version(
                res_type, self._get("timeout"), self._get("debounce_time")
            )
        except Exception as e:
            logger.error(f"get_latest_version: failed with {e}")
            return ""
        logger.debug(f"get_latest_version: {res} {version}")
        return version
    
    async def get_ip(self) -> str:
        return utils.get_ip()

    def _get(self, key: str, allow_none: bool = False) -> Any:
        if allow_none:
            return self.settings.getSetting(key)
        else:
            value = self.settings.getSetting(key)
            if value is None:
                raise ValueError(f'Value of "{key}" is None')
            return value

    def _set_default(self, key: str, value: Any) -> None:
        if not self.settings.getSetting(key):
            self.settings.setSetting(key, value)

    # async def _migration(self):
    #     decky.logger.info("Migrating")
    #     decky.migrate_logs(os.path.join(decky.DECKY_USER_HOME,
    #                                            ".config", "decky-natpierce", "natpierce.log"))
    #     decky.migrate_settings(
    #         os.path.join(decky.DECKY_HOME, "settings", "natpierce.json"),
    #         os.path.join(decky.DECKY_USER_HOME, ".config", "decky-natpierce"))
    #     decky.migrate_runtime(
    #         os.path.join(decky.DECKY_HOME, "natpierce"),
    #         os.path.join(decky.DECKY_USER_HOME, ".local", "share", "decky-natpierce"))
