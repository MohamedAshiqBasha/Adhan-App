import time
from datetime import datetime, date

import requests
import pygame
import pytz
from dateutil import parser


# -----------------------------
# Configuration
# -----------------------------
LAT = 29.6585
LNG = -95.7336
METHOD = 2
TZ_NAME = "America/Chicago"
LOCATION_LABEL = "77407 – Richmond, TX"

PRAYER_ORDER = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]

SCREEN_WIDTH = 480
SCREEN_HEIGHT = 320

BG_COLOR = (13, 13, 13)
TEXT_COLOR = (242, 242, 242)
ACCENT_COLOR = (0, 150, 136)
DIVIDER_COLOR = (60, 60, 60)

tz = pytz.timezone(TZ_NAME)


# -----------------------------
# Adhan audio configuration
# -----------------------------
ADHAN_FILES = {
    "Fajr": "fajr_adhan_final.mp3",
    "Dhuhr": "normal_adhan_final.mp3",
    "Asr": "normal_adhan_final.mp3",
    "Maghrib": "normal_adhan_final.mp3",
    "Isha": "normal_adhan_final.mp3",
}

ADHAN_FADEOUT_MS = 0


# -----------------------------
# Prayer time logic
# -----------------------------
def fetch_prayer_times_for_today():
    url = "http://api.aladhan.com/v1/timings"
    today = datetime.now(tz)
    params = {
        "latitude": LAT,
        "longitude": LNG,
        "method": METHOD,
        "timezonestring": TZ_NAME,
        "date": today.strftime("%d-%m-%Y"),
    }

    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()["data"]
    timings = data["timings"]

    prayer_datetimes = {}

    for p in PRAYER_ORDER:
        time_str = timings[p]
        today_str = today.strftime("%Y-%m-%d")
        dt = parser.parse(f"{today_str} {time_str}")
        dt = tz.localize(dt)
        prayer_datetimes[p] = dt

    return prayer_datetimes


def format_time_12h(dt_obj):
    return dt_obj.strftime("%I:%M %p").lstrip("0")


