# veritas nautobot toolkit library

# Übersicht

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

# Installation

Die Installtion ist recht einfach. veritas nutzt poetry, um Abhängigkeiten aufzulösen. 

## Python Environment

Es ist am einfachsten, ein lokales Python-Environment zu nutzen. So kann man zum Beispiel (mini)conda nutzen.

Mit

conda create --name veritas python=3.11

wird ein neues Environment mit dem Namen 'veritas' und der Python Version 3.11 angelegt.

## Installation der Library

Mit 

poetry install

wird die Library installiert und kann anschließend genutzt werden.


# Beispiele



