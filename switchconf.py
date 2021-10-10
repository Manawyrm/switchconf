#!/usr/bin/env python3
import importlib
import click
import yaml
import pprint
pp = pprint.PrettyPrinter(indent=4, compact=False)


def get_vlan_id_by_name(vlan_name, vlans_by_name):
    if vlan_name not in vlans_by_name:
        raise Exception(f"VLAN {vlan_name} not found!")

    return vlans_by_name[vlan_name]['vlan-id']


def get_switch_port_config(port_name, port_config, switch_default_vlan, vlans_by_name):
    # Determine port type, default to untagged
    if port_config is None:
        port_config = {}

    if 'type' not in port_config:
        port_config['type'] = "untagged"

    port_config['type'] = port_config['type'].lower()

    if port_config['type'] == "trunk":
        # Trunk ports have all VLANs
        port_config['tagged-vlan-ids'] = []
        for vlan_name in vlans_by_name:
            port_config['tagged-vlan-ids'].append(get_vlan_id_by_name(vlan_name, vlans_by_name))

        # and use the default VLAN as the PVID
        port_config['pvid'] = get_vlan_id_by_name(switch_default_vlan, vlans_by_name)
    elif port_config['type'] == "tagged":
        port_config['tagged-vlan-ids'] = []
        for vlan_name in port_config['vlans']:
            port_config['tagged-vlan-ids'].append(get_vlan_id_by_name(vlan_name, vlans_by_name))

        if 'vlan' in port_config:
            # Admin has configured an additional untagged VLAN on this tagged port
            port_config['untagged-vlan-id'] = get_vlan_id_by_name(port_config['vlan'], vlans_by_name)
            port_config['pvid'] = port_config['untagged-vlan-id']
        else:
            pvid = switch_default_vlan
            if 'pvid' in port_config:
                pvid = port_config['pvid']

            port_config['pvid'] = get_vlan_id_by_name(pvid, vlans_by_name)
            if port_config['pvid'] not in port_config['tagged-vlan-ids']:
                raise Exception(f"Port {port_name} - Default VLAN ({switch_default_vlan}, ID: {port_config['pvid']})"
                                " is not a member of the tagged port. Either add the pvid-Parameter manually"
                                " or add the default VLAN to this port.")

    elif port_config['type'] == "untagged":
        vlan = switch_default_vlan
        if 'vlan' in port_config:
            vlan = port_config['vlan']

        port_config['untagged-vlan-id'] = get_vlan_id_by_name(vlan, vlans_by_name)
        port_config['pvid'] = port_config['untagged-vlan-id']
        pass
    else:
        raise Exception(f"Port {port_name} - Type {port_config['type']} unknown!")

    return port_config


def parse_switch_config(switch_name, switch_config, vlans_by_name, global_default_vlan):
    # Determine default VLAN for this switch. Use global VLAN unless "default-vlan" property is present.
    switch_default_vlan = global_default_vlan
    if 'default-vlan' in switch_config:
        switch_default_vlan = switch_config['default-vlan']

    # Run through all (configured) ports
    for port_name in switch_config['ports']:
        switch_config['ports'][port_name] = get_switch_port_config(port_name,
                                                                   switch_config['ports'][port_name],
                                                                   switch_default_vlan,
                                                                   vlans_by_name)

    return switch_config


def parse_config(config):
    vlans_by_name = config['vlans']

    for switch_name in config['switches']:
        config['switches'][switch_name] = parse_switch_config(switch_name, config['switches'][switch_name], vlans_by_name, config['default-vlan'])


def load_switch_backends(config):
    switch_backends = {}
    # Run through all switches
    for switch_name in config['switches']:
        switch_type = config['switches'][switch_name]['type']
        # and try to load the switch type as a python module with the same name in the backends-folder
        try:
            switch_backend = importlib.import_module("backends." + switch_type.lower())
        except ImportError:
            raise Exception(f"Switch backend for type {switch_type} not found!")

        # try to connect (this will also validate the credentials hopefully)
        try:
            switch_backend.test_connection(config['switches'][switch_name])
        except Exception as ex:
            raise Exception(f"Could not connect to {switch_name}, type: {switch_type}! More detail: {repr(ex)}")

        switch_backends[switch_name] = switch_backend

    return switch_backends


def deploy_config(switch_backends, config):
    for switch_name in config['switches']:
        switch_backends[switch_name].deploy_config(config['switches'][switch_name])

    return

@click.command()
@click.option('--config', help='Config file')
@click.option('--dry-run', help='Do a dry-run (try to connect, parse config, don\'t change anything')
def main(config, dry_run):
    with open(config, "r") as config_stream:
        try:
            config = yaml.safe_load(config_stream)
        except yaml.YAMLError as exc:
            print(exc)
            exit(1)

    parse_config(config)
    switch_backends = load_switch_backends(config)

    print(yaml.safe_dump(config, sort_keys=False, default_style=None, default_flow_style=False))

    deploy_config(switch_backends, config)

if __name__ == '__main__':
    main()

