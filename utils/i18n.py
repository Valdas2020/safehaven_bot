"""Centralised localisation strings."""

TEXTS: dict[str, dict[str, str]] = {
    "UA": {
        "lang_prompt": "Вітаємо! 👋\nОберіть мову спілкування:",
        "gdpr": (
            "🔒 *Конфіденційність*\n\n"
            "Ми збираємо мінімально необхідні дані для підбору спеціаліста.\n"
            "Дані зберігаються безпечно і *не передаються третім особам*.\n\n"
            "Ви погоджуєтесь із умовами обробки персональних даних?"
        ),
        "gdpr_decline": "Розуміємо ваш вибір. Якщо передумаєте — надішліть /start 💙",
        "intake_name": "Як вас звати? (можна псевдонім)",
        "intake_age": "Оберіть вікову категорію:",
        "intake_location": "У якому місті / регіоні ви знаходитесь?",
        "intake_format": "Який формат допомоги вам підходить?",
        "triage_prompt": "Розкажіть коротко про ситуацію або оберіть категорію:",
        "triage_sent": "✅ Запит прийнято. Спеціаліст зв'яжеться з вами найближчим часом 💙",
        "triage_urgent": (
            "🚨 *Ми поруч. Ви не самі.*\n\n"
            "Якщо є небезпека — зверніться зараз:\n"
            "🇺🇦 Гаряча лінія: *0 800 505 201* (безкоштовно)\n"
            "🇨🇿 Linka bezpečí: *116 111*\n"
            "🆘 Екстрена: *112*\n\n"
            "_Для запису до спеціаліста надішліть /start_"
        ),
        "slots_header": "📅 Доступні слоти (сесія 45 хв):",
        "slot_booked": "✅ Сесію заброньовано! Спеціаліст зв'яжеться для підтвердження.",
        "slot_callback": "📞 Передзвоніть мені",
        "callback_saved": "📞 Зрозуміло! Ми зателефонуємо вам найближчим часом.",
        "no_slots": "😔 Наразі немає вільних слотів. Ми зв'яжемося з вами вручну.",
        "age_child": "Дитина (до 18)",
        "age_adult": "Дорослий (18+)",
        "format_online": "Онлайн",
        "format_in_person": "Особисто",
        "cat_crisis": "🆘 Криза",
        "cat_consult": "🧠 Психолог",
        "cat_ikp": "🤝 Допомога / ІКП",
        "btn_accept": "✅ Погоджуюсь",
        "btn_decline": "❌ Відмовляюсь",
        "btn_callback": "📞 Передзвоніть мені",
        "intake_email": (
            "📧 Введіть ваш email для підтвердження та нагадування за день до сесії.\n"
            "_(Якщо у вас немає email або не хочете вказувати — натисніть «Пропустити»)_"
        ),
        "intake_phone": (
            "📱 Введіть ваш номер телефону (необов'язково).\n"
            "_(Натисніть «Пропустити», якщо не хочете вказувати)_"
        ),
        "intake_contact_method": "Який спосіб зв'язку ви надаєте перевагу?",
        "btn_skip": "⏭ Пропустити",
        "contact_phone": "📞 Телефон",
        "contact_viber": "💜 Viber",
        "contact_whatsapp": "💚 WhatsApp",
        "contact_telegram": "✈️ Telegram",
    },
    "RU": {
        "lang_prompt": "Добро пожаловать! 👋\nВыберите язык:",
        "gdpr": (
            "🔒 *Конфиденциальность*\n\n"
            "Мы собираем минимальные данные для подбора специалиста.\n"
            "Данные надёжно хранятся и *не передаются третьим лицам*.\n\n"
            "Вы соглашаетесь с условиями обработки персональных данных?"
        ),
        "gdpr_decline": "Понимаем. Если передумаете — отправьте /start 💙",
        "intake_name": "Как вас зовут? (можно псевдоним)",
        "intake_age": "Выберите возрастную категорию:",
        "intake_location": "В каком городе / регионе вы находитесь?",
        "intake_format": "Какой формат помощи вам подходит?",
        "triage_prompt": "Опишите кратко ситуацию или выберите категорию:",
        "triage_sent": "✅ Запрос принят. Специалист свяжется с вами в ближайшее время 💙",
        "triage_urgent": (
            "🚨 *Мы рядом. Вы не одни.*\n\n"
            "Если есть угроза жизни — обратитесь сейчас:\n"
            "🇷🇺 Телефон доверия: *8-800-2000-122* (бесплатно)\n"
            "🇨🇿 Linka bezpečí: *116 111*\n"
            "🆘 Экстренная: *112*\n\n"
            "_Для записи к специалисту отправьте /start_"
        ),
        "slots_header": "📅 Доступные слоты (сессия 45 мин):",
        "slot_booked": "✅ Сессия забронирована! Специалист свяжется для подтверждения.",
        "slot_callback": "📞 Перезвоните мне",
        "callback_saved": "📞 Понял! Мы перезвоним вам в ближайшее время.",
        "no_slots": "😔 Свободных слотов пока нет. Мы свяжемся вручную.",
        "age_child": "Ребёнок (до 18)",
        "age_adult": "Взрослый (18+)",
        "format_online": "Онлайн",
        "format_in_person": "Лично",
        "cat_crisis": "🆘 Кризис",
        "cat_consult": "🧠 Психолог",
        "cat_ikp": "🤝 Помощь / ИКП",
        "btn_accept": "✅ Соглашаюсь",
        "btn_decline": "❌ Отказываюсь",
        "btn_callback": "📞 Перезвоните мне",
        "intake_email": (
            "📧 Введите ваш email для подтверждения и напоминания за день до сессии.\n"
            "_(Если у вас нет email или не хотите указывать — нажмите «Пропустить»)_"
        ),
        "intake_phone": (
            "📱 Введите ваш номер телефона (необязательно).\n"
            "_(Нажмите «Пропустить», если не хотите указывать)_"
        ),
        "intake_contact_method": "Какой способ связи вы предпочитаете?",
        "btn_skip": "⏭ Пропустить",
        "contact_phone": "📞 Телефон",
        "contact_viber": "💜 Viber",
        "contact_whatsapp": "💚 WhatsApp",
        "contact_telegram": "✈️ Telegram",
    },
    "CZ": {
        "lang_prompt": "Vítejte! 👋\nVyberte jazyk:",
        "gdpr": (
            "🔒 *Ochrana soukromí*\n\n"
            "Shromažďujeme minimální údaje pro přidělení specialisty.\n"
            "Údaje jsou bezpečně uloženy a *nejsou sdíleny s třetími stranami*.\n\n"
            "Souhlasíte se zpracováním osobních údajů?"
        ),
        "gdpr_decline": "Rozumíme. Kdykoli napište /start 💙",
        "intake_name": "Jak se jmenujete? (přezdívka je v pořádku)",
        "intake_age": "Vyberte věkovou kategorii:",
        "intake_location": "Ve kterém městě / regionu se nacházíte?",
        "intake_format": "Jakou formu pomoci preferujete?",
        "triage_prompt": "Stručně popište situaci nebo vyberte kategorii:",
        "triage_sent": "✅ Požadavek přijat. Specialista vás brzy kontaktuje 💙",
        "triage_urgent": (
            "🚨 *Slyšíme vás. Nejste sami.*\n\n"
            "Pokud hrozí nebezpečí:\n"
            "🇨🇿 Linka bezpečí: *116 111*\n"
            "🇨🇿 Linka první pomoci: *116 123*\n"
            "🆘 Záchranná: *112*\n\n"
            "_Pro objednání ke specialistovi napište /start_"
        ),
        "slots_header": "📅 Dostupné termíny (sezení 45 min):",
        "slot_booked": "✅ Termín zarezervován! Specialista vás kontaktuje.",
        "slot_callback": "📞 Zavolejte mi zpět",
        "callback_saved": "📞 Rozumím! Zavoláme vám co nejdříve.",
        "no_slots": "😔 Momentálně nejsou volné termíny. Ozveme se ručně.",
        "age_child": "Dítě (do 18)",
        "age_adult": "Dospělý (18+)",
        "format_online": "Online",
        "format_in_person": "Osobně",
        "cat_crisis": "🆘 Krize",
        "cat_consult": "🧠 Psycholog",
        "cat_ikp": "🤝 Pomoc / IKP",
        "btn_accept": "✅ Souhlasím",
        "btn_decline": "❌ Odmítám",
        "btn_callback": "📞 Zavolejte mi zpět",
        "intake_email": (
            "📧 Zadejte svůj email pro potvrzení a připomenutí den před sezením.\n"
            "_(Pokud nemáte email nebo nechcete uvádět — klikněte na «Přeskočit»)_"
        ),
        "intake_phone": (
            "📱 Zadejte své telefonní číslo (nepovinné).\n"
            "_(Klikněte na «Přeskočit», pokud nechcete uvádět)_"
        ),
        "intake_contact_method": "Jaký způsob kontaktu preferujete?",
        "btn_skip": "⏭ Přeskočit",
        "contact_phone": "📞 Telefon",
        "contact_viber": "💜 Viber",
        "contact_whatsapp": "💚 WhatsApp",
        "contact_telegram": "✈️ Telegram",
    },
    "EN": {
        "lang_prompt": "Welcome! 👋\nSelect your language:",
        "gdpr": (
            "🔒 *Privacy Notice*\n\n"
            "We collect minimal data to match you with a specialist.\n"
            "It is stored securely and *never shared with third parties*.\n\n"
            "Do you agree to the data processing terms?"
        ),
        "gdpr_decline": "We understand. Send /start whenever you're ready 💙",
        "intake_name": "What is your name? (alias is fine)",
        "intake_age": "Please select your age category:",
        "intake_location": "Which city / region are you in?",
        "intake_format": "What support format works best for you?",
        "triage_prompt": "Briefly describe your situation or choose a category:",
        "triage_sent": "✅ Request received. A specialist will contact you shortly 💙",
        "triage_urgent": (
            "🚨 *We hear you. You are not alone.*\n\n"
            "If your life is in danger, reach out now:\n"
            "🇨🇿 Linka bezpečí: *116 111*\n"
            "🇨🇿 Crisis line: *116 123*\n"
            "🆘 Emergency: *112*\n\n"
            "_To book a session with a specialist, send /start_"
        ),
        "slots_header": "📅 Available slots (45-min session):",
        "slot_booked": "✅ Session booked! The specialist will contact you to confirm.",
        "slot_callback": "📞 Please call me back",
        "callback_saved": "📞 Got it! We will call you back shortly.",
        "no_slots": "😔 No available slots right now. We'll reach out manually.",
        "age_child": "Child (under 18)",
        "age_adult": "Adult (18+)",
        "format_online": "Online",
        "format_in_person": "In-person",
        "cat_crisis": "🆘 Crisis",
        "cat_consult": "🧠 Psychologist",
        "cat_ikp": "🤝 Assistance / IKP",
        "btn_accept": "✅ I agree",
        "btn_decline": "❌ I decline",
        "btn_callback": "📞 Please call me back",
        "intake_email": (
            "📧 Enter your email for a booking confirmation and a reminder the day before.\n"
            "_(No email or prefer not to share? Tap «Skip»)_"
        ),
        "intake_phone": (
            "📱 Enter your phone number (optional).\n"
            "_(Tap «Skip» if you'd rather not share it)_"
        ),
        "intake_contact_method": "Which contact method do you prefer?",
        "btn_skip": "⏭ Skip",
        "contact_phone": "📞 Phone",
        "contact_viber": "💜 Viber",
        "contact_whatsapp": "💚 WhatsApp",
        "contact_telegram": "✈️ Telegram",
    },
}


def t(lang: str, key: str) -> str:
    return TEXTS.get(lang, TEXTS["EN"]).get(key, TEXTS["EN"].get(key, key))
