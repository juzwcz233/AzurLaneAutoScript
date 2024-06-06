import os
import json
from module.base.base import ModuleBase
from module.config.config import AzurLaneConfig


class GGData(ModuleBase):
    gg_enable = False
    gg_restart = True
    gg_on = False
    ggdata = {}

    def __init__(self, config=AzurLaneConfig):
        self.config = config
        self.ggdata = {
            'name': self.config.config_name,
            'gg_enable': self.config.cross_get('GameManager.GGHandler.Enable', default=False),
            'gg_restart': self.config.cross_get('GameManager.GGHandler.RestartEverytime', default=True),
            'gg_on': False
        }
        self.filename = f'./gg_config/{self.config.config_name}.GG.json'

        if not os.path.exists('./gg_config'):
            os.mkdir('./gg_config')
        with open(file=self.filename, mode='a+', encoding='utf-8') as json_file:
            json_file.close()
        with open(file=self.filename, mode='r', encoding='utf-8') as json_file:
            try:
                data = json.load(json_file)
                if data['name'] != self.config.config_name:
                    raise ValueError
            except(ValueError, KeyError):
                with open(file=self.filename, mode='w', encoding='utf-8') as json_file:
                    json.dump(self.ggdata, json_file, ensure_ascii=False, indent=4)
            else:
                self.ggdata = data

    def get_data(self):
        return self.ggdata

    def set_data(self, target=None, value=None):
        self.ggdata[target] = value
        with open(file=self.filename, mode='w', encoding='utf-8') as json_file:
            json.dump(self.ggdata, json_file, ensure_ascii=False, indent=4)
