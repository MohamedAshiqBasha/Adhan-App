import time
from datetime import datetime, date
from datetime import datetime, date, timedelta

import requests
import pygame
import pytz
from dateutil import parser
import os


# -----------------------------
# Configuration
# -----------------------------
LAT = 29.6585
LNG = -95.7336
METHOD = 2
TZ_NAME = "America/Chicago"
LOCATION_LABEL = "77407 – Richmond, TX"

PRAYER_ORDER = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]

SCREEN_WIDTH = 480   # adjust for your 3.5" screen
SCREEN_HEIGHT = 320

BG_COLOR = (13, 13, 13)
TEXT_COLOR = (242, 242, 242)
ACCENT_COLOR = (0, 150, 136)  # teal
DIVIDER_COLOR = (60, 60, 60)

tz = pytz.timezone(TZ_NAME)

# Optional test flag (leave False for real use)
DEBUG_FAKE_TIMES = False


# -----------------------------
# Adhan audio configuration (ADDED)
# -----------------------------
ADHAN_FILES = {
    "Fajr": "fajr_adhan_final.mp3",
    "Dhuhr": "normal_adhan_final.mp3",
    "Asr": "normal_adhan_final.mp3",
    "Maghrib": "normal_adhan_final.mp3",
    "Isha": "normal_adhan_final.mp3",
}

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


# -----------------------------
# Adhan playback helper (ADDED)
# -----------------------------
def play_adhan_for_prayer(prayer_name):
    filename = ADHAN_FILES.get(prayer_name)
    if not filename:
        print("DEBUG: No filename for prayer", prayer_name)
        return
    full_path = asset_path(filename)
    try:
        print("DEBUG: Loading file", full_path)
        pygame.mixer.music.load(full_path)
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play()
        print("DEBUG: Started playing", full_path)
    except Exception as e:
        print(f"Error playing adhan for {prayer_name}: {e}")


# -----------------------------
# Pygame drawing helpers
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


def draw_screen(screen, fonts, prayer_datetimes, status_text):
    screen.fill(BG_COLOR)

    now = datetime.now(tz)

    header_font, small_font, clock_font, medium_font = fonts

    # 1) Top header: location + date
    y = 6
    draw_text(
        screen,
        LOCATION_LABEL,
        header_font,
        TEXT_COLOR,
        SCREEN_WIDTH // 2,
        y,
        center=True,
    )
    y += header_font.get_linesize() + 2

    date_str = now.strftime("%A, %b %d, %Y")
    draw_text(
        screen, date_str, small_font, TEXT_COLOR, SCREEN_WIDTH // 2, y, center=True
    )
    y += small_font.get_linesize() + 4

    pygame.draw.line(
        screen, DIVIDER_COLOR, (20, y), (SCREEN_WIDTH - 20, y), width=1
    )
    y += 8

    # 2) Main clock
    time_str = now.strftime("%I:%M:%S %p").lstrip("0")
    clock_rect = draw_text(
        screen,
        time_str,
        clock_font,
        TEXT_COLOR,
        SCREEN_WIDTH // 2,
        y,
        center=True,
    )
    y = clock_rect.bottom + 4

    # 3) Next prayer section
    result = get_next_prayer_and_remaining(prayer_datetimes)
    if result is None:
        next_line = "All prayers for today have passed"
        remaining_line = ""
    else:
        name, dt, hours, minutes = result
        nice_time = format_time_12h(dt)
        next_line = f"Next: {name} at {nice_time}"
        if hours > 0:
            remaining_line = f"{hours} hour(s), {minutes} min remaining"
        else:
            remaining_line = f"{minutes} min remaining"

    draw_text(
        screen, next_line, medium_font, ACCENT_COLOR, SCREEN_WIDTH // 2, y, center=True
    )
    y += medium_font.get_linesize() + 2

    if remaining_line:
        draw_text(
            screen,
            remaining_line,
            medium_font,
            TEXT_COLOR,
            SCREEN_WIDTH // 2,
            y,
            center=True,
        )

    # 4) Daily prayer list (bottom half)
    list_top_y = SCREEN_HEIGHT // 2 - 20
    label_x = 40
    time_x = SCREEN_WIDTH - 40

    for idx, p in enumerate(PRAYER_ORDER):
        dt = prayer_datetimes[p]
        p_time = format_time_12h(dt)
        row_y = list_top_y + idx * (small_font.get_linesize() + 2)
        draw_text(screen, p, small_font, TEXT_COLOR, label_x, row_y, center=False)
        # right aligned time
        rendered = small_font.render(p_time, True, TEXT_COLOR)
        rect = rendered.get_rect()
        rect.top = row_y
        rect.right = time_x
        screen.blit(rendered, rect)

    # Draw single adhan icon to the right of the prayer labels (ADDED)
    try:
        icon_width = 160
        icon_height = 110
        icon_x = SCREEN_WIDTH - 315
        icon_y = list_top_y + 15
        screen.blit(
            pygame.transform.smoothscale(
                pygame.image.load(asset_path("adhan_icon_final.png")).convert_alpha(),
                (icon_width, icon_height)
            ),
            (icon_x, icon_y)
        )
    except Exception as e:
        print(f"Error drawing adhan icon: {e}")

    # 5) Bottom status bar
    pygame.draw.line(
        screen,
        DIVIDER_COLOR,
        (20, SCREEN_HEIGHT - 35),
        (SCREEN_WIDTH - 20, SCREEN_HEIGHT - 35),
        width=1,
    )

    draw_text(
        screen,
        status_text,
        small_font,
        TEXT_COLOR,
        SCREEN_WIDTH // 2,
        SCREEN_HEIGHT - 30,
        center=True,
    )


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def asset_path(name):
    return os.path.join(SCRIPT_DIR, name)


