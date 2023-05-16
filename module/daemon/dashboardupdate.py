from module.log_res.log_res import LogRes
from module.logger import logger
from module.ocr.ocr import Ocr, Digit
from module.base.utils import *
from module.ui.ui import UI
from module.gacha.ui import GachaUI
from module.shop.ui import ShopUI
from module.config.utils import deep_get
from module.handler.login import LoginHandler
from module.ui.assets import MAIN_GOTO_CAMPAIGN, CAMPAIGN_MENU_NO_EVENT
from module.campaign.assets import OCR_EVENT_PT, OCR_COIN, OCR_OIL, OCR_COIN_LIMIT, OCR_OIL_LIMIT
from module.shop.assets import SHOP_GEMS, SHOP_MEDAL, SHOP_MERIT, SHOP_GUILD_COINS, SHOP_CORE
from module.gacha.assets import BUILD_CUBE_COUNT

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


class DashboardUpdate(LoginHandler):
    def run(self):
        option = deep_get(self.config.data, 'DashboardUpdate.DashboardUpdate.Update')
        if option=="main":
            self.app_start()
            self.get_main()
            self.get_cube()
            logger.info('Update Dashboard Data Finished')
        elif option=="all":
            self.app_start()
            self.get_main()
            self.get_cube()
            self.goto_shop()
            self.get_pt()
            UI(self.config, device=self.device).ui_goto_main()
            logger.info('Update Dashboard Data Finished')

    def get_main(self, skip_first_screenshot=True):
        UI(self.config, device=self.device).ui_goto_main()
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
            logger.hr('Get Coin')
            _coin = {
                'Value': OCR_COIN.ocr(self.device.image),
                'Limit': OCR_COIN_LIMIT.ocr(self.device.image)
            }
            logger.hr('Get Gem')
            gem = OCR_SHOP_GEMS.ocr(self.device.image)
            if _oil['Value'] > 0:
                break
        LogRes(self.config).Oil = _oil
        LogRes(self.config).Coin = _coin
        LogRes(self.config).Gem = gem
        self.config.update()

    def get_cube(self, skip_first_screenshot=True):
        logger.hr('Get Cube')
        GachaUI(self.config, device=self.device).ui_goto_gacha()
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()
            cube = OCR_BUILD_CUBE_COUNT.ocr(self.device.image)
            if cube > 0:
                break
        LogRes(self.config).Cube = cube
        self.config.update()
        UI(self.config, device=self.device).ui_goto_main()
    
    def get_pt(self):
        self.device.sleep(0.2)
        self.device.click(MAIN_GOTO_CAMPAIGN)
        self.device.sleep(0.2)
        self.device.screenshot()
        logger.hr('Get pt')
        if self.appear(CAMPAIGN_MENU_NO_EVENT, offset=(20, 20)):
            logger.info('Event is already closed')
            pt = 0
            logger.attr('Event_PT', pt)
            LogRes(self.config).Pt = pt
        else:
            self.ui_goto_event()
            pt = OCR_PT.ocr(self.device.image)
            res = re.search(r'X(\d+)', pt)
            if res:
                pt = int(res.group(1))
                logger.attr('Event_PT', pt)
                LogRes(self.config).Pt = pt
            else:
                logger.warning(f'Invalid pt result: {pt}')
                pt = 0
                LogRes(self.config).Pt = pt
        self.config.update()
    
    def goto_shop(self):
        ShopUI(self.config, device=self.device).ui_goto_shop()
        ShopUI(self.config, device=self.device).shop_swipe()
        if ShopUI(self.config, device=self.device).shop_bottom_navbar_ensure(left=5):
            self.device.sleep((0.4, 0.5))
            logger.hr('Get Merit')
            self.get_merit()
        if ShopUI(self.config, device=self.device).shop_bottom_navbar_ensure(left=4):
            self.device.sleep((0.4, 0.5))
            logger.hr('Get Core')
            self.get_core()
        if ShopUI(self.config, device=self.device).shop_bottom_navbar_ensure(left=2):
            self.device.sleep((0.4, 0.5))
            logger.hr('Get GuildCoin')
            self.get_guild_coins()
        if ShopUI(self.config, device=self.device).shop_bottom_navbar_ensure(left=1):
            self.device.sleep((0.4, 0.5))
            logger.hr('Get Medal')
            self.get_medal()
        UI(self.config, device=self.device).ui_goto_main()
    
    def get_medal(self, skip_first_screenshot=True):
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()
            medal = OCR_SHOP_MEDAL.ocr(self.device.image)
            if medal > 0:
                break
        LogRes(self.config).Medal = medal
        self.config.update()

    def get_merit(self, skip_first_screenshot=True):
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()
            merit = OCR_SHOP_MERIT.ocr(self.device.image)
            if merit > 0:
                break
        LogRes(self.config).Merit = merit
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
        LogRes(self.config).GuildCoin = guildcoin
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
        LogRes(self.config).Core = core
        self.config.update()

    def app_start(self):
        if self.device.app_is_running():
            logger.info('Game is already running, goto main page')
        else:
            logger.info('Game is not running, start game and goto main page')
            LoginHandler(self.config, device=self.device).app_start()

if __name__ == '__main__':
    DashboardUpdate('alas', task='DashboardUpdate').run()