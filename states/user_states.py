from aiogram.fsm.state import State, StatesGroup


class UserFlow(StatesGroup):
    language_selection = State()
    gdpr_consent       = State()
    intake_name        = State()
    intake_age         = State()
    intake_location    = State()
    intake_format      = State()
    triage_choice      = State()
    triage_description = State()
    slot_selection     = State()
