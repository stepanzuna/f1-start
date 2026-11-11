import random

from psychopy import core, visual

OFF = "#333333"
ON = "red"
FOREPERIODS = [0.5, 1.25, 2.0, 2.75]


def frames(seconds: float, rate: float) -> int:
    """Převede sekundy na počet snímků."""
    return round(seconds * rate)


def make_lamps(win: visual.Window) -> list[visual.Circle]:
    """Vytvoří 5 zhasnutých lamp vedle sebe."""
    lamps = []
    for i in range(5):
        x = -240 + i * 120
        lamps.append(
            visual.Circle(win, radius=40, pos=(x, 0), fillColor=OFF, lineColor=None)
        )
    return lamps


def draw_lamps(lamps: list[visual.Circle], n_on: int) -> None:
    """Nakreslí lampy, prvních n_on rozsvícených."""
    for i, lamp in enumerate(lamps):
        lamp.fillColor = ON if i < n_on else OFF
        lamp.draw()


def run_start(win: visual.Window, lamps: list[visual.Circle], rate: float) -> None:
    """Jeden F1 start: rozsvěcování, prodleva, zhasnutí."""
    for n_on in range(1, 6):
        for _ in range(frames(0.4, rate)):
            draw_lamps(lamps, n_on)
            win.flip()

    foreperiod = random.choice(FOREPERIODS)
    for _ in range(frames(foreperiod, rate)):
        draw_lamps(lamps, 5)
        win.flip()

    # blok 3: zhasnutí na 0,5 s – tvůj úkol


def main() -> None:
    win = visual.Window(size=(800, 600), color="black", units="pix")
    rate = win.getActualFrameRate()
    print(f"Frekvence: {rate:.1f} Hz")

    lamps = make_lamps(win)
    run_start(win, lamps, rate)

    win.close()
    core.quit()


if __name__ == "__main__":
    main()
