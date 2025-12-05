from aiogram import Router, F,Bot,Dispatcher,types
from aiogram.filters import CommandStart,Command
from aiogram.types import Message, CallbackQuery, BotCommand
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters.state import StateFilter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import asyncio
from config import load_config
from database import create_all_tables,drop_all_tables,engine,get_async_db,create_all_schools
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from models import UserORM,ClassORM,HomeworkORM
from datetime import datetime, timedelta
from func import validate_class_name,validate_school_name,is_admin,get_subject_english,ask_apifreellm,find_file_by_partial_name
import os

router = Router()

config_cl = load_config()
bot = Bot(token=config_cl.token)
dp = Dispatcher()

dp.include_router(router)

class GetBookState(StatesGroup):
    # Для получение книги
    waiting_for_name_book = State()

class SaveBooksState(StatesGroup):
    # Для получения названия книги
    waiting_for_name_book = State()
    # Для получения файла книги
    waiting_for_file_book = State()

class SendMessChatGPR(StatesGroup):
    # Для обидания сообщения для chatgpt
    waiting_message_for_chatgpt = State()

class AddHomeworkState(StatesGroup):
    # Для ожидания школы
    waiting_for_school_homework = State()
    # Для ожидания класса
    waiting_for_class_homework = State()
    # Для ожидания предмета
    waiting_subject_at_school_homework = State()
    # Для ожидания дз
    waiting_homework = State()

class GetHomeworkState(StatesGroup):
    get_homework = State()

class AddTimetableState(StatesGroup):
    # Для ожидания школы
    waiting_for_school = State()
    # Для ожидания класса
    waiting_for_class = State()
    # Для ожидания фотки расписания
    waiting_for_photo = State()
    # Для просмотра расписания - ожидание школы
    waiting_for_school_for_timetable = State()
    # Для просмотра расписания - ожидание класса
    waiting_for_class_for_timetable = State()


class AppointAdminState(StatesGroup):
    # Для назначения admin
    waiting_for_user_id_for_appoint_admin = State()
    # Для снятия admin
    waiting_for_user_id_for_remove_admin = State()

# Создаем клавиатуру с кнопкой отмены
def get_cancel_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

# Клавиатура для скрытия кнопок
remove_keyboard = types.ReplyKeyboardRemove()

# ФУНКЦИЯ ДЛЯ УСТАНОВКИ КОМАНД МЕНЮ
# -------------------------------------------------------------------------------------------------
async def set_main_menu(bot: Bot):
    """Установка команд меню для всех пользователей"""
    main_menu_commands = [
        BotCommand(command='/commands', description='📋 Показать все команды'),
        BotCommand(command='/timetable', description='📅 Посмотреть расписание'),
        BotCommand(command='/get_homework', description='📚 Получить домашнее задание'),
        BotCommand(command='/send_chatgpt',description='ИИ ассиснет'),
        BotCommand(command='/get_book',description='Книги')
    ]
    await bot.set_my_commands(main_menu_commands)
# -------------------------------------------------------------------------------------------------

# Универсальный обработчик для кнопки отмены
# -------------------------------------------------------------------------------------------------
@dp.message(F.text == "❌ Отмена")
async def cancel_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer("Нет активных действий для отмену.", reply_markup=remove_keyboard)
        return
    
    await state.clear()
    await message.answer("Действие отменено. Вы можете начать заново.", reply_markup=remove_keyboard)
# -------------------------------------------------------------------------------------------------


# ОБРАБОТКА СТАРТА
# -------------------------------------------------------------------------------------------------
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(f"Привет!Для получение всех команд используй - /commands")
    user_id = message.from_user.id
    username_t = message.from_user.username

    # Устанавливаем команды меню
    await set_main_menu(bot)

    if user_id == int(config_cl.admin_id_tg):
        new_user = UserORM(
            tg_id=str(user_id),
            username=username_t,
            possibility_to_add=True
        )
    else:
        new_user = UserORM(
            tg_id=str(user_id),
            username=username_t,
            possibility_to_add=False
        )

    async with get_async_db() as session:  
        try:
            result = await session.execute(select(UserORM).where(UserORM.tg_id == str(user_id)))
            flag = result.scalars().one_or_none()
            if not flag:
                session.add(new_user)
                await session.commit()
        except IntegrityError:
            await session.rollback()
        except Exception as e:
            await session.rollback()
            print(f"Произошла ошибка: {str(e)}")
