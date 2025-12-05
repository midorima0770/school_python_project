from dotenv import load_dotenv
from dataclasses import dataclass
import os 

load_dotenv()

@dataclass
class Config:
    token: str
    database_url: str
    admin_id_tg: str
    save_dir: str

def load_config() -> Config:
    return Config(
        token=os.getenv("TOKEN"),
        database_url=os.getenv("DATABASE_URL"),
        admin_id_tg=os.getenv("ADMIN_ID_TG"),
        save_dir=os.getenv("SAVE_DIR"),
    )

config_cl = load_config()