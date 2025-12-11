# hass-stockholm-sopbilen 

## Description
Home Assistant Integration for Stockholm Waste Management for home owners.

## Installation
1. Go to **HACS → Integrations**
2. Click the **⋮ menu → Custom repositories**
   Repository: https://github.com/frossmant/hass-stockholm-sopbilen
         Type: Integration
   Click on ADD
5. Install → Restart Home Assistant
6. Go to **Settings → Devices & Services → Add Integration**
7. Search for **Stockholm Sopbilen**
8. Restart Home Assistant

## Usage
Here is an example for the address format that should be used when adding a monitored address in the HASS GUI.
```
Daltorpsvägen 28, Vällingby, 16244
```
See [example.yaml](example.yaml) for an example deck to display your waste management.
![Garbage Collection Screenshot](https://raw.githubusercontent.com/frossmant/hass-stockholm-sopbilen/main/screenshot_deck.png)

## Features
- Adding addresses to monitor using the standard home assistant integration UI
- Currently monitoring two types of waste, Restavfall and Matavfall
- Getting execution date, weekday and frequency in weeks for the waste collection.

## Contact
frossmant@icloud.com

## Changelog
See [CHANGELOG](CHANGELOG)

## License
GPL v3 license, see [LICENSE](LICENSE).
