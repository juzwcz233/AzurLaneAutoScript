from module.log_res import LogRes
from module.logger import logger
from module.ocr.ocr import Ocr, Digit
from module.base.timer import Timer
from module.base.utils import *
from module.gacha.ui import GachaUI
from module.shop.ui import ShopUI
from module.config.utils import deep_get
from module.ui.page import page_campaign_menu, page_raid
from module.ui.assets import CAMPAIGN_MENU_NO_EVENT
from module.campaign.assets import OCR_EVENT_PT, OCR_COIN, OCR_OIL, OCR_COIN_LIMIT, OCR_OIL_LIMIT
from module.shop.assets import SHOP_GEMS, SHOP_MEDAL, SHOP_MERIT, SHOP_GUILD_COINS, SHOP_CORE
from module.gacha.assets import BUILD_CUBE_COUNT
from module.raid.raid import pt_ocr

OCR_OIL = Digit(OCR_OIL, name='OCR_OIL', letter=(247, 247, 247), threshold=128)
OCR_COIN = Digit(OCR_COIN, name='OCR_COIN', letter=(239, 239, 239), threshold=128)
OCR_OIL_LIMIT = Digit(OCR_OIL_LIMIT, name='OCR_OIL_LIMIT', letter=(235, 235, 235), threshold=128)
OCR_COIN_LIMIT = Digit(OCR_COIN_LIMIT, name='OCR_COIN_LIMIT', letter=(239, 239, 239), threshold=128)
OCR_SHOP_GEMS = Digit(SHOP_GEMS, letter=(255, 243, 82), name='OCR_SHOP_GEMS')
OCR_BUILD_CUBE_COUNT = Digit(BUILD_CUBE_COUNT, letter=(255, 247, 247), threshold=64)
OCR_SHOP_MEDAL = Digit(SHOP_MEDAL, letter=(239, 239, 239), name='OCR_SHOP_MEDAL')
OCR_SHOP_MERIT = Digit(SHOP_MERIT, letter=(239, 239, 239), name='OCR_SHOP_MERIT')
OCR_SHOP_GUILD_COINS = Digit(SHOP_GUILD_COINS, letter=(255, 255, 255), name='OCR_SHOP_GUILD_COINS')
OCR_SHOP_CORE = Digit(SHOP_CORE, letter=(239, 239, 239), name='OCR_SHOP_CORE')

class PtOcr(Ocr):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, lang='azur_lane', alphabet='X0123456789', **kwargs)

    def pre_process(self, image):
        """
        Args:
            image (np.ndarray): Shape (height, width, channel)

        Returns:
            np.ndarray: Shape (width, height)
        """
        # Use MAX(r, g, b)
        r, g, b = cv2.split(cv2.subtract((255, 255, 255, 0), image))
        image = cv2.min(cv2.min(r, g), b)
        # Remove background, 0-192 => 0-255
        image = cv2.multiply(image, 255 / 192)

        return image.astype(np.uint8)

OCR_PT = PtOcr(OCR_EVENT_PT)


