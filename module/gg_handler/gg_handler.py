from module.base.timer import timeout, Timer
from module.base.base import ModuleBase as Base
from module.gg_handler.gg_data import GGData
from module.gg_handler.gg_screenshot import GGScreenshot
from module.combat.combat import Combat
from module.logger import logger
from module.notify import handle_notify
from module.gg_handler.assets import OCR_PRE_BATTLE_CHECK
from module.combat.assets import BATTLE_PREPARATION
from module.ocr.ocr import Digit
from module.gg_handler.gg_task import *

OCR_CHECK = Digit(OCR_PRE_BATTLE_CHECK, name='OCR_PRE_BATTLE_CHECK', letter=(255, 255, 255), threshold=255)

class GGHandler(Base):
    """
    A module to handle needs of cheaters
    Args:
        config: AzurLaneConfig
        device: Device
    """

    def __init__(self, config, device):
        self.config = config
        self.device = device
        self.gg_data = GGData(self.config).get_data()
        self.gg_enable = GGData(self.config).get_data()['gg_enable']
        self.gg_auto = GGData(self.config).get_data()['gg_auto']
        self.gg_on = GGData(self.config).get_data()['gg_on']
        self.RestartEverytime = self.config.cross_get('GameManager.GGHandler.RestartEverytime', default=True)
        self.factor = self.config.cross_get('GameManager.GGHandler.GGMultiplyingFactor', default=200)
        self.method = self.config.cross_get('GameManager.GGHandler.GGMethod', default='screenshot')

    def restart(self, crashed=False):
        from module.handler.login import LoginHandler
        from module.exception import GameStuckError
        for _ in range(2):
            try:
                if not timeout(LoginHandler(self.config, self.device).app_restart, timeout_sec=600):
                    break
                raise RuntimeError
            except GameStuckError as e:
                pass
            except Exception as e:
                logger.exception(e)
                if crashed:
                    from module.notify import handle_notify
                    handle_notify(self.config.Error_OnePushConfig,
                                  title=f"Alas <{self.config.config_name}> 崩溃了",
                                  content=f"<{self.config.config_name}> 需要手动介入，也许你的模拟器卡死")
                    exit(1)
                crashed = True

    def set(self, mode=True):
        """
            Set the GG status to True/False.
            Args:
                mode: bool
        """
        if mode:
            logger.hr('Enabling GG', level=2)
            GGScreenshot(config=self.config, device=self.device).run(factor=self.factor)
        else:
            self.gg_reset()

    def skip_error(self):
        """
        Close all the windows of GG.
        Often to be used when game restarts with GG enabled.
        Returns:
            bool: Whether GG error panel occurs
        """
        GGScreenshot(config=self.config, device=self.device).skip_error()

    def check_config(self) -> dict:
        """
        Reset GG config to the user's config and return gg_data.
        Returns:
            gg_data: dict = {
                        'gg_enable' : bool = Whether GG manager enabled,
                        'gg_auto' : bool = Whether to start GG before tasks,
                        'gg_on' : bool = Whether multiplier is on now}
        """
        gg_enable = self.config.cross_get('GameManager.GGHandler.Enabled', default=False)
        gg_auto = self.config.cross_get('GameManager.GGHandler.GGFactorEnable', default=False)
        GGData(self.config).set_data(target='gg_enable', value=gg_enable)
        GGData(self.config).set_data(target='gg_auto', value=gg_auto)
        logger.hr('Check GG config')
        logger.info('GG config:')
        logger.info(
            f'[Enabled]{self.gg_enable} [AutoRestart]{self.gg_auto} [CurrentStage]{self.gg_on}')
        return self.gg_data

    def handle_restart_before_tasks(self) -> bool:
        """
        Check if user need to restart everytime alas starts before tasks, and handle it.
        Returns:
            bool: If it needs restart first
        """
        if self.RestartEverytime and self.gg_enable:
            logger.info('Restart to reset GG status.')
            self.restart()
            return True
        return False

    def handle_restart(self):
        """
        Handle the restart errors of GG.
        """
        if self.gg_enable:
            GGData(config=self.config).set_data(target='gg_on', value=False)
            logger.hr('Loading GG config')
            logger.info('GG config:')
            logger.info(
                f'[Enabled]{self.gg_enable} [AutoRestart]{self.gg_auto} [CurrentStage]{self.gg_on}')

    def gg_reset(self):
        """
        Force restart the game to reset GG status to False
        """
        if self.gg_enable and self.gg_on:
            logger.hr('Disabling GG', level=2)
            self.restart()
            logger.attr('GG', 'Disabled')

    def check_status(self, mode=True):
        """
        A check before a task begins to decide whether to enable GG and set it.
        Args:
            mode: The multiplier status when finish the check.
        """
        if self.gg_enable:
            gg_auto = mode if self.config.cross_get('GameManager.GGHandler.GGFactorEnable', default=False) else False
            logger.hr('Check GG status')
            logger.info(f'Check GG status:')
            logger.info(
                f'[Enabled]{self.gg_enable} [AutoRestart]{self.gg_auto} [CurrentStage]{self.gg_on}')
            if gg_auto:
                if not self.gg_on:
                    self.set(True)
            elif self.gg_on:
                self.gg_reset()

    def power_limit(self, task=''):
        """
        Forced final check before some dangerous tasks for cheaters.
        If power is too high, disable the multiplier and assume the user need GG to be Enabled before the other tasks.
        Args:
            task: str = What task it is to limit power, default limit is 16500 for front ships.
        """
        limit = self.config.cross_get(f'GameManager.PowerLimit.{task}', default=16500)
        lowlimit = self.config.cross_get(f'GameManager.GGHandler.GGLowLimit', default=500)
        logger.attr('Power Limit', limit)
        self.device.sleep(2)
        timeout = Timer(1, count=15).start()
        skip_first_screenshot = True
        ocr = 0
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.sleep((1, 1.5))
                self.device.screenshot()
            if Combat(config=self.config, device=self.device).handle_combat_automation_confirm():
                continue
            if timeout.reached():
                logger.error('Get ScoutCE timeout')
                handle_notify(self.config.Error_OnePushConfig,
                            title=f"Alas <{self.config.config_name}> 超时",
                            content=f"<{self.config.config_name}> 识别战力超时，模拟器卡死或者网络掉线")
                exit(1)
            if self.appear(BATTLE_PREPARATION, offset=(30, 20)):
                self.device.screenshot()
                ocr = OCR_CHECK.ocr(self.device.image)
            if ocr > lowlimit:
                break
        if ocr >= limit:
            for i in range(3):
                logger.critical('There\'s high chance that GG is on, restart to disable it')
            handle_notify(self.config.Error_OnePushConfig,
                              title=f"Alas <{self.config.config_name}> 超模战力",
                              content=f"<{self.config.config_name}> 识别到使用超模战力进行不被允许的任务，紧急重启规避检查")
            GGData(self.config).set_data(target='gg_on', value=False)
            GGData(self.config).set_data(target='gg_enable', value=True)
            self.config.cross_set('GameManager.GGHandler.Enabled', value=True)
            self.config.cross_set('GameManager.GGHandler.GGFactorEnable', value=True)
            return True

    def check_then_set_gg_status(self, task=''):
        """
        If task is in list _disabled or _group_enabled defined in this function,
        set gg to the defined status
        Args:
            task : str = the next task to run
        """
        _disabled_task = self.config.cross_get('GameManager.GGHandler.DisabledTask')
        """
            'disable_guild_and_dangerous'
            'disable_all_dangerous_task'
            'disable_meta_and_exercise'
            'disable_exercise'
            'enable_all'
        """

        _group_exercise = EXERCISE
        _group_meta = META
        _group_coalition = COALITION
        _group_raid = RAID
        _group_personal_choice = GUILD
        _group_enabled = MAINS + EVENTS + FARM + DAYIL + OPSI + OTHER

        # Handle ignorance

        if _disabled_task == 'disable_guild_and_dangerous':
            _disabled = _group_exercise + _group_meta + _group_raid + _group_coalition + _group_personal_choice
            _enabled = _group_enabled
        elif _disabled_task == 'disable_all_dangerous_task':
            _disabled = _group_exercise + _group_meta + _group_raid + _group_coalition
            _enabled = _group_enabled + _group_personal_choice
        elif _disabled_task == 'disable_meta_and_exercise':
            _disabled = _group_exercise + _group_meta
            _enabled = _group_enabled + _group_raid + _group_coalition + _group_personal_choice
        elif _disabled_task == 'disable_exercise':
            _disabled = _group_exercise
            _enabled = _group_enabled + _group_personal_choice + _group_raid + _group_coalition + _group_meta
        elif _disabled_task == 'enable_all':
            _disabled = []
            _enabled = _group_enabled + _group_personal_choice + _group_raid + _group_coalition + _group_meta + _group_exercise

        if task in _disabled:
            self.check_status(False)
        elif task in _enabled:
            self.check_status(True)
