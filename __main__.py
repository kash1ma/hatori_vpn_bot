import os
from os import getenv
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InputFile, FSInputFile, URLInputFile
from aiogram.dispatcher.router import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
import asyncio
import paramiko
import time


load_dotenv()

#general settings
TOKEN = getenv("BOT_TOKEN")
VPN_SERVER_IP = "45.9.74.10"
SSH_USERNAME = "root"
SSH_PASSWORD = getenv("PASSWORD")
SCRIPT_PATH = "/root/script.py"
OUTPUT_DIR = "/root/clients"
LOCAL_DOWNLOAD_DIR = "./downloads"
CA_PASSPHRASE = getenv("CA_PASSPHRASE")
BOT_PASSWORD = getenv("BOT_PASSWORD")

# All handlers should be attached to the Router (or Dispatcher)
# Initialize bot and dispatcher
bot = Bot(token=TOKEN)
router = Router()
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)

# Temporary storage for user inputs
user_inputs = {}

# Command handler to start the bot
@router.message(Command("start"))
async def start_command(message: Message):
    await message.answer("Welcome! Send /generate to create a VPN config.")

# Handle /generate command
@router.message(Command("generate"))
async def ask_password(message: Message):
    await message.answer("Please enter the bot password to proceed.")
    user_inputs[message.from_user.id] = {"step": "awaiting_password"}

async def ask_config_name(message: Message):
    
    await message.answer("Please provide a name for your VPN configuration.")
    user_inputs[message.from_user.id] = {"step": "awaiting_name"}

# Handle user input dynamically
@router.message(lambda message: message.from_user.id in user_inputs)
async def handle_user_input(message: Message):
    user_id = message.from_user.id
    step = user_inputs[user_id].get("step")

    if step == "awaiting_password":
        if message.text == BOT_PASSWORD:
            await message.answer("Password correct. Please provide a name for your VPN configuration.")
            user_inputs[user_id]["step"] = "awaiting_name"
        else:
            await message.answer("Incorrect password. Please try again or use /generate to start over.")
            user_inputs.pop(user_id, None)

    if step == "awaiting_name":
        user_inputs[user_id]["config_name"] = message.text
        await message.answer("Generating your VPN configuration. Please wait...")
        await generate_vpn_config(message)
        user_inputs.pop(user_id, None)

# Function to generate VPN config
async def generate_vpn_config(message: Message):
    user_id = message.from_user.id
    config_name = user_inputs[user_id]["config_name"]

    try:
        # Connect to the VPN server
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPN_SERVER_IP, username=SSH_USERNAME, password=SSH_PASSWORD)

        # Start the script and provide inputs
        stdin, stdout, stderr = ssh.exec_command(f"python3 {SCRIPT_PATH}")
        stdin.write(config_name + "\n")
        stdin.flush()
        time.sleep(4)
        stdin.write(CA_PASSPHRASE + "\n")
        stdin.flush()


        # Assuming the output contains the name of the generated config file
        config_file_name = f"{config_name}.ovpn"
        remote_file_path = os.path.join(OUTPUT_DIR, config_file_name)
        local_file_path = os.path.join(LOCAL_DOWNLOAD_DIR, config_file_name)

        # Download the config file
        message.answer(f"Downloading config file: {remote_file_path}")
        sftp = ssh.open_sftp()
        os.makedirs(LOCAL_DOWNLOAD_DIR, exist_ok=True)
        sftp.get(remote_file_path, local_file_path)
        sftp.close()
        ssh.close()

        # Send the config file to the user
        input_file = FSInputFile(local_file_path)
        await message.answer("Here is your OpenVPN configuration file:")
        await message.answer_document(FSInputFile(local_file_path, filename=config_file_name))
    except Exception as e:
        await message.answer(f"An error occurred: {e}")

# Main entry point
async def main():
    # Start the bot
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())