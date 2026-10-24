from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    entering_user_id = State()  # Для действий, где нужно ввести user_id
    broadcast_text = State()
    broadcast_confirm = State()
    # Manual creation of admin-only demo profiles.
    fake_profile_name = State()
    fake_profile_age = State()
    fake_profile_gender = State()
    fake_profile_description = State()
    fake_profile_location = State()
    fake_profile_photo = State()
    fake_profile_media = State()
