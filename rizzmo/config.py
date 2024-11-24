import socket
from dataclasses import dataclass

from easymesh.types import Host

IS_RIZZMO = socket.gethostname() == 'rizzmo'


@dataclass
class Config:
    coordinator_host: Host = 'rizzmo.local'

    camera_index: int = 0


config = Config()
