import telebot
import os
import sqlite3
import subprocess
import time

dir = "/path/to/dir"
bot_token = "YOUR_BOT_TOKEN"
channel_id = "YOUR_CHANNEL_ID"

bot = telebot.TeleBot(bot_token, parse_mode=None)
os.makedirs(dir) if not os.path.exists(dir) else None

db_path = f"{dir}/v2vn.db"
if not os.path.exists(db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE users (\
            id INTEGER PRIMARY KEY, \
            user_id TEXT, \
            full_name TEXT, \
            username TEXT, \
            count TEXT, \
            timestamp INTEGER \
            )')
        cursor.execute('CREATE TABLE files (\
            id INTEGER PRIMARY KEY, \
            user_id TEXT, \
            file_id TEXT, \
            timestamp INTEGER \
            )')
        conn.commit()

def cropvideo(new_path, user_id):
    timestamp = time.time()
    out_path = f"{dir}/download/{user_id}/output_{timestamp}.mp4"
    ffmpeg_cmd = [
        "ffmpeg",
        "-i", new_path,
        "-vf", "scale=512:512",
        "-c:a", "copy",
        "-c:v", "libx264",
        "-crf", "26",
        "-y", out_path
    ]
    subprocess.run(ffmpeg_cmd)
    return out_path

@bot.message_handler(content_types=["video"])
def handle_video(message):
    if message.chat.type == "private":
        user_id = message.from_user.id

        adduser(message)

        file_size = message.video.file_size
        if file_size < 209712520:
            editlater = bot.send_message(user_id, "Downloading...").message_id
            video_fid = message.video.file_id
            file_info = bot.get_file(video_fid)

            download_file = bot.download_file(file_info.file_path)
            os.makedirs(f"{dir}/download/{user_id}/videos", exist_ok=True)
            path = f"{dir}/download/{user_id}/{file_info.file_path}"
            with open(path, "wb") as f:
                f.write(download_file)
            new_fname = message.video.file_name or "notitle.mp4"
            new_path = f"{dir}/download/{user_id}/{message.date}_{new_fname}"
            os.rename(path, new_path)

            try:
                editlater = bot.edit_message_text("Cropping video...", user_id, editlater).message_id
            except:
                pass

            send_video = cropvideo(new_path, user_id)

            try:
                editlater = bot.edit_message_text("Sending back...", user_id, editlater).message_id
            except:
                pass

            with open(send_video, "rb") as vf:
                video_fid = bot.send_video(user_id, vf, reply_to_message_id=message.id, allow_sending_without_reply=True).video.file_id
                bot.send_video(channel_id, video_fid)
            os.remove(send_video)

            try:
                bot.delete_message(user_id, editlater)
            except:
                pass

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET count=COALESCE(count, 0) + 1 \
                    WHERE user_id=?',(user_id,))
                timestamp = message.date
                cursor.execute('INSERT INTO files (user_id, file_id, timestamp) VALUES (?, ?, ?)', \
                    (user_id, video_fid, timestamp))
                conn.commit()
            player = getuser(message)
            logging(f"{player} Made a video.")
            logging(f"File name: {new_fname}") if new_fname != "notitle.mp4" else None
        else:
            bot.send_message(user_id, "File too big. Send a video smaller than 20M.")

            player = getuser(message)
            logging(f"{player} Sent a file bigger than 20MB.")

bot.infinity_polling(timeout=10, long_polling_timeout=5)