# -----------------------------
# Main loop
# -----------------------------
def main():
    pygame.init()
    pygame.display.set_caption("Adhan Clock")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    # Initialize mixer for audio (ADDED)
    pygame.mixer.init()

    # Load adhan icon image (ADDED)
    adhan_icon = pygame.image.load(asset_path("adhan_icon_final.png")).convert_alpha()
    adhan_icon = pygame.transform.smoothscale(adhan_icon, (80, 80))

    header_font = pygame.font.SysFont("DejaVu Sans", 18, bold=True)
    small_font = pygame.font.SysFont("DejaVu Sans", 21, bold=True)
    clock_font = pygame.font.SysFont("DejaVu Sans", 32, bold=True)
    medium_font = pygame.font.SysFont("DejaVu Sans", 19, bold=True)
    fonts = (header_font, small_font, clock_font, medium_font)

    status_text = "Fetching today's times..."
    current_date = date.today()
    prayer_datetimes = fetch_prayer_times_for_today()
    status_text = "Running"

    # track last minute we updated (for "remaining" changes)
    last_minute = -1

    # track last prayer for which adhan was played (ADDED)
    last_adhan_prayer = None

    running = True
    while running:
        # event handling (needed to allow close)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # DEBUG: press 'a' key to play Fajr adhan manually (ADDED)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_a:
                print("DEBUG: Manual trigger for Fajr")
                play_adhan_for_prayer("Fajr")

        now = datetime.now(tz)

        # New day detection
        if date.today() != current_date:
            current_date = date.today()
            status_text = "Updating times..."
            prayer_datetimes = fetch_prayer_times_for_today()
            status_text = "Running"
            # reset adhan tracking for new day (ADDED)
            last_adhan_prayer = None

        # Only recompute remaining once per minute
        if now.minute != last_minute:
            last_minute = now.minute

        # Check if it's time to play adhan (FINAL LOGIC)
        result = get_next_prayer_and_remaining(prayer_datetimes)
        if result is not None:
            next_name, next_dt, hours, minutes = result
            # Trigger when remaining time reaches 0 minutes, once per prayer
            if hours == 0 and minutes == 0 and last_adhan_prayer != next_name:
                print("DEBUG: Triggering adhan for", next_name, "at", now, "scheduled", next_dt)
                play_adhan_for_prayer(next_name)
                print("DEBUG: mixer busy?", pygame.mixer.music.get_busy())
                last_adhan_prayer = next_name
                status_text = f"Playing Adhan ({next_name})"

        draw_screen(screen, fonts, prayer_datetimes, status_text)
        pygame.display.flip()

        clock.tick(30)  # 30 FPS for smooth clock seconds

    pygame.quit()


if __name__ == "__main__":
    main()
