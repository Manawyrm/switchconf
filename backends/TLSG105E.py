import json

import hjson
import yaml
import requests
import re

class TLSG105E:
    NUM_PHYSICAL_PORTS = 5

    SELTYPE_UNTAGGED = 0
    SELTYPE_TAGGED = 1
    SELTYPE_NOTAMEMBER = 2

    def __init__(self, name, config, vlans):
        if len(vlans) >= 32:
            raise Exception(f"Switch {name} - Cheap TP-Link switches only support 32 different VLANs. Aborting.")

        self.name = name
        self.ip = config['ip']
        self.username = config['username']
        self.password = config['password']

        # Send a login POST request
        login_response = requests.post(self.build_url('logon.cgi'), data={
            'username': self.username,
            'password': self.password,
            'cpassword': '',
            'logon': 'Login'
        })

        # Ask for the system info page
        system_info_response = requests.get(self.build_url('SystemInfoRpm.htm'))
        if 'info_ds' not in system_info_response.text:
            raise Exception(f"Switch {name} - Login not successful or switch firmware incompatible!")


    def build_url(self, url):
        return f"http://{self.ip}/{url}"

    def deploy_config(self, config, vlans):
        vlan_overview_response = requests.get(self.build_url('Vlan8021QRpm.htm'))
        if "var qvlan_ds = {\nstate:0," in vlan_overview_response.text:
            # 802.1q VLANs aren't enabled yet. Enable VLANs:
            print(f"Switch {self.name} - Enabling 802.1q VLANs...")
            requests.get(self.build_url('qvlanSet.cgi'), params={
                'qvlan_en': 1,
                'qvlan_mode': 'Apply'
            })

        # Set the 802.1q VLAN config
        for vlan_name in vlans:
            vlan_id = vlans[vlan_name]['vlan-id']
            safe_vlan_name = ''.join(filter( lambda x: x in '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', vlan_name ))[:10]
            request = {
                'vid': vlan_id,
                'vname': safe_vlan_name,
                'qvlan_add': 'Add%2FModify'
            }
            for port_id in range(1, self.NUM_PHYSICAL_PORTS + 1):
                # define all physical ports as "Not a member" first
                request['selType_' + str(port_id)] = self.SELTYPE_NOTAMEMBER

                # now let's try to find this port in our config data
                for port_name in config['ports']:
                    if port_name == 'port' + str(port_id):
                        port_config = config['ports'][port_name]
                        if 'tagged-vlan-ids' in port_config and vlan_id in port_config['tagged-vlan-ids']:
                            request['selType_' + str(port_id)] = self.SELTYPE_TAGGED

                        if 'untagged-vlan-id' in port_config and port_config['untagged-vlan-id'] == vlan_id:
                            request['selType_' + str(port_id)] = self.SELTYPE_UNTAGGED

            #print(yaml.safe_dump(request, sort_keys=False, default_style=None, default_flow_style=False))
            print(f"Switch {self.name} - Configuring VLAN ID {vlan_id} - {safe_vlan_name}...")
            requests.get(self.build_url('qvlanSet.cgi'), params=request)

        # Set the 802.1q PVID Settings
        for port_id in range(1, self.NUM_PHYSICAL_PORTS + 1):
            # define all physical ports as PVID 1
            pvid = 1

            # now let's try to find this port in our config data
            for port_name in config['ports']:
                if port_name == 'port' + str(port_id):
                    port_config = config['ports'][port_name]
                    if 'pvid' in port_config:
                        pvid = port_config['pvid']

            request = {
                # pbm - Port BitMap - example: Port 3 -> 00000100 -> pbm: 4
                'pbm': 1 << (port_id - 1),
                'pvid': pvid
            }
            print(f"Switch {self.name} - Configuring PVID on Port {port_id} - PVID: {pvid}...")
            #print(yaml.safe_dump(request, sort_keys=False, default_style=None, default_flow_style=False))
            requests.get(self.build_url('vlanPvidSet.cgi'), params=request)

        # Now let's delete unused VLANs
        try:
            vlan_info_response = requests.get(self.build_url('Vlan8021QRpm.htm'))
            vlan_info = self.try_parse_html_json("qvlan_ds", vlan_info_response.text)

            # Iterate through all VLANs on the switch
            for vlan_id in vlan_info['vids']:
                vlan_should_exist = False
                # Go through each VLAN in the config
                for vlan_name in vlans:
                    if vlan_id == vlans[vlan_name]['vlan-id']:
                        vlan_should_exist = True

                if not vlan_should_exist:
                    print(f"Switch {self.name} - Removing unused VLAN-ID: {vlan_id}...")
                    requests.get(self.build_url('qvlanSet.cgi'), params={
                        'selVlans': vlan_id,
                        'qvlan_del': 'Delete'
                    })

        except Exception:
            raise Exception(f"Switch {self.name} - Failed while removing old VLANs...")

        return True

    def try_parse_html_json(self, variable_name, html):
        matches = re.search(r"%s = (.*?);" % variable_name, html, re.DOTALL)

        if matches:
            if len(matches.groups()) >= 1:
                json_blob = matches.group(1)
                data = hjson.loads(json_blob)
                return data

        return None