# -------------------------------------------------------------------------------------------------


# НАЗНАЧЕНИЕ АДМИНА
# -------------------------------------------------------------------------------------------------
@dp.message(Command("appoint_admin"),F.from_user.id == int(config_cl.admin_id_tg))
async def appoint_admin(message: Message, state: FSMContext):

    await state.set_state(AppointAdminState.waiting_for_user_id_for_appoint_admin)

    await message.answer("Напишите user.id: ", reply_markup=get_cancel_keyboard())

# State для добавления admin
@dp.message(StateFilter(AppointAdminState.waiting_for_user_id_for_appoint_admin))
async def waiting_for_user_id(message: Message, state: FSMContext):
    # Проверяем нажатие кнопки отмены
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление админа отменено.", reply_markup=remove_keyboard)
        return
    
    data = await state.get_data()
    previous_state = data.get("previous_state")
    bot_messages_ids = data.get("bot_messages_ids", [])

    user_id = message.text.strip()

    async with get_async_db() as session:  
        try:
           result = await session.execute(select(UserORM).where(UserORM.tg_id==str(user_id)))
           user_flag = result.scalars().one_or_none()

           if not user_flag:
               await message.answer(f"Пользователя с таким id: {user_flag.tg_id} , не существует")
               return
           else:
               user_flag.possibility_to_add = True
               await session.commit()

        except Exception as e:
            await message.answer(f"Ошибка: {e}")

    await message.answer(f"Вы успешно назначили админа")
    await state.clear()
# -------------------------------------------------------------------------------------------------





# СНЯТИЕ АДМИНА 
# -------------------------------------------------------------------------------------------------
@dp.message(Command("remove_admin"),F.from_user.id == int(config_cl.admin_id_tg))
async def appoint_admin(message: Message, state: FSMContext):

    await state.set_state(AppointAdminState.waiting_for_user_id_for_remove_admin)

    await message.answer("Напишите user.id: ", reply_markup=get_cancel_keyboard())

# State для снятия admin
@dp.message(StateFilter(AppointAdminState.waiting_for_user_id_for_remove_admin))
async def waiting_for_user_id(message: Message, state: FSMContext):
    # Проверяем нажатие кнопки отмены
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Снятие админа отменено.", reply_markup=remove_keyboard)
        return
    
    data = await state.get_data()
    previous_state = data.get("previous_state")
    bot_messages_ids = data.get("bot_messages_ids", [])

    user_id = message.text.strip()

    async with get_async_db() as session:  
        try:
           result = await session.execute(select(UserORM).where(UserORM.tg_id==str(user_id)))
           user_flag = result.scalars().one_or_none()

           if not user_flag:
               await message.answer(f"Пользователя с таким id: {user_flag.tg_id} , не существует")
               return
           else:
               user_flag.possibility_to_add = False
               await session.commit()

        except Exception as e:
            await message.answer(f"Ошибка: {e}")

    await message.answer(f"Вы успешно сняли админа")
    await state.clear()
# -------------------------------------------------------------------------------------------------





