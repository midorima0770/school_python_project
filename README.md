This is a telegram bot project on the aiogram + sqlalchemy framework that I wrote for a school project.

1).Therefore, at the beginning, after pull, create a .env file in which you pass the following values:
    TOKEN
    DATABASE_URL 
    ADMIN_ID_TG
    SAVE_DIR

Here is an example of DATABASE_URL : "postgresql+asyncpg://postgres:password@localhost:5432/tg_bot"

2).The next step is to create venv and activate it.

3).Download all dependencies via pip using the command:
  pip install -r requirements.txt

4).Run app.py and that's it.