def get_next_prayer_and_remaining(prayer_datetimes):
    now = datetime.now(tz)
    for name in PRAYER_ORDER:
        dt = prayer_datetimes[name]
        if dt > now:
            diff = dt - now
            total_minutes = int(diff.total_seconds() // 60)
            hours = total_minutes // 60
            minutes = total_minutes % 60
            return name, dt, hours, minutes
    return None


def play_adhan_for_prayer(prayer_name):
    filename = ADHAN_FILES.get(prayer_name)
    if not filename:
        return
    try:
        pygame.mixer.music.load(filename)
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play()
    except Exception as e:
        print(f"Error playing adhan for {prayer_name}: {e}")


def is_adhan_playing():
    return pygame.mixer.music.get_busy()


# -----------------------------
# Drawing
# -----------------------------
def draw_text(surface, text, font, color, x, y, center=False):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect()
    if center:
        rect.centerx = x
        rect.top = y
    else:
        rect.topleft = (x, y)
    surface.blit(rendered, rect)
    return rect


def draw_screen(screen, fonts, prayer_datetimes, status_text, adhan_icon):
    screen.fill(BG_COLOR)

    now = datetime.now(tz)

    header_font, small_font, clock_font, medium_font = fonts

    # Header
    y = 6
    draw_text(screen, LOCATION_LABEL, header_font, TEXT_COLOR,
              SCREEN_WIDTH // 2, y, center=True)
    y += header_font.get_linesize() + 2

    date_str = now.strftime("%A, %b %d, %Y")
    draw_text(screen, date_str, small_font, TEXT_COLOR,
              SCREEN_WIDTH // 2, y, center=True)
    y += small_font.get_linesize() + 4

    pygame.draw.line(screen, DIVIDER_COLOR,
                     (20, y), (SCREEN_WIDTH - 20, y), width=1)
    y += 8

    # Clock
    time_str = now.strftime("%I:%M:%S %p").lstrip("0")
    clock_rect = draw_text(screen, time_str, clock_font,
                           TEXT_COLOR, SCREEN_WIDTH // 2, y, center=True)
    y = clock_rect.bottom + 4

    result = get_next_prayer_and_remaining(prayer_datetimes)
    if result:
        name, dt, hours, minutes = result
        nice_time = format_time_12h(dt)
        next_line = f"Next: {name} at {nice_time}"

        # Compute exact remaining seconds
        now = datetime.now(tz)
        diff = dt - now
        total_seconds = int(diff.total_seconds())

        if total_seconds < 60:
            # Less than 1 minute: show only seconds
            if total_seconds < 0:
                total_seconds = 0
            remaining_line = f"{total_seconds} second(s) remaining"
        else:
            # 1 minute or more: keep your original minutes display
            if hours > 0:
                remaining_line = f"{hours} hour(s), {minutes} min remaining"
            else:
                remaining_line = f"{minutes} min remaining"
    else:
        next_line = "All prayers for today have passed"
        remaining_line = ""


    draw_text(screen, next_line, medium_font,
              ACCENT_COLOR, SCREEN_WIDTH // 2, y, center=True)
    y += medium_font.get_linesize() + 2

    if remaining_line:
        draw_text(screen, remaining_line, medium_font,
                  TEXT_COLOR, SCREEN_WIDTH // 2, y, center=True)

    # Prayer List
    list_top_y = SCREEN_HEIGHT // 2 - 20
    label_x = 40
    time_x = SCREEN_WIDTH - 40

    for idx, p in enumerate(PRAYER_ORDER):
        dt = prayer_datetimes[p]
        p_time = format_time_12h(dt)
        row_y = list_top_y + idx * (small_font.get_linesize() + 2)

        draw_text(screen, p, small_font, TEXT_COLOR,
                  label_x, row_y, center=False)

        rendered = small_font.render(p_time, True, TEXT_COLOR)
        rect = rendered.get_rect()
        rect.top = row_y
        rect.right = time_x
        screen.blit(rendered, rect)

    # Adhan Icon
    screen.blit(adhan_icon, (SCREEN_WIDTH - 315, list_top_y + 25))

    # Bottom Bar
    pygame.draw.line(screen, DIVIDER_COLOR,
                     (20, SCREEN_HEIGHT - 35),
                     (SCREEN_WIDTH - 20, SCREEN_HEIGHT - 35),
                     width=1)

    draw_text(screen, status_text, small_font,
              TEXT_COLOR, SCREEN_WIDTH // 2,
              SCREEN_HEIGHT - 30, center=True)


# -----------------------------
# Main
# -----------------------------
def main():
    pygame.init()
    pygame.display.set_caption("Adhan Clock")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    pygame.mixer.init()

    adhan_icon = pygame.image.load("adhan_icon_final.png").convert_alpha()
    adhan_icon = pygame.transform.smoothscale(adhan_icon, (160, 110))

    header_font = pygame.font.SysFont("DejaVu Sans", 18, bold=True)
    small_font = pygame.font.SysFont("DejaVu Sans", 21, bold=True)
    clock_font = pygame.font.SysFont("DejaVu Sans", 32, bold=True)
    medium_font = pygame.font.SysFont("DejaVu Sans", 19, bold=True)
    fonts = (header_font, small_font, clock_font, medium_font)

    status_text = "Fetching today's times..."
    current_date = date.today()
    prayer_datetimes = fetch_prayer_times_for_today()
    status_text = "Running"

    adhan_played_today = {p: False for p in PRAYER_ORDER}

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        now = datetime.now(tz)

        # 60-second trigger window
        for prayer_name in PRAYER_ORDER:
            prayer_time = prayer_datetimes.get(prayer_name)
            if prayer_time is None:
                continue

            diff = (now - prayer_time).total_seconds()

            if 0 <= diff < 60 and not adhan_played_today[prayer_name]:
                if not is_adhan_playing():
                    play_adhan_for_prayer(prayer_name)
                    adhan_played_today[prayer_name] = True
                    status_text = f"Playing Adhan ({prayer_name})"

        # If adhan finished but status still shows "Playing Adhan", revert to "Running"
        if not is_adhan_playing() and status_text.startswith("Playing Adhan"):
            status_text = "Running"


        if date.today() != current_date:
            current_date = date.today()
            prayer_datetimes = fetch_prayer_times_for_today()
            adhan_played_today = {p: False for p in PRAYER_ORDER}
            status_text = "Running"

        draw_screen(screen, fonts, prayer_datetimes, status_text, adhan_icon)
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()
