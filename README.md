Telegram Bot Project (Aiogram + SQLAlchemy)

This project is a Telegram bot built using Aiogram and SQLAlchemy, developed as a school project.

🚀 Installation & Setup
1️⃣ Create a .env file

After cloning the repository, create a .env file in the root directory and set the following variables:

TOKEN=your_bot_token
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/tg_bot
ADMIN_ID_TG=your_admin_id
SAVE_DIR=your_directory_for_saving_files


Example DATABASE_URL:

postgresql+asyncpg://postgres:password@localhost:5432/tg_bot

2️⃣ Create and activate a virtual environment
python -m venv venv
# Linux / macOS
source venv/bin/activate
# Windows PowerShell
.\venv\Scripts\Activate.ps1

3️⃣ Install dependencies
pip install -r requirements.txt

4️⃣ Update variable values in the code

Replace the values of variables at the following lines:

465, 588, 873, 914

5️⃣ Run the bot
python app.py


🎉 The bot is now running and ready to use!