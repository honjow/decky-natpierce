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

    async def get_version(self) -> str:
        """获取natpierce核心版本号"""
        if self.is_running:
            logger.debug("核心正在运行，从日志解析版本号")
            return self._parse_version_from_log()
        else:
            logger.debug("核心未运行，临时启动获取版本号")
            return await self._get_version_by_temp_start()

    def _parse_version_from_log(self) -> str:
        """从日志文件解析版本号（匹配空格开头的行）"""
        try:
            if not os.path.exists(self.log_path):
                return ""
            
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
            
            # 从后往前搜索，找最新的版本信息
            for line in reversed(lines):
                # 匹配空格开头的行中的版本号模式
                import re
                if re.match(r'^\s+', line):  # 行以空格开头
                    match = re.search(r'V\d+\.\d+', line)
                    if match:
                        version = match.group().replace("V", "v")
                        logger.debug(f"找到版本号: {version}")
                        return version
            
            logger.warning("在日志中未找到版本号")
            return ""
            
        except Exception as e:
            logger.error(f"解析日志版本号失败: {e}")
            return ""

    async def _get_version_by_temp_start(self) -> str:
        """临时启动并实时监控，获取版本号后立即停止"""
        try:
            # 启动前清空日志文件，确保只读取本次启动的日志
            if os.path.exists(self.log_path):
                open(self.log_path, 'w').close()
            
            # 启动核心
            await self.start()
            
            # 实时监控日志，获取到版本号后立即停止
            version = self._monitor_log_for_version(timeout=10)
            
            # 立即停止
            await self.stop()
            
            return version
            
        except Exception as e:
            logger.error(f"临时启动获取版本号失败: {e}")
            # 确保清理
            if self.is_running:
                await self.stop()
            return ""

    def _monitor_log_for_version(self, timeout: int = 10) -> str:
        """实时监控日志文件，找到版本号后立即返回"""
        import time
        import re
        
        start_time = time.time()
        last_position = 0
        
        while time.time() - start_time < timeout:
            try:
                if os.path.exists(self.log_path):
                    with open(self.log_path, 'r') as f:
                        # 从上次读取位置开始读取
                        f.seek(last_position)
                        new_content = f.read()
                        last_position = f.tell()
                        
                        if new_content:
                            # 按行处理新内容
                            for line in new_content.split('\n'):
                                # 匹配空格开头的行中的版本号
                                if re.match(r'^\s+', line):
                                    match = re.search(r'V\d+\.\d+', line)
                                    if match:
                                        version = match.group().replace("V", "v")
                                        logger.debug(f"实时监控找到版本号: {version}")
                                        return version
                
                # 短暂等待后继续监控
                time.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"监控日志时出错: {e}")
                time.sleep(0.1)
        
        logger.warning(f"监控日志超时 ({timeout}秒)")
        return ""
