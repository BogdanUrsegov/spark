from aiogram.fsm.state import State, StatesGroup

class FillProfile(StatesGroup):
    name = State()
    age = State()
    gender = State()
    description = State()
    location = State()
    photo = State()