from cached_property import cached_property
from module.logger import logger
from module.base.base import ModuleBase as Base
from module.config.utils import deep_get
from module.config.utils import read_file, filepath_argument
from datetime import datetime

def now():
    return datetime.now().replace(microsecond=0)

class LogRes(Base):
    """
    set attr--->
    Logres(AzurLaneConfig).<res_name>=resource_value:int
    OR  ={'Value:int, 'Limit/Total':int}:dict
    """
    YellowCoin: list

    def __init__(self, config):
        self.__dict__['config'] = config

    def __setattr__(self, key, value):
        if key in self.groups:
            _key_group = f'Resource.{key}'
            _key_time = _key_group + f'.Record'
            original = deep_get(self.config.data, _key_group)
            if isinstance(value, int):
                if value != original['Value']:
                    _key = _key_group + '.Value'
                    self.config.modified[_key] = value
                    self.config.modified[_key_time] = now()
            elif isinstance(value, dict):
                for value_name, value in value.items():
                    if value != original[value_name]:
                        _key = _key_group + f'.{value_name}'
                        self.config.modified[_key] = value
                        self.config.modified[_key_time] = now()
        else:
            logger.info('No such resource on dashboard')
            super().__setattr__(key, value)

    @cached_property
    def groups(self) -> dict:
        return deep_get(read_file(filepath_argument("task")), 'Dashboard.tasks.Resource')
