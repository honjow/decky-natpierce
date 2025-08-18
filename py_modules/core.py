import asyncio
import os
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
        self.log_path = os.path.join(decky.DECKY_PLUGIN_LOG_DIR, "core.log")

    def _get_controller_port(self) -> int:
        port = self.settings.getSetting("controller_port")
        if port is None:
            port = 33272
        logger.debug(f"get_controller_port: {port}")
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
        # System environment check before starting
        await self._pre_start_check()
        
        await self._link_config()
        if self._process and self._process.returncode is None:
            logger.warning("core is already running")
            await self.stop()

        command = self._gen_cmd(self._get_controller_port())
        logger.info(f"starting core: {' '.join(command)}")
        self._command = command

        logger.debug(f"core log file: {self.log_path}")
        self._logfile = open(self.log_path, "w")

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

    async def _check_tun_module(self) -> None:
        """Check and handle TUN module"""
        try:
            # Check if TUN module exists (modinfo tun)
            proc = await asyncio.create_subprocess_exec(
                'modinfo', 'tun',
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                env=utils.env_fix()
            )
            returncode = await proc.wait()
            
            if returncode != 0:
                logger.error("TUN module does not exist in the system")
                raise RuntimeError("TUN module not found, please ensure kernel supports TUN/TAP")
            
            logger.info("TUN module exists in the system")
            
            # Check if TUN module is loaded (lsmod | grep -q "^tun ")
            proc = await asyncio.create_subprocess_shell(
                'lsmod | grep -q "^tun "',
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                env=utils.env_fix()
            )
            returncode = await proc.wait()
            
            if returncode == 0:
                logger.info("TUN module is already loaded")
                return
            
            # TUN module not loaded, try to load it (modprobe tun)
            logger.info("TUN module not loaded, attempting to load...")
            proc = await asyncio.create_subprocess_exec(
                'modprobe', 'tun',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=utils.env_fix()
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                logger.info("TUN module loaded successfully")
            else:
                error_msg = stderr.decode().strip() if stderr else "unknown error"
                logger.error(f"Failed to load TUN module: {error_msg}")
                raise RuntimeError(f"Cannot load TUN module, may need root privileges: {error_msg}")
                
        except Exception as e:
            logger.error(f"TUN module check failed: {e}")
            raise

    async def _check_ip_forward(self) -> None:
        """Check and enable IP forwarding"""
        try:
            # Read current IP forwarding status
            with open('/proc/sys/net/ipv4/ip_forward', 'r') as f:
                current_value = f.read().strip()
            
            if current_value == '1':
                logger.info("IP forwarding is already enabled")
                return
            
            # IP forwarding not enabled, try to enable it
            logger.info("IP forwarding not enabled, attempting to enable...")
            with open('/proc/sys/net/ipv4/ip_forward', 'w') as f:
                f.write('1')
            
            # Verify if successfully enabled
            with open('/proc/sys/net/ipv4/ip_forward', 'r') as f:
                new_value = f.read().strip()
            
            if new_value == '1':
                logger.info("IP forwarding enabled successfully")
            else:
                raise RuntimeError("Failed to enable IP forwarding, status verification failed")
                
        except PermissionError:
            logger.error("Root privileges required to enable IP forwarding")
            raise RuntimeError("Root privileges required to enable IP forwarding")
        except FileNotFoundError:
            logger.error("IP forwarding configuration file not found")
            raise RuntimeError("System does not support IP forwarding")
        except Exception as e:
            logger.error(f"IP forwarding check failed: {e}")
            raise RuntimeError(f"Cannot enable IP forwarding: {e}")

    async def _pre_start_check(self) -> None:
        """System environment check before starting"""
        logger.info("Starting system environment check...")
        
        try:
            # Execute checks in order
            await self._check_tun_module()
            await self._check_ip_forward()
            logger.info("System environment check completed, all checks passed")
            
        except Exception as e:
            logger.error(f"System environment check failed: {e}")
            raise RuntimeError(f"System environment does not meet requirements: {e}")

    async def get_version(self) -> str:
        """Get natpierce core version"""
        if self.is_running:
            return self._parse_version_from_log()
        elif os.path.exists(self.CORE_PATH):
            return self.settings.getSetting("core_version")
        else:
            return ""

    def _parse_version_from_log(self) -> str:
        """Parse version from log file (match lines starting with spaces)"""
        try:
            if not os.path.exists(self.log_path):
                return ""
            
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
            
            # Search from bottom to top for latest version info
            for line in reversed(lines):
                # Match version pattern in lines starting with spaces
                import re
                if re.match(r'^\s+', line):  # Line starts with spaces
                    match = re.search(r'V\d+\.\d+', line)
                    if match:
                        version = match.group().replace("V", "v")
                        logger.debug(f"Found version: {version}")
                        return version
            
            logger.warning("Version not found in log")
            return ""
            
        except Exception as e:
            logger.error(f"Failed to parse version from log: {e}")
            return ""