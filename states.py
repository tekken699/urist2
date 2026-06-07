from aiogram.fsm.state import State, StatesGroup


class ClaimFlow(StatesGroup):
    choosing_partner = State()
    searching_partner = State()
    entering_bakery_address = State()
    entering_act_date = State()
    entering_violations = State()
    uploading_photos = State()


class AddPartner(StatesGroup):
    name = State()
    full_fio = State()
    inn = State()
    ogrnip = State()
    address = State()
    email = State()
    phone = State()
    dkk_number = State()
    dkk_date = State()
    confirm = State()


class EditPartner(StatesGroup):
    waiting_value = State()
