import asyncio
import logging
import os
import pathlib
import shutil

from aiogram import Bot, Dispatcher, executor
from aiogram.types import ParseMode, InputMediaPhoto, InputMediaVideo, InputMediaAnimation, InputMediaDocument

from config import BOT_TOKEN, CHATS_LISTENER, CHATS_FOR_SENDING, API_ID, API_HASH, reply_message, video_formats, \
    image_formats, gif_formats

logging.basicConfig(level=logging.INFO)
from telethon.sync import TelegramClient, events, types

bot = Bot(token=BOT_TOKEN)


def is_part_in_list(str_, words):
    for word in words:
        if word.lower() in str_.lower():
            return True
    return False


async def send_media(folder_path, media_type, media, text=""):
    try:
        message_with_media = media
        files = []
        message_text = ""

        for chat in CHATS_FOR_SENDING:
            try:
                if media_type != "group":
                    message_with_media = open(media, "rb")
                else:
                    generated_media = generate_media_array(media, text)
                    message_with_media = generated_media["media"]
                    files = generated_media["files"]

                if text != "" and media_type != "group":
                    message_text = append_caption(chat)
                elif media_type == "group" and message_with_media[0]:
                    message_with_media[0].caption = append_caption(chat)

                if media_type == "photo":
                    await bot.send_photo(chat["chatId"], photo=message_with_media, caption=message_text,
                                         parse_mode=ParseMode.MARKDOWN)
                elif media_type == "video":
                    await bot.send_video(chat["chatId"], video=message_with_media, caption=message_text,
                                         parse_mode=ParseMode.MARKDOWN)
                elif media_type == "animation":
                    await bot.send_animation(chat["chatId"], animation=message_with_media, caption=message_text,
                                             parse_mode=ParseMode.MARKDOWN)
                elif media_type == "document":
                    await bot.send_document(chat["chatId"], document=message_with_media, caption=message_text,
                                            parse_mode=ParseMode.MARKDOWN)
                elif media_type == "group":
                    await bot.send_media_group(chat["chatId"], message_with_media)
                    close_files(files)

            except Exception as ex:
                logging.error(str(ex))

            if media_type != "group":
                message_with_media.close()

        shutil.rmtree(folder_path)
        reply_message = None
    except Exception as ex:
        logging.error(str(ex))


def append_caption(chat) -> str:
    return f"[{chat['urlFollowCaption']}]({chat['urlFollow']}) | [{chat['urlBotCaption']}]({chat['urlBot']})"


def get_file_type(path: str) -> str:
    if path.endswith(gif_formats):
        return "animation"
    elif path.endswith(video_formats):
        return "video"
    elif path.endswith(image_formats):
        return "photo"
    else:
        return "document"


async def save_media(message, folder_path) -> str:
    try:
        if not os.path.exists(folder_path):
            os.mkdir(folder_path)

        path = str((await message.download_media(file=folder_path)).replace("\\", "/"))

        # file_info = os.stat(path)
        # size = file_info.st_size / (1024 * 1024)
        # if size > 55:
        #     folder, filename = os.path.split(path)
        #     clip = moviepy.VideoFileClip(path)
        #
        #     new_path = folder_path+"/covert_"+filename
        #     clip.write_videofile(new_path)
        #
        #     os.remove(path)
        #     path = new_path

        return path
    except Exception as ex:
        logging.error(str(ex))


async def media_message(message):
    folder_path = f"./temp_media/{message.chat_id}_{message.id}"
    path = await save_media(message, folder_path)

    media_type = get_file_type(path)
    await send_media(folder_path, media_type, path, message.text)
    pass


def close_files(files):
    for file in files:
        try:
            file.close()
        except Exception as ex:
            logging.error(str(ex))


def generate_media_array(files_info, caption):
    media = []
    files = []
    n = 0
    for file in files_info:
        media_type = get_file_type(file["path"])
        file = open(file["path"], "rb")
        files.append(file)
        if media_type == "video":
            media.append(InputMediaVideo(file, caption=caption if n == 0 else "",
                                         parse_mode=ParseMode.MARKDOWN))
        elif media_type == "photo":
            media.append(InputMediaPhoto(file, caption=caption if n == 0 else "",
                                         parse_mode=ParseMode.MARKDOWN))
        elif media_type == "animation":
            media.append(InputMediaAnimation(file, caption=caption if n == 0 else "",
                                             parse_mode=ParseMode.MARKDOWN))
        else:
            media.append(InputMediaDocument(file, caption=caption if n == 0 else "",
                                            parse_mode=ParseMode.MARKDOWN))
        n += 1

    return {
        "media": media,
        "files": files
    }


async def group_media_message(message, client, max_amp=10):
    folder_path = f"./temp_media/{message.chat_id}_{message.grouped_id}"
    if message.grouped_id is None:
        return [message] if message.media is not None else []

    search_ids = [i for i in range(message.id - max_amp, message.id + max_amp + 1)]
    posts = await client.get_messages(message.chat_id, ids=search_ids)

    files_info = []
    for post in posts:
        if post is not None and post.grouped_id == message.grouped_id and post.media is not None:
            path = await save_media(post, folder_path)
            files_info.append({"path": path})

    await send_media(folder_path, "group", files_info)


async def getBot():
    result = await bot.get_me()
    print(result)


if __name__ == "__main__":
    with TelegramClient('12403767378', API_ID, API_HASH) as client:
        @client.on(events.NewMessage(chats=CHATS_LISTENER))
        async def handler(event):
            try:
                await getBot()
                message = event.message

                if message.is_reply:
                    reply_message = await event.message.get_reply_message()

                if message.text:
                    if "https" in message.text or "http" in message.text:
                        return

                if message.grouped_id:
                    await group_media_message(message, client)
                elif message.media and not message.grouped_id:
                    await media_message(message)

            except Exception as e:
                print("error: " + str(e))


        client.run_until_disconnected()
