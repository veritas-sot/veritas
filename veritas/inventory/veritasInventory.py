from loguru import logger
from typing import Any, Dict, Type
from ..sot import sot
from nornir.core.inventory import (
    Inventory,
    Group,
    Groups,
    Host,
    Hosts,
    Defaults,
    ConnectionOptions,
    HostOrGroup,
    ParentGroups,
)


def _get_connection_options(data: Dict[str, Any]) -> Dict[str, ConnectionOptions]:
    cp = {}
    for cn, c in data.items():
        cp[cn] = ConnectionOptions(
            hostname=c.get("hostname"),
            port=c.get("port"),
            username=c.get("username"),
            password=c.get("password"),
            platform=c.get("platform"),
            extras=c.get("extras"),
        )
    return cp

def _get_defaults(data: Dict[str, Any]) -> Defaults:
    return Defaults(
        hostname=data.get("hostname"),
        port=data.get("port"),
        username=data.get("username"),
        password=data.get("password"),
        platform=data.get("platform"),
        data=data.get("data"),
        connection_options=_get_connection_options(data.get("connection_options", {})),
    )

def _get_inventory_element(
    typ: Type[HostOrGroup], data: Dict[str, Any], name: str, defaults: Defaults
) -> HostOrGroup:
    return typ(
        name=name,
        hostname=data.get("hostname"),
        port=data.get("port"),
        username=data.get("username"),
        password=data.get("password"),
        platform=data.get("platform"),
        data=data.get("data"),
        groups=data.get(
            "groups"
        ),
        defaults=defaults,
        connection_options=_get_connection_options(data.get("connection_options", {})),
    )


class VeritasInventory:
    def __init__(
        self,
        url: str,
        token: str,
        query: str,
        use_primary_ip: bool = True,
        username: str = "",
        password: str = "",
        connection_options: Dict[str, Any] = {},
        data: Dict[str, Any] = {},
        host_groups: list = [],
        groups: Dict[str, Any] = {}

    ) -> None:
        self.url = url
        self.token = token
        self.query = query
        self.use_primary_ip = use_primary_ip
        self.username = username
        self.password = password
        self.connection_options = connection_options
        self.data = data
        self.host_groups = host_groups
        self.groups = groups

    def load(self) -> Inventory:

        devicelist = {}
        nb = sot.Sot(token=self.token, url=self.url)
        # if the user wants 'data' or groups we have to add those fields to our select list
        select = ['hostname', 'primary_ip4', 'platform'] + self.data.get('sot',[])
        sot_devicelist = nb.select(select) \
                           .using('nb.devices') \
                           .where(self.query)

        for device in sot_devicelist:
            hostname = device.get('hostname')
            if not device.get('primary_ip4'):
                logger.error(f'host {hostname} has no primary IPv4 address... skipping')
                continue
            sot_ip4 = device.get('primary_ip4', {}).get('address')
            primary_ip4 = sot_ip4.split('/')[0] if sot_ip4 is not None else hostname
            host_or_ip = primary_ip4 if self.use_primary_ip else hostname
            platform = device.get('platform',{}).get('name','ios') if device['platform'] else 'ios'
            manufacturer = device.get('platform',{}).get('manufacturer',{}).get('name') if device['platform']['manufacturer'] else 'cisco'

            # data is used to get this data later on using the inventory later
            # host = nr.inventory.hosts[hostname]
            # platform = host['platform]
            _data = {'platform': platform,
                     'primary_ip': primary_ip4,
                     'manufacturer': manufacturer}
            # add all keys to data
            for key in self.data.keys():
                if 'sot' == key:
                    sot_keys = self.data.get('sot')
                    for sot_key in sot_keys:
                        if sot_key.startswith('cf_'):
                            sk = sot_key.replace('cf_','')
                            _data[sk] = device.get(sk)
                        else:
                            _data[sot_key] = device.get(sot_key)
                else:
                    _data[key] = self.data.get(key)

            _host_groups = []
            for key in self.host_groups:
                if key.startswith('cf_'):
                    ky = key.replace('cf_','')
                    _host_groups.append(device.get(ky))
                else:
                    _host_hroups.append(device.get(key))

            devicelist[hostname] = {'hostname': host_or_ip,
                                    'port': 22,
                                    'username': self.username,
                                    'password': self.password,
                                    'platform': platform,
                                    'data': _data,
                                    'groups': _host_groups,
                                    'connection_options': self.connection_options
                                   }

        # defaults = Defaults()
        defaults_dict = {}
        defaults = _get_defaults(defaults_dict)
            
        hosts = Hosts()
        for n, h in devicelist.items():
            hosts[n] = _get_inventory_element(Host, h, n, defaults)

        groups = Groups()
        for n, g in self.groups.items():
            groups[n] = _get_inventory_element(Group, g, n, defaults)

        for g in groups.values():
            g.groups = ParentGroups([groups[g] for g in g.groups])

        for h in hosts.values():
            h.groups = ParentGroups([groups[g] for g in h.groups])

        return Inventory(hosts=hosts, groups=groups, defaults=defaults)
