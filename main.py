from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import asyncio
import database
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get bot token from environment variable
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables")

# Initialize the bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()



# Create reply keyboard
keyboard_reply = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="50"),
            KeyboardButton(text="100"),
        ],
        [
            KeyboardButton(text="150"),
            KeyboardButton(text="200")
        ]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# Define the message handler
@dp.message()
async def echo(message: Message):
    # Check if message is a positive integer
    if not message.text.isdigit() or int(message.text) <= 0:
        return
        
    user_id = message.from_user.id
    group_id = message.chat.id if message.chat.type != "private" else None
    topic_id = message.message_thread_id if message.message_thread_id else None

    # topic_id = 1

    if group_id is None or topic_id is None:
        return
    
    async with database.get_session() as session:
        dhikar_type_id = await database.get_dhikar_type_id(session, group_id, topic_id)
        if dhikar_type_id is None:
            return
        dhikar_count = int(message.text)
        await database.create_dhikar_entry(session, user_id=user_id, dhikar_count=dhikar_count, dhikar_type_id=dhikar_type_id)

        total_dhikar, dhikar_title = await database.get_total_dhikar_count(session, dhikar_type_id=dhikar_type_id)
    
    # Add reply message
    await message.reply(f"Added {dhikar_count} to {dhikar_title}\nTotal count: {total_dhikar}", reply_markup=keyboard_reply)

# Main function to start the bot
async def main():
    # Initialize database and create tables
    database.init_db()
    await database.create_tables(database._engine)
    
    print("Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
