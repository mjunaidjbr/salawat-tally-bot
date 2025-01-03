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

# Load environment variables and parse admin users
ADMIN_USER_IDS = [int(id.strip()) for id in os.getenv('admin_user_ids', '').split(',') if id.strip()]

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

# Add this helper function
async def get_username_by_id(bot: Bot, user_id: int) -> str:
    try:
        chat = await bot.get_chat(user_id)
        if chat.first_name:
            full_name = chat.first_name
            if chat.last_name:
                full_name += f" {chat.last_name}"
            return full_name
        elif chat.username:
            return chat.username
        return f"User{user_id}"  # Fallback if no name or username
    except Exception:
        return f"User{user_id}"  # Fallback if user not found or other errors

# Add this command handler after the existing handlers
@dp.message(lambda message: message.text == "/leader_board")
async def leader_board(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_USER_IDS:  # Check if user is admin
        await message.delete()  # Delete the command message if not admin
        await bot.send_message(
            chat_id=group_id,
            text=f"Imtiaz Noor removed this message",
            message_thread_id=topic_id
        )
        return
        
    group_id = message.chat.id if message.chat.type != "private" else None
    topic_id = message.message_thread_id if message.message_thread_id else None

    if group_id is None or topic_id is None:
        return

    async with database.get_session() as session:
        dhikar_type_id = await database.get_dhikar_type_id(session, group_id, topic_id)
        if dhikar_type_id is None:
            return

        result = await database.get_top_contributors(session, dhikar_type_id)
        
        if not result["contributors"]:
            await message.reply("No contributions yet!")
            return

        # Format the leaderboard message with three columns
        leaderboard_text = "🏆 𝗟𝗘𝗔𝗗𝗘𝗥𝗕𝗢𝗔𝗥𝗗 🏆\n"
        leaderboard_text += "\n"
        leaderboard_text += f"📿 {result['dhikar_title']} 📿\n\n"
        
        # Header with exact spacing
        leaderboard_text += "𝗥𝐚𝐧𝐤    𝐔𝐬𝐞𝐫      𝐂𝐨𝐮𝐧𝐭\n"

        medals = ["🥇", "🥈", "🥉"]
        
        for contributor in result["contributors"]:
            username = await get_username_by_id(bot, contributor["user_id"])
            rank = contributor['rank']
            
            # Adjust username length and padding (20 spaces)
            username = (username[:17] + '...') if len(username) > 17 else username
            
            
            # Rank display (5 spaces)
            rank_display = medals[rank - 1] if rank <= 3 else str(rank)
            
            
            # Count with exactly 5 spaces, right-aligned with spaces
            count = str(contributor['total_dhikar'])
            
            leaderboard_text += f"{rank_display} | {username} ⮕ {count}\n\n"


        await message.reply(leaderboard_text)

# Define the message handler
@dp.message()
async def echo(message: Message):
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_USER_IDS
    
    group_id = message.chat.id if message.chat.type != "private" else None
    topic_id = message.message_thread_id if message.message_thread_id else None

    if group_id is None or topic_id is None:
        return
    



    async with database.get_session() as session:
        dhikar_type_id = await database.get_dhikar_type_id(session, group_id, topic_id)
        if dhikar_type_id is None:
            return
        

        # Allow any message from admins, but for others, check if it's an integer (positive or negative)
        if not is_admin:
            try:
                int(message.text)
            except ValueError:
                # Delete invalid message from non-admin users
                await message.delete()
                await bot.send_message(
                    chat_id=group_id,
                    text=f"Imtiaz Noor removed this message",
                    message_thread_id=topic_id
                )
                return
        else:
            try:
                int(message.text)
            except ValueError:
                return
        dhikar_count = int(message.text)
        if dhikar_count > 0:
            await database.create_dhikar_entry(session, user_id=user_id, dhikar_count=dhikar_count, dhikar_type_id=dhikar_type_id)

            total_dhikar, dhikar_title = await database.get_total_dhikar_count(session, dhikar_type_id=dhikar_type_id)
    
            # Add reply message
            # await message.reply(f"You added {dhikar_count} to {dhikar_title}\nTotal count: {total_dhikar}", reply_markup=keyboard_reply)
            username = await get_username_by_id(bot, user_id)
            await message.reply(
                f"{username} added {dhikar_count} to {dhikar_title}\nTotal count: {total_dhikar}", 
                reply_markup=keyboard_reply
            )
        else:
            if dhikar_count == 0:
                # Delete invalid message from non-admin users
                await message.delete()
                await bot.send_message(
                    chat_id=group_id,
                    text=f"Imtiaz Noor removed this message",
                    message_thread_id=topic_id
                )
                return
         
            dhikar_count = int(int(message.text) * -1)
            row_deleted = await database.delete_last_dhikar_entry(session=session,user_id=user_id,dhikar_type_id=dhikar_type_id,dhikar_count=dhikar_count)
            if row_deleted:
                # Get updated total after deletion
                total_dhikar, dhikar_title = await database.get_total_dhikar_count(session, dhikar_type_id=dhikar_type_id)
                await bot.send_message(
                    chat_id=group_id,
                    text=f"Deleted {dhikar_count} from {dhikar_title}\nTotal count: {total_dhikar}",
                    reply_markup=keyboard_reply,
                    message_thread_id=topic_id
                )
            else:
                # Delete invalid message from non-admin users
                await message.delete()
                await bot.send_message(
                    chat_id=group_id,
                    text=f"Imtiaz Noor removed this message",
                    message_thread_id=topic_id
                )
                






# Main function to start the bot
async def main():
    # Initialize database and create tables
    database.init_db()
    await database.create_tables(database._engine)
    
    print("Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