# ПРОСМОТР ВСЕХ КОМАНД
# -------------------------------------------------------------------------------------------------
@dp.message(Command("commands"))
async def get_all_comands(message: Message, state: FSMContext):
    # Проверяем нажатие кнопки отмены
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Просмотр команд отменен.", reply_markup=remove_keyboard)
        return

    user_id = message.from_user.id 
    username_t = message.from_user.username

    async with get_async_db() as session:  
        try:   
            result = await session.execute(select(UserORM).where(UserORM.tg_id == str(user_id)))
            user = result.scalars().one_or_none()

        except Exception as e:
            await message.answer(f"Ошибка: {e}")
            return
        
    if not user:
        if user_id == int(config_cl.admin_id_tg):
            new_user = UserORM(
                tg_id=str(user_id),
                username=username_t,
                possibility_to_add=True
            )
        else:
            new_user = UserORM(
                tg_id=str(user_id),
                username=username_t,
                possibility_to_add=False
            )
        async with get_async_db() as session:  
            try:
                result = await session.execute(select(UserORM).where(UserORM.tg_id == str(user_id)))
                flag = result.scalars().one_or_none()
                if not flag:
                    session.add(new_user)
                    await session.commit()
            except IntegrityError:
                await session.rollback()
            except Exception as e:
                await session.rollback()
                print(f"Произошла ошибка: {str(e)}")
        return

    if user.tg_id == config_cl.admin_id_tg:
        await message.answer(f"Привет!Вот основные команды для работы:\n    /commands - показывает все доступные тебе команды,\n    /show_users - показывает всех пользователей,\n    /add_timetable - для добавления расписания,\n    /timetable - для просмотра расписания,\n    /appoint_admin - для добавления админа,\n    /remove_admin - для снятия админа,\n    /add_homework - добавление дз,\n    /send_chatgpt - ии ассиснет,\n    /add_book - добавление учебников,\n    /get_book - получнеие книги")
    elif user.possibility_to_add and user.tg_id != int(config_cl.admin_id_tg):
        await message.answer(f"Привет!Вот основные команды для работы:\n    /commands - показывает все доступные тебе команды,\n    /add_timetable - для добавления расписания,\n    /timetable - для просмотра расписания,\n    /add_homework - добавление дз,\n    /send_chatgpt - ии ассиснет,\n    /add_book - добавление учебников,\n    /get_book - получнеие книги")
    elif not user.possibility_to_add and user.tg_id != int(config_cl.admin_id_tg):
        await message.answer(f"Привет!Вот основные команды для работы:\n    /commands - показывает все доступные тебе команды,\n    /timetable - для просмотра расписания,\n    /send_chatgpt - ии ассиснет,\n    /get_book - получнеие книги")
# -------------------------------------------------------------------------------------------------






# ПРОСМОТР ВСЕХ ПОЛЬЗОВАТЕЛЕЙ
# -------------------------------------------------------------------------------------------------
@dp.message(Command("show_users"),F.from_user.id == int(config_cl.admin_id_tg))
async def handle_message(message: Message):
    
    async with get_async_db() as session:  
        try:
            result = await session.execute(select(UserORM))
            users = result.scalars().all()

            result = []
            for user in users:
                result.append(
                    {
                        "username":user.username,
                        "id":user.tg_id
                    }
                )

            if users:
                await message.answer(f'Пользователи: {result}')
            else:
                await message.answer(f'Пользователей нету')
        except Exception as e:
            await message.answer(f"Ошибка: {e}")
# -------------------------------------------------------------------------------------------------








# ДОБАВЛЕНИЕ РАСПИСАНИЯ
# -------------------------------------------------------------------------------------------------
@dp.message(Command("add_timetable"))
async def add_timetable(message: Message, state: FSMContext):

    if not await is_admin(str(message.from_user.id)):
        await message.answer("У вас нет прав для использования этой команды.")
        return  
    
    # Очищаем состояние и начинаем заново
    await state.clear()
    await state.set_state(AddTimetableState.waiting_for_school)
    
    # Просим ввести школу
    sent_msg = await message.answer("Введите номер школы, например: 11 или 9", reply_markup=get_cancel_keyboard())
    await state.update_data(bot_messages_ids=[sent_msg.message_id])



# State для получения школы
@dp.message(StateFilter(AddTimetableState.waiting_for_school))
async def get_school(message: Message, state: FSMContext):
    # Проверяем нажатие кнопки отмены
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление расписания отменено.", reply_markup=remove_keyboard)
        return
    
    data = await state.get_data()
    previous_state = data.get("previous_state")
    bot_messages_ids = data.get("bot_messages_ids", [])

    school_name = message.text.strip()  

    if not validate_school_name(str(school_name)):
        sent_msg = await message.answer("Неверный формат школы. Пожалуйста, введите в формате, например: 11 или 9.", reply_markup=get_cancel_keyboard())
        bot_messages_ids.append(sent_msg.message_id)
        await state.update_data(bot_messages_ids=bot_messages_ids)
        return
    
    await state.update_data(school_name=school_name)
    
    sent_msg = await message.answer("Введите номер и букву класса, например: 11Б или 9А", reply_markup=get_cancel_keyboard())
    bot_messages_ids.append(sent_msg.message_id)
    await state.update_data(bot_messages_ids=bot_messages_ids)

    # Используем предыдущее состояние если оно указано, иначе - значение по умолчанию
    next_state = previous_state if previous_state else AddTimetableState.waiting_for_class
    await state.set_state(next_state)




