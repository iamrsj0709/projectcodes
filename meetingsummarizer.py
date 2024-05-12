import subprocess
import time
import sounddevice as sd
import numpy as np
import deepspeech
import smtplib
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

# Function to join Zoom meeting
def join_zoom_meeting(meeting_link, email, password, chrome_driver_path):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.binary_location = chrome_driver_path
    
    driver = webdriver.Chrome(options=chrome_options)
    
    driver.get(meeting_link)
    wait = WebDriverWait(driver, 30)
    try:
        email_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
        email_field.send_keys(email)
        password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
        password_field.send_keys(password)
        join_button = wait.until(EC.element_to_be_clickable((By.ID, "joinButton")))
        join_button.click()
    except TimeoutException:
        print("Timeout occurred while waiting for elements to load.")
        driver.quit()
        return None
    time.sleep(10)
    return driver

# Function to record audio
def record_audio(duration, fs, channels):
    print("Recording audio...")
    audio_frames = sd.rec(int(duration * fs), samplerate=fs, channels=channels, dtype='int16')
    sd.wait()
    return audio_frames

# Function to transcribe audio using DeepSpeech

def transcribe_audio(audio_data, model_path):
    print("Transcribing audio...")
    model = deepspeech.Model(model_path)
    # Flatten the audio data array
    audio_data_flat = np.ravel(audio_data)
    transcript = model.stt(audio_data_flat)
    return transcript

# Function to send email
def send_email(sender_email, sender_password, receiver_email, subject, message):
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email

    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(sender_email, sender_password)
    server.sendmail(sender_email, receiver_email, msg.as_string())
    server.quit()

def main():
    # Zoom meeting details
    meeting_link = "https://zoom.us/j/97153237863?pwd=eTRYTW5DTTlvY05acWVBNnIxZ2U2Zz09"
    email = "rhyna@onehash.ai"
    password = "ia9VvW"
    chrome_driver_path = '/home/rhyna/neverinstall/chromedriver_linux64'

    # Audio settings
    duration = 10
    fs = 44100
    channels = 2

    # DeepSpeech model path
    model_path = "/home/rhyna/deepspeech-0.9.3-models.pbmm"

    # Sender and receiver email details
    sender_email = "rhyna@onehash.ai"
    sender_password = "uyrt kzwt rgfm vlxh"
    receiver_email = "rsjohn2021@gmail.com"

    # Join Zoom meeting
    driver = join_zoom_meeting(meeting_link, email, password, chrome_driver_path)

    # Record audio
    audio_data = record_audio(duration, fs, channels)

    # Transcribe audio
    transcript = transcribe_audio(audio_data, model_path)
    print("Transcript:", transcript)

    # Send transcription via email
    subject = "Zoom Meeting Transcription"
    message = transcript
    send_email(sender_email, sender_password, receiver_email, subject, message)

    # Close the browser
    if driver:
        driver.quit()

if _name_ == "_main_":
    main()

