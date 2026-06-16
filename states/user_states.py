from aiogram.fsm.state import State, StatesGroup


class SpecialistFlow(StatesGroup):
    awaiting_note = State()


class UserFlow(StatesGroup):
    language_selection = State()
    gdpr_consent = State()
    intake_name = State()
    intake_age = State()
    intake_age_number = State()
    intake_child_first_name = State()
    intake_child_last_name = State()
    intake_location = State()
    intake_email = State()
    intake_phone = State()
    intake_protection = State()
    intake_prague = State()
    intake_situation = State()
    triage_choice = State()
    triage_description = State()
    slot_selection = State()
