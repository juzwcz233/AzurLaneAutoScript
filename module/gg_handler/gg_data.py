from module.base.base import ModuleBase
from module.config.config import AzurLaneConfig


class GGData(ModuleBase):
    def __init__(self, config=AzurLaneConfig):
        self.config = config
        self.ggdata = {
            'name': self.config.config_name,
            'gg_enable': self.config.cross_get('GameManager.GGHandler.Enable', default=False),
            'gg_restart': self.config.cross_get('GameManager.GGHandler.RestartEverytime', default=True),
            'gg_on': False
        }
        try:
            dataname = self.config.cross_get('GameManager.Storage.Storage.name', default=None)
            if dataname != self.config.config_name:
                raise ValueError
        except(ValueError, KeyError):
            self.config.cross_set('GameManager.Storage.Storage', self.ggdata)

    def get_data(self, target=None):
        return self.config.cross_get(f'GameManager.Storage.Storage.{target}', default=None)

    def set_data(self, target=None, value=None):
        self.config.cross_set(f'GameManager.Storage.Storage.{target}', value)
