from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import Integer,String,Boolean,ForeignKey

Base = declarative_base()

# Пользователь
#--------------------------------------------------------------------------------------------
class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)
    tg_id: Mapped[str] = mapped_column(String,nullable=True,default=None)
    username: Mapped[str] = mapped_column(String,nullable=True,default=None)

    possibility_to_add: Mapped[bool] = mapped_column(Boolean,nullable=False)
#--------------------------------------------------------------------------------------------


# Школа
#--------------------------------------------------------------------------------------------
class SchoolORM(Base):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)
    name: Mapped[str] = mapped_column(String,nullable=False)
#--------------------------------------------------------------------------------------------


# Класс
#--------------------------------------------------------------------------------------------
class ClassORM(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)

    school_id: Mapped[int] = mapped_column(Integer,ForeignKey("schools.id"),nullable=True,default=None)

    num: Mapped[str] = mapped_column(String,nullable=False)
    timetable_flag: Mapped[bool] = mapped_column(Boolean,nullable=False)
    timetable_url: Mapped[str] = mapped_column(String,nullable=True)
#--------------------------------------------------------------------------------------------


# Домашнее задание
#--------------------------------------------------------------------------------------------
class HomeworkORM(Base):
    __tablename__ = "homework"

    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)
    # Внешний ключ на класс ClassORM
    class_id: Mapped[int] = mapped_column(Integer,ForeignKey("classes.id"),nullable=False)

    algebra: Mapped[str] = mapped_column(String,default=None,nullable=True)
    geometry: Mapped[str] = mapped_column(String,default=None,nullable=True)
    english_language: Mapped[str] = mapped_column(String,default=None,nullable=True)
    russian_language: Mapped[str] = mapped_column(String,default=None,nullable=True)
    literature: Mapped[str] = mapped_column(String,default=None,nullable=True)
    history: Mapped[str] = mapped_column(String,default=None,nullable=True)
    physics: Mapped[str] = mapped_column(String,default=None,nullable=True)
    chemistry: Mapped[str] = mapped_column(String,default=None,nullable=True)
    biology: Mapped[str] = mapped_column(String,default=None,nullable=True)
    geography: Mapped[str] = mapped_column(String,default=None,nullable=True)
    social_science: Mapped[str] = mapped_column(String,default=None,nullable=True)
    informatics: Mapped[str] = mapped_column(String,default=None,nullable=True)
#--------------------------------------------------------------------------------------------