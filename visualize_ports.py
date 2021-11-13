#!/usr/bin/env python3
import importlib
import click
import yaml
import pprint
from N2G import drawio_diagram
import switchconf

switch_style = "sketch=0;pointerEvents=1;shadow=0;dashed=0;html=1;strokeColor=none;fillColor=#434445;aspect=fixed;labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;shape=mxgraph.vvd.virtual_switch;"
port_style = "sketch=0;pointerEvents=1;shadow=0;dashed=0;html=1;strokeColor=none;fillColor=#434445;aspect=fixed;labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;shape=mxgraph.vvd.ethernet_port;"
machine_style = "sketch=0;pointerEvents=1;shadow=0;dashed=0;html=1;strokeColor=none;fillColor=#434445;aspect=fixed;labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;shape=mxgraph.vvd.machine;"

def find_destination_on_switch(switch, destination_name):
    for port_name in switch['ports']:
        port = switch['ports'][port_name]
        if "destination" in port:
            if port['destination'] == destination_name:
                return port_name

    return False

@click.command()
@click.option('--config', help='Config file')
def main(config):
    with open(config, "r") as config_stream:
        try:
            config = yaml.safe_load(config_stream)
        except yaml.YAMLError as exc:
            print(exc)
            exit(1)

    switchconf.parse_config(config)
    print(yaml.safe_dump(config, sort_keys=False, default_style=None, default_flow_style=False))

    diagram = drawio_diagram()
    diagram.add_diagram("Page-1", width=1920, height=1080)

    # Add all switches and all ports
    for switch_name in config['switches'].keys():
        switch = config['switches'][switch_name]
        diagram.add_node(id=switch_name, style=switch_style, width=130, height=70)
        for port_name in switch['ports']:
            port = switch['ports'][port_name]
            diagram.add_node(id=switch_name + port_name, label=port_name, style=port_style, width=50, height=50)
            diagram.add_link(switch_name, switch_name + port_name, label="")

    # Add all destination links
    for switch_name in config['switches'].keys():
        switch = config['switches'][switch_name]
        for port_name in switch['ports']:
            port = switch['ports'][port_name]

            if "destination" in port:
                destination_port = find_destination_on_switch(config['switches'][port['destination']], switch_name)
                #label = f"{switch_name}: {port_name}\n{port['destination']}: {destination_port}"
                diagram.add_link(switch_name + port_name, port['destination'] + destination_port, label="")
                print(f"Adding Destination Link between {switch_name + port_name} and {port['destination'] + destination_port}")


            if "description" in port:
                diagram.add_node(switch_name + port['description'], label=port['description'], style=machine_style, width=20, height=50)
                diagram.add_link(switch_name + port_name, switch_name + port['description'], label="")
                print(f"Adding Description Link between {switch_name + port_name} and {switch_name + port['description']}")


    diagram.layout(algo="rt")
    diagram.dump_file(filename="Sample_graph.drawio", folder="./")


if __name__ == '__main__':
    main()

