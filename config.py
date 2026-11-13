"""Konstanty a parametry experimentu (bez PsychoPy)."""

# Barvy
OFF = "#333333"
ON = "red"
FLAG_COLOR = "#EF9F27"

# Rozložení obrazovky (v pixelech, střed obrazovky je (0, 0))
N_LAMPS = 5
LAMP_RADIUS = 40
LAMP_SPACING = 120
LAMP_Y = -90
FLAG_WIDTH = 500
FLAG_HEIGHT = 300
FLAG_POS = (0, 180)

# Časy (v sekundách)
FOREPERIODS = [0.5, 1.25, 2.0, 2.75]
LIGHT_INTERVAL = 1.0
RESPONSE_WINDOW = 1.5
REST_INTERVAL = 1.0
ANTICIPATION_THRESHOLD = 0.1

# Plán startů
GO_PER_FOREPERIOD = 3
NOGO_PER_FOREPERIOD = 1