class DashboardUpdate(ShopUI, GachaUI):
    def dashboard_run(self):
        option = deep_get(self.config.data, 'DashboardUpdate.DashboardUpdate.Update')
        if option=="main":
            self.get_main()
            self.get_cube()
        elif option=="all":
            self.get_main()
            self.get_cube()
            self.goto_shop()
            self.get_pt()
            self.ui_goto_main()
        logger.info('Update Dashboard Data Finished')

    def get_main(self, skip_first_screenshot=True):
        self.ui_goto_main()
        _oil = {}
        _coin = {}
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()
            
            logger.hr('Get Oil')
            _oil = {
                'Value': OCR_OIL.ocr(self.device.image),
                'Limit': OCR_OIL_LIMIT.ocr(self.device.image)
            }
            oil = _oil['Value']
            logger.hr('Get Coin')
            _coin = {
                'Value': OCR_COIN.ocr(self.device.image),
                'Limit': OCR_COIN_LIMIT.ocr(self.device.image)
            }
            coin = _coin['Value']
            logger.hr('Get Gem')
            gem = OCR_SHOP_GEMS.ocr(self.device.image)
            if _oil['Value'] > 0:
                break
        logger.info(f'[Oil]{oil} [Coin]{coin} [Gem]{gem}')
        LogRes(self.config).Oil = _oil
        LogRes(self.config).Coin = _coin
        LogRes(self.config).Gem = gem
        self.config.update()

    def get_cube(self, skip_first_screenshot=True):
        logger.hr('Get Cube')
        self.ui_goto_gacha()
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()
            cube = OCR_BUILD_CUBE_COUNT.ocr(self.device.image)
            if cube > 0:
                break
        logger.attr('Cube',cube)
        LogRes(self.config).Cube = cube
        self.config.update()
        self.ui_goto_main()

    def _get_pt(self):
        pt = OCR_PT.ocr(self.device.image)
        res = re.search(r'X(\d+)', pt)
        if res:
            pt = int(res.group(1))
        else:
            pt = 0
            logger.warning(f'Invalid pt result: {pt}')
        logger.attr('Event_PT', pt)
        LogRes(self.config).Pt = pt
        self.config.update()

    def get_pt(self):
        self.ui_goto(page_campaign_menu)
        self.device.sleep(0.5)
        self.device.screenshot()
        if self.appear(button=CAMPAIGN_MENU_NO_EVENT, offset=(50, 50)):
            logger.warning('Event is already closed')
            pt = 0
            logger.attr('Event_PT', pt)
            LogRes(self.config).Pt = pt
        else:
            event = deep_get(self.config.data, 'DashboardUpdate.DashboardUpdate.Event')
            if event == 'event':
                self.ui_goto_event()
                self._get_pt()
            elif event == 'raid':
                self.ui_ensure(page_raid)
                self.get_event_pt()

    def get_event_pt(self):
        """
        Returns:
            int: Raid PT, 0 if raid event is not supported

        Pages:
            in: page_raid
        """
        from module.log_res import LogRes
        skip_first_screenshot = True
        timeout = Timer(1.5, count=5).start()
        event = deep_get(self.config.data, 'Raid.Campaign.Event')
        ocr = pt_ocr(event)
        if ocr is not None:
            # 70000 seems to be a default value, wait
            while 1:
                if skip_first_screenshot:
                    skip_first_screenshot = False
                else:
                    self.device.screenshot()

                pt = ocr.ocr(self.device.image)
                if timeout.reached():
                    logger.warning('Wait PT timeout, assume it is')
                    LogRes(self.config).Pt = pt
                    return pt
                if pt in [70000, 70001]:
                    continue
                else:
                    LogRes(self.config).Pt = pt
                    return pt
        else:
            logger.info(f'Raid {self.config.Campaign_Event} does not support PT ocr, skip')
            return 0

    def goto_shop(self):
        self.ui_goto_shop()
        current = self._shop_bottom_navbar.get_active(main=self)
        logger.info(f'Shop nav actives at left={current}')
        if current is not None:
            current += 1
            if self.shop_bottom_navbar_ensure(left=current - 1):
                self.device.sleep((0.4, 0.5))
                logger.hr('Get Merit')
                self.get_merit()
            if current - 3 >= 1:
                if self.shop_bottom_navbar_ensure(left=current - 3):
                    self.device.sleep((0.4, 0.5))
                    logger.hr('Get Core')
                    self.get_core()
            else:
                logger.warning('Cannot navigate to core shop, skip')
        else:
            logger.error('Cannot get the position of general shop, skip merit shop and core shop')
        self.shop_swipe()
        if self.shop_bottom_navbar_ensure(left=4):
            self.device.sleep((0.4, 0.5))
            logger.hr('Get GuildCoin')
            self.get_guild_coins()
        if self.shop_bottom_navbar_ensure(left=3):
            self.device.sleep((0.4, 0.5))
            logger.hr('Get Medal')
            self.get_medal()
        self.ui_goto_main()

    def get_merit(self, skip_first_screenshot=True):
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()
            merit = OCR_SHOP_MERIT.ocr(self.device.image)
            if merit > 0:
                break
        logger.attr('Merit',merit)
        LogRes(self.config).Merit = merit
        self.config.update()

    def get_core(self, skip_first_screenshot=True):
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()
            core = OCR_SHOP_CORE.ocr(self.device.image)
            if core > 0:
                break
        logger.attr('Core',core)
        LogRes(self.config).Core = core
        self.config.update()

    def get_guild_coins(self, skip_first_screenshot=True):
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()
            guildcoin = OCR_SHOP_GUILD_COINS.ocr(self.device.image)
            if guildcoin > 0:
                break
        logger.attr('GuildCoin',guildcoin)
        LogRes(self.config).GuildCoin = guildcoin
        self.config.update()
    
    def get_medal(self, skip_first_screenshot=True):
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()
            medal = OCR_SHOP_MEDAL.ocr(self.device.image)
            if medal > 0:
                break
        logger.attr('Medal',medal)
        LogRes(self.config).Medal = medal
        self.config.update()

    def run(self):
        self.dashboard_run()
        self.config.task_delay(server_update=True)