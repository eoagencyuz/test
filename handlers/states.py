from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    """Ro'yxatdan o'tish bosqichlari. COMPLETED holati users jadvalida saqlanadi."""
    waiting_name = State()
    waiting_phone = State()
    waiting_passport = State()
    confirming_data = State()
    searching_student = State()


IN_PROGRESS_STATES = (
    Registration.waiting_name,
    Registration.waiting_phone,
    Registration.waiting_passport,
    Registration.confirming_data,
)
