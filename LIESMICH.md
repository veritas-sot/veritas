# veritas nautobot toolkit library

# Übersicht <a name="introduction"></a>

# Table of contents
1. [Übersicht](#*introduction*)
2. [Installation](#installation)
    1. [Python Environment](#install_python_env)
    2. [Installation der Library](#install_python_lib)
3. [Beispiele](#examples)


Die Library soll einem das 'Leben' mit nautobot einfacher machen, indem es einige grundlegende Funktionen zur Verfügung stellt. Dabei wird weitestgehend ein Fluent-Syntax genutzt, um es 'Netzwerkern' einafacher zu machen, bestimmte Daten abzufragen oder Geräte nautobot hinzuzufügen. 

Möchte man beispielsweise eine Liste aller Geräte haben, die zu einer bestimmten Location gehören, so kann dies einfach mit

```
liste = my_sot.select('id, hostname') \
              .using('nb.devices') \
              .where('location=meine_location')
```

realisiert werden. Auch 'boolische' Ausdrücke sind möglich:

```
liste = my_sot.select('id, hostname') \
              .using('nb.devices') \
              .where('name=eins.local or name=zwei.local')
```

Auch ist das Onboarding eines Gerätes simple. Mit

```
neues_device = sot.onboarding \
                  .interfaces(interfaces) \
                  .vlans(vlan_properties) \
                  .primary_interface(primary_interface.get('name')) \
                  .add_prefix(False) \
                  .add_device(device_properties)
```

wird ein neues Gerät samt Interfaces und Adressen angelegt und das Primary Interface gesetzt. Weitere Beispiele werden im Abschnitt (#Beispiele) aufgelistet.

# Installation <a name="installation"></a>

Die Installtion ist recht einfach. veritas nutzt poetry, um Abhängigkeiten aufzulösen. 

## Python Environment <a name="install_python_env"></a>

Es ist am einfachsten, ein lokales Python-Environment zu nutzen. So kann man zum Beispiel (mini)conda nutzen.

Mit

```
conda create --name veritas python=3.11
```

wird ein neues Environment mit dem Namen 'veritas' und der Python Version 3.11 angelegt.

## Installation der Library <a name="install_python_lib"></a>

Mit 

```
poetry install
```

wird die Library installiert und kann anschließend genutzt werden.


# Beispiele <a name="examples"></a>


## Grundlegendes

Mit 

```
from veritas.sot import sot
```

wird dei sot-Klasse der Library importiert. Um mit nautobot Daten auszutauschen, wird ein Objekt erstellt.


```
from veritas.sot import sot

my_sot = sot.Sot(token="my_secret_token", 
                 url="http://url_to_nautobot:port",
                 api_version="2.0")
```

Anschließend kann dieses Objekt genutzt werden, um Abfragen zu stellen.

```
# get id and hostname of hosts where name includes local
devices = my_sot.select('id, hostname, custom_field_data') \
                .using('nb.devices') \
                .where('name__ic=local')
print(json.dumps(devices, indent=4))
```

Dies ergibt beispielsweise die Ausgabe

```
[
    {
        "id": "e7ac5c82-7e8b-4363-8c1b-81a20e8561b1",
        "hostname": "lab.local",
        "custom_field_data": {
            "net": "testnet"
        }
    }
]
```

## Weitere Beispiele

### Abfragen von Locations

```
# get all hosts of a location
devices = my_sot.select(['hostname']) \
                .using('nb.devices') \
                .where('location=default-site')
print(json.dumps(devices, indent=4))
```

Ergebnis:

```
[
    {
        "hostname": "lab.local"
    }
]
```


### Abfragen von Interfaces

```
# get id, hostname and interface (named GigabitEthernet0/0) of all hosts
devices = my_sot.select('id, hostname, interfaces') \
                .using('nb.devices') \
                .where('interfaces_name=GigabitEthernet0/0')
print(json.dumps(devices, indent=4))
```

Ergebnis:

```
[
    {
        "id": "e7ac5c82-7e8b-4363-8c1b-81a20e8561b1",
        "hostname": "lab.local",
        "interfaces": [
            {
                "id": "3a49d6e8-7960-45f3-bc7f-db387a751859",
                "name": "GigabitEthernet0/0",
                "description": "test",
                "enabled": true,
                "mac_address": null,
                "type": "A_1000BASE_T",
                "mode": null,
                "status": {
                    "id": "f8121765-f3cc-4662-92d2-000258c6383a",
                    "name": "Active"
                },
                "ip_addresses": [],
                "connected_circuit_termination": null,
                "tagged_vlans": [],
                "untagged_vlan": null,
                "cable": null,
                "tags": [],
                "lag": null,
                "member_interfaces": []
            }
        ]
    }
]```

