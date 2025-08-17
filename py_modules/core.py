import asyncio
import os
from pathlib import Path
from pdb import post_mortem
import subprocess
from typing import Awaitable, Callable, Optional, List

import decky
from decky import logger
import utils
from setting import Settings

ExitCallback = Callable[[Optional[int]], Awaitable[None]]


class CoreController:
    CORE_PATH = os.path.join(decky.DECKY_PLUGIN_DIR, "bin", "natpierce")
    CONFIG_PATH = os.path.join(decky.DECKY_PLUGIN_DIR, "bin", "data", "config")
    DECKY_CONFIG_PATH = os.path.join(
        decky.DECKY_PLUGIN_SETTINGS_DIR, "natpierce_config"
    )
    RESOURCE_DIR = decky.DECKY_PLUGIN_RUNTIME_DIR

    def __init__(self):
        self.settings = Settings()

        self._process: Optional[asyncio.subprocess.Process] = None
        self._command: List[str] = []
        self._exit_callback: Optional[ExitCallback] = None
        self._monitor_task: Optional[asyncio.Task] = None

    def _get_controller_port(self) -> int:
        port = self.settings.getSetting("controller_port")
        if port is None:
            port = 33272
        logger.info(f"get_controller_port: {port}")
        return int(port)

    @property
    def is_running(self) -> bool:
        if not self._process:
            return False
        if self._process.returncode is None:
            return True
        return False

    @classmethod
    def _gen_cmd(cls, port: int) -> List[str]:
        return [
            cls.CORE_PATH,
            "-p",
            str(port),
        ]

    async def _link_config(self) -> None:
        try:
            CONFIG_DIR = os.path.dirname(self.CONFIG_PATH)
            if not os.path.exists(CONFIG_DIR):
                os.makedirs(CONFIG_DIR, exist_ok=True)
            if os.path.exists(self.CONFIG_PATH):
                os.remove(self.CONFIG_PATH)
            os.symlink(self.DECKY_CONFIG_PATH, self.CONFIG_PATH)
        except Exception as e:
            logger.error(f"failed to link config: {e}", exc_info=True)
            raise

    async def start(self) -> None:
        await self._link_config()
        if self._process and self._process.returncode is None:
            logger.warning("core is already running")
            await self.stop()

        command = self._gen_cmd(self._get_controller_port())
        logger.info(f"starting core: {' '.join(command)}")
        self._command = command

        log_path = os.path.join(decky.DECKY_PLUGIN_LOG_DIR, "core.log")
        logger.info(f"core log file: {log_path}")
        self._logfile = open(log_path, "w")

        try:
            self._process = await asyncio.create_subprocess_exec(
                *command,
                stdout=self._logfile,
                stderr=self._logfile,
                env=utils.env_fix(),
            )
            logger.debug(f"core pid: {self._process.pid}")
            self._monitor_task = asyncio.create_task(self._monitor_exit())
        except Exception as e:
            logger.error(f"failed to start core: {str(e)}")
            self._logfile.close()
            self._logfile = None
            raise

    async def stop(self) -> None:
        if not self._process or self._process.returncode is not None:
            raise RuntimeError("No running core")

        logger.info(f"terminating core (PID: {self._process.pid})")
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            self._monitor_task = None
        try:
            self._process.terminate()
        except Exception as e:
            logger.error(f"failed to terminate core with error: {e}")
        finally:
            self._process = None
            logger.debug("core terminated")
            if self._logfile:
                self._logfile.close()
                self._logfile = None

    async def _monitor_exit(self):
        assert self._process is not None
        returncode = await self._process.wait()
        logger.debug(f"core exited with code: {returncode}")

        if self._exit_callback is not None:
            try:
                await self._exit_callback(returncode)
            except Exception as e:
                logger.error(f"error in exit callback: {str(e)}")

    def set_exit_callback(self, callback: Optional[ExitCallback]):
        self._exit_callback = callback

    @classmethod
    def get_version(cls) -> str:
        try:
            cmd = [cls.CORE_PATH, "-v"]
            logger.debug(f"get_version: cmd: {' '.join(cmd)}")
            output = subprocess.check_output(cmd)
        except Exception as e:
            logger.error(f"get_version: failed to start core: {str(e)}")
            return ""

        logger.debug(f"get_version: output: {output}")
        for s in output.decode().split(" "):
            if s.startswith("v"):
                return s.strip()
        return ""
