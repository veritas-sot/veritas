# veritas nautobot toolkit library

# Table of contents
1. [Übersicht](#*introduction*)
2. [Installation](#installation)
    1. [Python Environment](#install_python_env)
    2. [Installation der Library](#install_python_lib)
3. [sot](#sot)
4. [tools](#tools)
5. [devicemanagement](#devicemanagement)
6. [inventory](#inventory)
7. [journal](#journal)
8. [checkmk](#checkmk)
9. [Beispiele](#examples)
    1. [sot](#examples_sot)
        - [Grundlegendes](#examples_basic)
        - [Devices](#examples_sot_all_devices)
        - [Roles und platforms](#examples_sot_roles_platforms)
        - [Interfaces](#examples_locations)
        - [Prefixes](#examples_prefixes)
        - [IP-Adressen](#examples_adresses)
    2. [tools](#examples_tools)

# Übersicht <a name="introduction"></a>

Die Library soll einem das 'Leben' mit nautobot einfacher machen, indem es einige grundlegende Funktionen zur Verfügung stellt. Dabei wird weitestgehend ein Fluent-Syntax genutzt, um es 'Netzwerkern' einafacher zu machen, bestimmte Daten abzufragen oder Geräte nautobot hinzuzufügen. 

Möchte man beispielsweise eine Liste aller Geräte haben, die zu einer bestimmten Location gehören, so kann diese Liste mit

```
liste = my_sot.select('id, hostname') \
              .using('nb.devices') \
              .where('location=meine_location')
```

erstellt werden. Auch 'boolische' Ausdrücke sind möglich:

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

wird ein neues Environment mit dem Namen 'veritas' und der Python Version 3.11 angelegt. Poetry wird benötigt, um die Library zu installieren. Mit

```
conda install poetry
```

kann poetry installiert werden.

## Installation der Library <a name="install_python_lib"></a>

Mit 

```
poetry install
```

wird die Library installiert und kann anschließend genutzt werden.

# sot <a name="sot"></a>

Die sot-Klasse bietet grundlegende Funktionen um nautobot anzusprechen. Dies beinhaltet:

* select
* get
* onboarding
* device
* ipam
* rest
* auth
* importer
* update


# tools <a name="tools"></a>

# devicemanagement <a name="devicemanagement"></a>

# inventory <a name="inventory"></a>

# journal <a name="journal"></a>

# checkmk <a name="checkmk"></a>

# Beispiele <a name="examples"></a>

## sot <a name="examples_sot"></a>

### Grundlegendes <a name="examples_basics"></a>

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

### Alle Devices <a name="examples_sot_all_devices"></a>

Um alle Devices von nautobot zu erhalten

```
devices = my_sot.select('hostname', 'primary_ip4') \
                .using('nb.devices') \
                .where()
print(json.dumps(devices, indent=4))
```

```
[
    {
        "hostname": "lab.local",
        "primary_ip4": {
            "id": "dbbdb143-2b61-4ef9-a50a-812e1b113894",
            "ip_version": 4,
            "address": "192.168.0.1/24",
            "description": "lab.local GigabitEthernet0/2",
            "mask_length": 24,
            "dns_name": "",
            "interfaces": [
                {
                    "id": "7f93212f-ff2c-4034-96f4-522f66d1b3b5",
                    "name": "GigabitEthernet0/2"
                }
            ]
        }
    }
]
```

### Abfragen von Locations <a name="examples_sot_locations"></a>

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

### Abfragen von Roles <a name="examples_sot_roles_platforms"></a>

```
# get all hosts with a specific role
devices = my_sot.select('hostname') \
                .using('nb.devices') \
                .where('role=default-role')
print(json.dumps(devices, indent=4))
```

### Custom Fields <a name="examples_sot_custom_fields"></a>

```
# get hosts with cf_net=testnet
devices = my_sot.select('hostname, cf_net') \
                .using('nb.devices') \
                .where('cf_net=testnet')
print(json.dumps(devices, indent=4))
```

Ergbenis:

```
[
    {
        "hostname": "lab.local",
        "custom_field_data": {
            "net": "testnet"
        }
    }
]
```

Mehrere Custom Fields mit einer logischen ODER-Verknüfung

```
devices = my_sot.select('hostname') \
                .using('nb.devices') \
                .where('cf_net=testnet or cf_field=value')
print(json.dumps(devices, indent=4))
```

Ergebnis:

```
[
    {
        "id": "5e6fa080-7636-4aec-99ad-7aa4d09cf34a",
        "hostname": "switch.local"
    },
    {
        "id": "e7ac5c82-7e8b-4363-8c1b-81a20e8561b1",
        "hostname": "lab.local"
    }
]
```

### Abfragen von Interfaces  <a name="examples_interfaces"></a>

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
]
```

### Abfragen von Prefixen  <a name="examples_prefixes"></a>

```
# get prefixes, prefix_length and namespace within a prefix
prefixes = my_sot.select('prefix, prefix_length, namespace') \
                 .using('nb.prefixes') \
                 .where('within_include=192.168.0.0/23')
print(json.dumps(prefixes, indent=4))
```

Ergebnis:

```
[
    {
        "prefix": "192.168.0.0/24",
        "prefix_length": 24,
        "namespace": {
            "name": "Global"
        }
    },
    {
        "prefix": "192.168.1.0/24",
        "prefix_length": 24,
        "namespace": {
            "name": "Private"
        }
    }
]
```


```
# get all prefixes within a specififc range and namespace
prefixes = my_sot.select('prefix, prefix_langth, namespace') \
                 .using('nb.prefixes') \
                 .where('within_include="192.168.0.0/23" and namespace=Global')
print(json.dumps(prefixes, indent=4))
```

Ergebnis:

```
[
    {
        "id": "f5f565a6-41c1-4b65-9be1-e59622babe26",
        "prefix": "192.168.0.0/24",
        "namespace": {
            "id": "d07521f8-3f55-4cba-9bf8-34e2dde472bb",
            "name": "Global"
        }
    }
]
```

### Abfragen von IP-Adressen  <a name="examples_adresses"></a>

```
devices = my_sot.select('hostname, address, primary_ip4_for') \
                .using('nb.ipaddresses') \
                .where('address=192.168.0.1')
print(json.dumps(devices, indent=4))
```

Ergebnis:

```
[
    {
        "address": "192.168.0.1/24",
        "primary_ip4_for": [
            {
                "name": "lab.local",
                "hostname": "lab.local"
            }
        ]
    }
]
```

Oder die Daten mit CIDR-Notation

```
# get id, hostname, and primary_ip of the host with IP=192.168.0.0/23
devices = my_sot.select('hostname, address, primary_ip4_for') \
                .using('nb.ipaddresses') \
                .where('prefix=192.168.0.0/23')
print(json.dumps(devices, indent=4))
```

Ergebnis:

```
[
    {
        "address": "192.168.0.1/24",
        "primary_ip4_for": [
            {
                "hostname": "lab.local"
            }
        ]
    },
    {
        "address": "192.168.1.1/24",
        "primary_ip4_for": [
            {
                "hostname": "switch.local"
            }
        ]
    }
]
```

Host mit einer bestimmten IP-Adresse und einem custom field:

```
# get hostname and primary_ip4 of hosts having an IP address in 192.168.0.0/23 and custom field net=testnet
devices = my_sot.select('hostname, primary_ip4_for, cf_net') \
                .using('nb.ipaddresses') \
                .where('prefix="192.168.0.0/23" and pip4for_cf_net=testnet')
print(json.dumps(devices, indent=4))
```

Ergebnis:

```
[
    {
        "id": "dbbdb143-2b61-4ef9-a50a-812e1b113894",
        "primary_ip4_for": [
            {
                "id": "e7ac5c82-7e8b-4363-8c1b-81a20e8561b1",
                "hostname": "lab.local",
                "custom_field_data": {
                    "net": "testnet"
                }
            }
        ]
    },
    {
        "id": "159bed0c-e089-4969-b511-c4e3ac410241",
        "primary_ip4_for": []
    }
]
```
## tools <a name="examples_tools"></a>
