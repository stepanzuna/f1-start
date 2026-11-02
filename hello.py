from psychopy import visual, core

win = visual.Window(size=(800, 600), color="black", units="pix")
rate = win.getActualFrameRate()

def frames(seconds: float) -> int:
    """Převede sekundy na počet snímků podle naměřené frekvence."""
    return round(seconds * rate)

lamp = visual.Circle(win, radius=40, pos=(0, 0), fillColor="red")

for _ in range(frames(1.0)):
    lamp.draw()
    win.flip()

for _ in range(frames(1.0)):
    win.flip()  # nic nekreslíme → obrazovka je černá

win.close()
core.quit()