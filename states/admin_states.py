from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    entering_user_id = State()  # Для действий, где нужно ввести user_id
    broadcast_text = State()
    broadcast_confirm = State()