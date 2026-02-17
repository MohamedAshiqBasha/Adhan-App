import time
import pygame

AUDIO_FILE = "fajr_adhan_final.mp3"  # change to your actual filename

pygame.init()
pygame.mixer.init()

print("Loading audio...")
pygame.mixer.music.load(AUDIO_FILE)
pygame.mixer.music.set_volume(1.0)  # volume between 0.0 and 1.0

print("Playing adhan...")
pygame.mixer.music.play()

# Wait until the audio finishes
while pygame.mixer.music.get_busy():
    time.sleep(0.5)

print("Done.")
pygame.mixer.quit()
pygame.quit()