# State для получения класса
@dp.message(StateFilter(AddTimetableState.waiting_for_class))
async def process_class(message: Message, state: FSMContext):
    # Проверяем нажатие кнопки отмены
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление расписания отменено.", reply_markup=remove_keyboard)
        return
    
    # Получаем school_name из состояния
    data = await state.get_data()
    school_name = data.get("school_name")

    class_name = message.text.strip()

    if not validate_class_name(class_name):
        sent_msg = await message.answer("Неверный формат класса. Пожалуйста, введите в формате, например: 11Б или 9А.", reply_markup=get_cancel_keyboard())
        # Добавляем сообщение с предупреждением в список для удаления
        data = await state.get_data()
        bot_messages_ids = data.get("bot_messages_ids", [])
        bot_messages_ids.append(sent_msg.message_id)
        await state.update_data(bot_messages_ids=bot_messages_ids)
        return
    
    # Создаем новый класс
    async with get_async_db() as session:  
        try:
            result = await session.execute(select(ClassORM).where(ClassORM.num == class_name,ClassORM.school_id == int(school_name)))
            class_1 = result.scalars().one_or_none()

            if class_1:
                await message.answer(f'Такой класс уже существует')
                return
            else:
                new_class = ClassORM(
                    school_id=int(school_name),
                    num = class_name,
                    timetable_flag=False
                )
                session.add(new_class)
                await session.commit()
        except Exception as e:
            await message.answer(f"Ошибка: {e}")

    await state.update_data(class_name=class_name)

    sent_msg = await message.answer(f"Класс {class_name} записан. Теперь отправьте, пожалуйста, фотографию расписания.", reply_markup=get_cancel_keyboard())
    data = await state.get_data()
    bot_messages_ids = data.get("bot_messages_ids", [])
    bot_messages_ids.append(sent_msg.message_id)
    await state.update_data(bot_messages_ids=bot_messages_ids)

    await state.set_state(AddTimetableState.waiting_for_photo)



# 1 State для получения фото (если его отправили)
@dp.message(lambda message: message.photo, StateFilter(AddTimetableState.waiting_for_photo))
async def process_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    class_name = data.get("class_name", "unknown_class")
    school_name = data.get("school_name", "unknown_school")  # Получаем номер школы
    bot_messages_ids = data.get("bot_messages_ids", [])

    photo = message.photo[-1]
    file_id = photo.file_id

    save_dir = r"D:\work_11_img"

    os.makedirs(save_dir, exist_ok=True)

    file = await bot.get_file(file_id)

    # Создаем безопасное имя файла с номером школы
    safe_class_name = "".join(c for c in class_name if c.isalnum())
    safe_school_name = "".join(c for c in school_name if c.isalnum())
    
    # Формируем имя файла: "школа_класс.jpg"
    file_name = f"{safe_school_name}_{safe_class_name}.jpg"
    file_path = os.path.join(save_dir, file_name)

    await bot.download_file(file.file_path, destination=file_path)

    async with get_async_db() as session:  
        try:
            result = await session.execute(select(ClassORM).where(ClassORM.num == class_name))
            class_1 = result.scalars().one_or_none()

            if not class_1:
                await message.answer(f'Класс не найден')
                return
            else:
                class_1.timetable_url = str(file_path)  # Используем полный путь
                class_1.timetable_flag = True

                await session.commit()

        except Exception as e:
            await message.answer(f"Ошибка: {e}")

    sent_msg = await message.answer(f"Фото получено! Расписание для школы {school_name}, класса {class_name} добавлено и сохранено.", reply_markup=remove_keyboard)
    bot_messages_ids.append(sent_msg.message_id)
    await state.update_data(bot_messages_ids=bot_messages_ids)
    
    await state.clear()



# 2 State для получения фото (если его не отправили)
@dp.message(StateFilter(AddTimetableState.waiting_for_photo))
async def delete_non_photo_messages(message: Message, state: FSMContext):
    # Проверяем нажатие кнопки отмены
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление расписания отменено.", reply_markup=remove_keyboard)
        return
    
    await state.update_data(bot_messages_ids=AddTimetableState.waiting_for_class)
    if not message.photo:
        try:
            await message.delete()
        except Exception as e:
            print(f"Не удалось удалить сообщение: {e}")
# -------------------------------------------------------------------------------------------------




