from aiogram.fsm.state import State, StatesGroup


class SpecialistFlow(StatesGroup):
    awaiting_note = State()


class UserFlow(StatesGroup):
    language_selection    = State()
    gdpr_consent          = State()
    intake_name           = State()
    intake_age            = State()
    intake_location       = State()
    intake_email          = State()
    intake_phone          = State()
    intake_contact_method = State()
    intake_protection     = State()
    intake_prague         = State()
    triage_choice         = State()
    triage_description    = State()
    slot_selection        = State()
