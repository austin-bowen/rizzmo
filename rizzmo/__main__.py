import socket
from time import sleep

from rizzmo.config import IS_RIZZMO
from rizzmo.procman import ProcessManager

host_nodes = {
    'rizzmo': (
        'camera_node',
        'maestro_ctl',
        'mic_node',
        'obj_tracker',
        'speech_node',
        'website_node',
    ),
    'potato': (
        ('objrec_node', 2),
        'vad_node',
    ),
    'austin-laptop': (
        'audio_viz_node',
        'display_objs_node',
    )
}


def main():
    host = socket.gethostname()
    nodes_to_start = host_nodes[host]
    print(f'Starting nodes: {nodes_to_start}')

    with ProcessManager() as p:
        if IS_RIZZMO:
            p.start_python_module('easymesh.coordinator')
            sleep(1)

        for node in nodes_to_start:
            if isinstance(node, str):
                count = 1
            else:
                node, count = node

            for _ in range(count):
                p.start_python_module(f'rizzmo.nodes.{node}')

        try:
            p.wait()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