# ПРОСМОТР РАСПИСАНИЯ
# -------------------------------------------------------------------------------------------------
@dp.message(Command("timetable"))
async def timetable_command(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(AddTimetableState.waiting_for_school_for_timetable)
    await message.answer("Введите номер школы, например: 11 или 9", reply_markup=get_cancel_keyboard())

# State для получения школы и отправки расписания 
@dp.message(StateFilter(AddTimetableState.waiting_for_school_for_timetable))
async def process_school_for_timetable(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Просмотр расписания отменен.", reply_markup=remove_keyboard)
        return
    
    school_name = message.text.strip()
    
    if not validate_school_name(school_name):
        await message.answer("Неверный формат школы. Пожалуйста, введите в формате, например: 11 или 9.", reply_markup=get_cancel_keyboard())
        return
    
    await state.update_data(school_name=school_name)
    await state.set_state(AddTimetableState.waiting_for_class_for_timetable)
    await message.answer("Введите номер и букву класса, например: 11Б или 9А", reply_markup=get_cancel_keyboard())

# State для получения класса и отправки расписания
@dp.message(StateFilter(AddTimetableState.waiting_for_class_for_timetable))
async def process_class_for_timetable(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Просмотр расписания отменен.", reply_markup=remove_keyboard)
        return
    
    class_name = message.text.strip()
    
    if not validate_class_name(class_name):
        await message.answer("Неверный формат класса. Пожалуйста, введите в формате, например: 11Б или 9А.", reply_markup=get_cancel_keyboard())
        return
    
    data = await state.get_data()
    school_name = data.get("school_name")
    
    async with get_async_db() as session:
        try:
            # Ищем класс по школе и названию
            result = await session.execute(
                select(ClassORM).where(
                    ClassORM.school_id == int(school_name),
                    ClassORM.num == class_name
                )
            )
            class_obj = result.scalars().one_or_none()
            
            if not class_obj:
                await message.answer(f"Класс {class_name} в школе {school_name} не найден.")
                return
            
            if not class_obj.timetable_flag:
                await message.answer(f"Расписание для класса {class_name} еще не добавлено.")
                return

            # Проверяем существование файла
            file_path = rf"D:\work_11_img\{school_name}_{class_name}.jpg"
            
            if not os.path.exists(file_path):
                await message.answer(f"Файл расписания не найден: {file_path}")
                return
            
            # Отправляем файл
            document = FSInputFile(file_path)
            await message.answer_document(document)
            await message.answer("Расписание отправлено!", reply_markup=remove_keyboard)
            
        except Exception as e:
            await message.answer(f"Ошибка при поиске расписания: {e}")
    
    await state.clear()
# -------------------------------------------------------------------------------------------------




# ДОБАВЛЕНИЕ ДЗ
# -------------------------------------------------------------------------------------------------
@dp.message(Command("add_homework"))
async def add_homework(message: Message, state: FSMContext):
    await message.answer("Введите номер школы, например: 11 или 9")
    await state.set_state(AddHomeworkState.waiting_for_school_homework)

    await state.update_data(previous_state="add_homework")

@dp.message(StateFilter(AddHomeworkState.waiting_for_school_homework))
async def waiting_for_school_homework(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление дз отменено.", reply_markup=remove_keyboard)
        return
    
    school_name = message.text.strip()
    
    if not validate_school_name(school_name):
        await message.answer("Неверный формат школы. Пожалуйста, введите в формате, например: 11 или 9.", reply_markup=get_cancel_keyboard())
        return
    
    await state.update_data(school_name=school_name)
    await state.set_state(AddHomeworkState.waiting_for_class_homework)
    await message.answer("Введите номер и букву класса, например: 11Б или 9А", reply_markup=get_cancel_keyboard())

@dp.message(StateFilter(AddHomeworkState.waiting_for_class_homework))
async def waiting_for_class_homework(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление дз отменено.", reply_markup=remove_keyboard)
        return
    
    class_name = message.text.strip()
    
    if not validate_class_name(class_name):
        await message.answer("Неверный формат класса. Пожалуйста, введите в формате, например: 11Б или 9А.", reply_markup=get_cancel_keyboard())
        return
    
    data = await state.get_data()
    school_name = data.get("school_name")

    async with get_async_db() as session:
        try:
            # Ищем класс по школе и названию
            result = await session.execute(
                select(ClassORM).where(
                    ClassORM.school_id == int(school_name),
                    ClassORM.num == class_name
                )
            )
            class_obj = result.scalars().one_or_none()
            
            if not class_obj:
                await message.answer(f"Класс {class_name} в школе {school_name} не найден.")
                return
            
            result = await session.execute(
                select(HomeworkORM).where(HomeworkORM.class_id==class_obj.id)
            )
            homework = result.scalars().one_or_none()

            if not homework:

                homework = HomeworkORM(
                    class_id=class_obj.id
                )

                session.add(homework)
                await session.commit()

            await state.update_data(class_obj_id=class_obj.id)
            # Перекидывем на state , который будет обрабатывать получение предмета
            #------------------------------------------------------------------------------------------
            previous_state = data.get("previous_state")
            if previous_state == "add_homework":
                await message.answer("Введите название предмета", reply_markup=get_cancel_keyboard())
                await state.set_state(AddHomeworkState.waiting_subject_at_school_homework)
            else:
                await state.set_state(GetHomeworkState.get_homework)
            #------------------------------------------------------------------------------------------

        except Exception as e:
            await message.answer(f"Ошибка при добавлении дз: {e}")

@dp.message(StateFilter(AddHomeworkState.waiting_subject_at_school_homework))
async def waiting_subject_at_school_homework(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление дз отменено.", reply_markup=remove_keyboard)
        return

    subject_at_school = message.text.strip()
    
    english_subject = get_subject_english(subject_at_school)
    if not english_subject:
        await message.answer("Неверный формат предмета. Пример: алгебра, русский язык", reply_markup=get_cancel_keyboard())
        return


    await state.update_data(subject_at_school=get_subject_english(subject_at_school))
    await message.answer(f"Напишите дз предмета {subject_at_school}")

    # Перекидываем на финальный state 
    #------------------------------------------------------------------------------------------
    await state.set_state(AddHomeworkState.waiting_homework)
    #------------------------------------------------------------------------------------------
   
@dp.message(StateFilter(AddHomeworkState.waiting_homework))
async def waiting_homework(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление дз отменено.", reply_markup=remove_keyboard)
        return

    homework = message.text.strip()

    data = await state.get_data()
    subject_at_school = data.get("subject_at_school")
    class_obj_id = data.get("class_obj_id")

    async with get_async_db() as session:
        try:
            result = await session.execute(
                select(HomeworkORM).where(HomeworkORM.class_id==class_obj_id)
            )
            homework_orm = result.scalars().one_or_none()

            if homework_orm:
                setattr(homework_orm, subject_at_school, homework)
                await session.commit()
                await message.answer(f"Домашнее задание по {subject_at_school} обновлено.")

                await state.clear()
            
        except Exception as e:
            await message.answer(f"Ошибка при добавлении дз: {e}")
# -------------------------------------------------------------------------------------------------



# ПОЛУЧЕНИЕ ДЗ
# -------------------------------------------------------------------------------------------------
@dp.message(Command("get_homework"))
async def get_homework_1(message: Message, state: FSMContext):
    await state.update_data(previous_state="get_homework")

    await message.answer("Введите номер школы, например: 11 или 9")
    await state.set_state(AddHomeworkState.waiting_for_school_homework)

@dp.message(StateFilter(GetHomeworkState.get_homework))
async def final_get_homework(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление дз отменено.", reply_markup=remove_keyboard)
        return
    
    data = await state.get_data()
    subject_at_school = data.get("subject_at_school")
    class_obj_id = data.get("class_obj_id")

    async with get_async_db() as session:
        try:
            
            result = await session.execute(
                select(HomeworkORM).where(HomeworkORM.class_id==class_obj_id)
            )

            homework = result.scalars().one_or_none()

            if not homework:
                await message.answer("Дз класса не найдено.")
                await state.clear()
                return

            subject_map = {
                "algebra": "Алгебра",
                "geometry": "Геометрия",
                "english_language": "Английский язык",
                "russian_language": "Русский язык",
                "literature": "Литература",
                "history": "История",
                "physics": "Физика",
                "chemistry": "Химия",
                "biology": "Биология",
                "geography": "География",
                "social_science": "Обществознание",
                "informatics": "Информатика",
            }

            # Формируем строку с домашними заданиями
            homework_lines = []
            for attr, subject_name in subject_map.items():
                value = getattr(homework, attr)
                if value and value.strip():  # проверка, что не None и не пустая строка
                    homework_lines.append(f"{subject_name} - {value.strip()}")

            if homework_lines:
                homework_text = "\n".join(homework_lines)
                await message.answer(f"Домашнее задание:\n{homework_text}")
            else:
                await message.answer("Для этого класса пока нет заданного домашнего задания.")

            await state.clear()
            
        except Exception as e:
            await message.answer(f"Ошибка при добавлении дз: {e}")

# -------------------------------------------------------------------------------------------------


# ИИ ассистент
# -------------------------------------------------------------------------------------------------
@dp.message(Command("send_chatgpt"))
async def send_chatgpt(message: Message, state: FSMContext):
    await message.answer("Задавайте свой вопрос", reply_markup=get_cancel_keyboard())
    await state.set_state(SendMessChatGPR.waiting_message_for_chatgpt)

@dp.message(StateFilter(SendMessChatGPR.waiting_message_for_chatgpt))
async def waiting_message_for_chatgpt(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Запрос отменен.", reply_markup=remove_keyboard)
        return

    question = message.text.strip()

    # Показываем что бот думает
    result = await ask_apifreellm(question)
    if result is None:
        await message.answer("Произошла неизвестная ошибка")
    else:
        await message.answer(result)
# -------------------------------------------------------------------------------------------------

# Добавление учебников
# -------------------------------------------------------------------------------------------------
@dp.message(Command("add_book"))
async def add_book(message: Message, state: FSMContext):

    await message.answer("Напишите название книги")
    await state.set_state(SaveBooksState.waiting_for_name_book)

@dp.message(StateFilter(SaveBooksState.waiting_for_name_book))
async def waiting_for_name_book(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Запрос отменен.", reply_markup=remove_keyboard)
        return

    name_book = message.text.strip()

    await state.update_data(name_book=name_book)

    await message.answer("Отправьте файл книги")
    await state.set_state(SaveBooksState.waiting_for_file_book)

@dp.message(lambda message: message.document is not None, StateFilter(SaveBooksState.waiting_for_file_book))
async def waiting_for_file_book(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Запрос отменен.", reply_markup=remove_keyboard)
        return

    save_dir = r"D:\work_11_books"
    os.makedirs(save_dir, exist_ok=True)

    data = await state.get_data()
    name_book = data.get("name_book")

    document = message.document
    if not document:
        await message.answer("Пожалуйста, пришлите файл.")
        return

    # Формируем имя файла с расширением
    file_name = f"{name_book}{os.path.splitext(document.file_name)[1]}"
    file_path = os.path.join(save_dir, file_name)

    # Получаем путь файла в Telegram
    file = await bot.get_file(document.file_id)

    # Скачиваем файл и сохраняем в file_path
    await bot.download_file(file.file_path, destination=file_path)

    await message.answer(f"Файл '{file_name}' успешно сохранён", reply_markup=remove_keyboard)
    await state.clear()

# -------------------------------------------------------------------------------------------------


# Получение книг
# -------------------------------------------------------------------------------------------------
@dp.message(Command("get_book"))
async def get_book(message: types.Message, state: FSMContext):
    await message.answer("Напишите название книги , пример : 10 обществознание боголюбов")
    await state.set_state(GetBookState.waiting_for_name_book)

@dp.message(StateFilter(GetBookState.waiting_for_name_book))
async def waiting_for_name_book_get(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Запрос отменен.", reply_markup=remove_keyboard)
        return

    books_dir = r"D:\work_11_books"

    name_book = message.text.strip()

    file_path = find_file_by_partial_name(books_dir,name_book)

    if file_path:
        file = FSInputFile(path=file_path)
        await message.answer_document(document=file)
    else:
        
        await message.answer("Файл не найден")
        return


# -------------------------------------------------------------------------------------------------

async def main():
    # СОЗДАНИЕ ТАБЛИЦ
    #await drop_all_tables(engine)
    # УДАЛЕНИЕ ТАБЛИЦ
    await create_all_tables(engine)
    # СОЗДАНИЕ ВСЕХ ШКОЛ
    await create_all_schools()

    # Устанавливаем команды меню при запуске бота
    await set_main_menu(bot)
    print("Команды меню установлены")

    print("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())