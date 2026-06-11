from aiogram.fsm.state import State, StatesGroup


class LikeMessageStates(StatesGroup):
    message = State()