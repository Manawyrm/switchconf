from .TLSG105E import TLSG105E


# TP-Link TL-SG108PE are very similar to TL-SG105E and run basically the same firmware
# with a different amount of ports
class TLSG108PE(TLSG105E):
    NUM_PHYSICAL_PORTS = 8
    pass
