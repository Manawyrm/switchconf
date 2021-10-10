# Switchconf

VLANs are useful, but managing VLANs even on proper networking hardware can be complex and error-prone. This project tries to simplify the VLAN and switch port configuration process by just describing the desired network configuration as a YAML config file. (see examples down below)

**Switchconf** is a Python3 script to manage a network of cheap, consumer managed Ethernet switches.  
It can talk to TP-Link TL-SG105E, SG108E (and probably others) via the web interface.

### Usage
```python3 switchconf.py --config mynetwork.yaml --dry-run```  

When everything looks correct, remove the ``--dry-run`` option and let the software do it's magic.

### Example configuration
```yaml
default-vlan: Main
switches:
  Switch-Upstairs:
    ip: switch-upstairs.domain.de
    type: "tl-sg105e"
    username: admin
    password: 1234
    description: "Switch-Upstairs"
    ports:
      port1:
        description: "Switch-Downstairs"
        type: trunk
        destination: "Switch-Downstairs"
      port2:
        description: "Ubiquiti AC Lite"
        type: trunk
        vlan: Main # untagged VLAN for Management
      port3:
      port4:
        description: "Router LAN1 Main"
        vlan: Main
      port5:
        description: "Router LAN4 Guest"
        vlan: Guest

  Switch-Downstairs:
    ip: switch-downstairs.domain.de
    type: "tl-sg105e"
    username: admin
    password: 1234
    description: "Switch-Downstairs"
    default-vlan: Guest
    ports:
      port1:
        description: "Switch-Upstairs"
        type: trunk
        destination: "Switch-Upstairs"
      port2:
        description: "Ubiquiti AC Lite"
        type: trunk
        vlan: Main # untagged VLAN for Management
      port3:
      port4:
      port5:

vlans:
  Main:
    vlan-id: 1
  Guest:
    vlan-id: 2
```


### Advantages
- Support for super cheap (25€) switches
- Way more usable and less error-prone than the web interface
- Adding/changing a VLAN doesn't require manual work anymore
- Support for "trunk" ports, which carry all VLANs automatically (to other switches, access points, routers, etc.)
- Simple plausibility check to prevent locking yourself out of the management
- No vendor-lock-in (currently only supports TP-Link, but is easily upgraded)
- YAML configuration can have port descriptions (web interface for TL-SG10x doesn't)
- Automatic PVID handling (PVIDs are the same as the untagged VLAN ID in 99.9% of cases)

### Disadvantages
- Security of TP-Link Managed Switches is abysmal
- No seperate management connectivity, VLAN 1 / untagged always needs to be reachable
- Only physical ports are supported, no LAG/virtual port support
- Only VLAN configuration supported, no STP, multicast, etc. configuration
- There's no atomicity to the network changes, the cheap switches don't support anything like that. 

### Known issues / quirks
- VLAN names, destination identifiers, etc. should be case-insensitive, matching might not work 100% for UTF-8 characters. When in doubt, use ASCII names/identifiers or be binary-perfect.
- Omission of certain config properties might lead to crashes. Please report or send PRs.
- This tool was designed for my own personal use, it might not suit your use-case. Read the dry-run output carefully!

### YAML parameters
3 parameters need to be present on the root-level: 
- `switches` - array, list of all switches  

Switches need to have the following properties:  
`type` - string, e.g. "tl-sg108e", which will call that script in `backends/`.  
`ports` - array, containing a list of all ports

Optional properties:  
`default-vlan` - string, VLAN name for unconfigured ports  
`description` - string, description, for humans only  

All other parameters are used by the device-backends directly, often `ip`, `username`, `password`.

- `vlans` - array, list of all VLANs
- `default-vlan` - string, VLAN name, used for all unconfigured ports