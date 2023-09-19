#!/usr/bin/env python
# coding: utf-8

# In[9]:


import telebot
import requests
from PIL import Image, ImageDraw, ImageFont
from telebot import types
from io import BytesIO
from datetime import datetime
import os


# In[ ]:


TOKEN = os.environ.get("IC_TELEGRAM_BOT_TOKEN")


# In[ ]:


bot = telebot.TeleBot(TOKEN)


# In[ ]:


user_states = {}


# In[ ]:


image_content = None


# In[ ]:


@bot.message_handler(commands = ["start"])
def send_welcome(message):
    print("Handler [send_welcome] called with message:", message.text)
    bot.reply_to(message,"Привет, я Ваш фото-бот! Загрузите фото, и я помогу его обработать!")


# In[12]:


def mirror_image(image_content):
    with Image.open(BytesIO(image_content)) as im:
        im_mirror = im.transpose(Image.FLIP_LEFT_RIGHT)
        output = BytesIO()
        im_mirror.save(output, format="JPEG")  # или другой формат, если необходимо
        output.seek(0)
    return output


# In[ ]:


def convert_to_static(image_path):
    with Image.open(image_path) as img:
        img.seek(0)  # переходим к первому кадру
        img.save(image_path, "PNG")  # сохраняем первый кадр как PNG


# In[ ]:


def random_sticker():
    print("Function [random_sticker] called.")
    API_KEY = "zg2XR3iT0gRRtkVIekgORsl7kUDcnJiq"
    response = requests.get("https://api.giphy.com/v1/stickers/random", params={"api_key": API_KEY})
    
    if response.status_code == 200:
        json_data = response.json()
        sticker_url = json_data["data"]["images"]["downsized"]["url"]
        
        # Скачиваем стикер
        response_image = requests.get(sticker_url)
        if response_image.status_code == 200:
            image_path = "downloaded_sticker.png"
            with open(image_path, "wb") as file:
                file.write(response_image.content)
            
            # Конвертируем стикер в статическое изображение
            convert_to_static(image_path)
            return image_path
        else:
            print("Error downloading sticker:", response_image.status_code)
            return None
    else:
        print("Error:", response.status_code)
        return None


# In[11]:


def add_sticker(image_path):
    print("Function [add_sticker] called with image_path:", image_path)
    sticker_path = random_sticker()  # это локальный путь к файлу, а не URL
    if sticker_path:
        with Image.open(image_path) as img:
            # Конвертируем изображение в RGBA, если это необходимо
            if img.mode != 'RGBA':
                img = img.convert('RGBA')

            sticker = Image.open(sticker_path)

            if sticker.mode != 'RGBA':
                sticker = sticker.convert('RGBA')

            # Удаляем однотонный фон стикера
            datas = sticker.getdata()
            newData = []
            for item in datas:
                # Если альфа-канал выше порога (в данном случае 50)
                if item[3] > 50:
                    newData.append((item[0], item[1], item[2], 255))
                else:
                    newData.append((255, 255, 255, 0))  # полностью прозрачный пиксель с белым RGB
            sticker.putdata(newData)
            
            # Создаем маску из альфа-канала стикера
            mask = sticker.split()[3]  # A channel
            
            x_position = (img.width - sticker.width) // 2
            y_position = img.height - sticker.height
            img.paste(sticker, (x_position, y_position), mask)

            img = img.convert("RGB")
            output_path = "image_with_sticker.jpg"
            img.save(output_path, "JPEG")
            
        os.remove(sticker_path)  # удаляем временный файл стикера
        return output_path
    else:
        print("Failed to get sticker.")
        return image_path


# In[ ]:


def is_valid_date(date_str, format="%d.%m.%Y"):
    try:
        # Пытаемся преобразовать строку в дату
        datetime.strptime(date_str, format)
        return True
    except ValueError:
        return False


# In[ ]:


def add_date(image_content,date, message):
    print("Function [add_date] called with date:", date)
    if is_valid_date(date):
        with Image.open(BytesIO(image_content)) as img:
            draw = ImageDraw.Draw(img)
            font = ImageFont.truetype("ArialRegular.ttf", 25)  # Выберите подходящий шрифт и размер
            draw.text((40, 40), date, font=font, fill="red")  # Вы можете изменить координаты и цвет
            output = BytesIO()
            img.save(output, format="JPEG")  # или другой формат, если необходимо
            output.seek(0)
        return output
    else:
        bot.send_message(message.chat.id, "Ошибка формата даты")


# In[13]:


def request_date(message):
    bot.send_message(message.chat.id, "Введите дату в формате ДД.ММ.ГГГГ")
    user_states[message.chat.id] = "awaiting_date"
    print("Setting user state:", message.chat.id, "to awaiting_date")


# In[ ]:


@bot.message_handler(content_types = ["photo"])
def handle_photo(message):
    print("Handler [handle_photo] called with message:", message.text)
    global image_content
    markup = types.ReplyKeyboardMarkup(row_width=3)
    item1 = types.KeyboardButton("Отзеркалить")
    item2 = types.KeyboardButton("Добавить стикер")
    item3 = types.KeyboardButton("Добавить дату")
    markup.add(item1, item2, item3)
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)
    image_path = bot.get_file(message.photo[-1].file_id).file_path 
    image_content = requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{image_path}").content
    user_states[str(message.chat.id) + "_image"] = image_content


# In[ ]:


#ОТЗЕРКАЛИТЬ
@bot.message_handler(func=lambda message: message.text == "Отзеркалить")
def handle_photo2(message):
    print("Handler [handle_photo2] called with message:", message.text)
    image_content = user_states.get(str(message.chat.id) + "_image")
    if image_content:
        mirrored_image = mirror_image(image_content)
        bot.send_photo(message.chat.id, mirrored_image)
    else:
        # Отправить сообщение пользователю, если изображение не найдено
        bot.send_message(message.chat.id, "Изображение не найдено!")  


# In[ ]:


#СЛУЧАЙНЫЙ СТИКЕР
@bot.message_handler(func=lambda message: message.text == "Добавить стикер")
def handle_photo3(message):
    print("Handler [handle_photo3] called with message:", message.text)
    image_content = user_states.get(str(message.chat.id) + "_image")
    if image_content:
        with open(add_sticker(BytesIO(image_content)), 'rb') as stick_added_image:
            bot.send_photo(message.chat.id, stick_added_image)
    else:
        # Отправить сообщение пользователю, если изображение не найдено
        bot.send_message(message.chat.id, "Изображение не найдено!")


# In[ ]:


@bot.message_handler(func = lambda message: message.text == "Добавить дату")
def handle_photo4(message):
    print("Handler [handle_photo4] called with message:", message.text)
    request_date(message)


# In[ ]:


@bot.message_handler(content_types=["text"])
def handle_text(message):
    print("Handler [handle_text] called with message:", message.text)
    if user_states.get(message.chat.id) == "awaiting_date":
        print("Current user state for", message.chat.id, "is awaiting_date")
        date = message.text
        image_content = user_states.get(str(message.chat.id) + "_image")
        
        if image_content:
            output_image = add_date(image_content, date, message)
            bot.send_photo(message.chat.id, output_image)
            del user_states[message.chat.id]
            del user_states[str(message.chat.id) + "_image"]
        else:
            # Отправить сообщение пользователю, если изображение не найдено
            bot.send_message(message.chat.id, "Изображение не найдено!")


# In[ ]:


print("Бот запущен!")


# In[ ]:


if __name__ == "__main__":
    bot.polling(none_stop=True)

