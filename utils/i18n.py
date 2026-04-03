"""Centralised localisation strings."""

TEXTS: dict[str, dict[str, str]] = {
    "UA": {
        "lang_prompt": "Вітаємо! 👋\nОберіть мову спілкування:",
        "gdpr": (
            "🔒 *Конфіденційність та захист даних*\n\n"
            "Ми збираємо:\n"
            "• Ім'я, вік, місто\n"
            "• Контактні дані (email, номер телефону)\n"
            "• Опис вашої ситуації — *дані про ментальне здоров'я (ст. 9 GDPR)*\n\n"
            "Дані використовуються виключно для підбору спеціаліста і *не передаються третім особам*.\n\n"
            "Ви можете видалити всі свої дані командою /deleteme у будь-який час.\n\n"
            "Ви надаєте *явну згоду* на обробку даних, включаючи дані про ментальне здоров'я?"
        ),
        "gdpr_decline": "Розуміємо ваш вибір. Якщо передумаєте — надішліть /start 💙",
        "deleteme_confirm": (
            "🗑 Всі ваші дані видалено з системи. Дякуємо, що довіряли нам 💙\n"
            "Якщо захочете повернутися — /start"
        ),
        "deleteme_notfound": "Даних не знайдено — можливо, ви ще не реєструвались.",
        "intake_name": "Як вас звати? (ім'я та прізвище)",
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
        "slot_booked": "✅ Сесію заброньовано!\n{details}",
        "slot_reminder": "⏰ Нагадування: ваша сесія <b>через 2 години</b>.\n\n{details}",
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
        "btn_call_operator": "☎️ Зателефонувати оператору",
        "intake_email": "📧 Введіть ваш email (обов'язкове поле):",
        "intake_email_invalid": "⚠️ Будь ласка, введіть коректний email адрес.",
        "intake_phone": "📱 Введіть ваш номер телефону (обов'язкове поле):",
        "intake_phone_invalid": "⚠️ Будь ласка, введіть номер телефону (мінімум 7 цифр).",
        "intake_contact_method": "Який спосіб зв'язку ви надаєте перевагу?",
        "intake_protection": "Чи маєте ви статус тимчасового захисту в Чехії?",
        "intake_prague": "Ваша адреса реєстрації — місто Прага?",
        "not_eligible_protection": (
            "😔 На жаль, в рамках даного проекту ми працюємо лише з біженцями, "
            "які мають статус тимчасового захисту в Чехії."
        ),
        "not_eligible_prague": (
            "😔 На жаль, в рамках даного проекту ми працюємо лише з біженцями, "
            "які мають статус тимчасового захисту в Чехії та проживають у Празі."
        ),
        "btn_yes": "✅ Так",
        "btn_no": "❌ Ні",
        "btn_skip": "⏭ Пропустити",
        "contact_phone": "📞 Телефон",
        "contact_viber": "💜 Viber",
        "contact_whatsapp": "💚 WhatsApp",
        "contact_telegram": "✈️ Telegram",
    },
    "RU": {
        "lang_prompt": "Добро пожаловать! 👋\nВыберите язык:",
        "gdpr": (
            "🔒 *Конфиденциальность и защита данных*\n\n"
            "Мы собираем:\n"
            "• Имя, возраст, город\n"
            "• Контактные данные (email, номер телефона)\n"
            "• Описание вашей ситуации — *данные о ментальном здоровье (ст. 9 GDPR)*\n\n"
            "Данные используются исключительно для подбора специалиста и *не передаются третьим лицам*.\n\n"
            "Вы можете удалить все свои данные командой /deleteme в любое время.\n\n"
            "Вы даёте *явное согласие* на обработку данных, включая данные о ментальном здоровье?"
        ),
        "gdpr_decline": "Понимаем. Если передумаете — отправьте /start 💙",
        "deleteme_confirm": (
            "🗑 Все ваши данные удалены из системы. Спасибо, что доверяли нам 💙\n"
            "Если захотите вернуться — /start"
        ),
        "deleteme_notfound": "Данные не найдены — возможно, вы ещё не регистрировались.",
        "intake_name": "Как вас зовут? (имя и фамилия)",
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
        "slot_booked": "✅ Сессия забронирована!\n{details}",
        "slot_reminder": "⏰ Напоминание: ваша сессия <b>через 2 часа</b>.\n\n{details}",
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
        "btn_call_operator": "☎️ Позвонить оператору",
        "intake_email": "📧 Введите ваш email (обязательное поле):",
        "intake_email_invalid": "⚠️ Пожалуйста, введите корректный email адрес.",
        "intake_phone": "📱 Введите ваш номер телефона (обязательное поле):",
        "intake_phone_invalid": "⚠️ Пожалуйста, введите номер телефона (минимум 7 цифр).",
        "intake_contact_method": "Какой способ связи вы предпочитаете?",
        "intake_protection": "Есть ли у вас статус временной защиты в Чехии?",
        "intake_prague": "Ваш адрес регистрации — город Прага?",
        "not_eligible_protection": (
            "😔 К сожалению, в рамках данного проекта мы работаем только с беженцами, "
            "имеющими статус временной защиты в Чехии."
        ),
        "not_eligible_prague": (
            "😔 К сожалению, в рамках данного проекта мы работаем только с беженцами, "
            "имеющими статус временной защиты в Чехии и проживающими в Праге."
        ),
        "btn_yes": "✅ Да",
        "btn_no": "❌ Нет",
        "btn_skip": "⏭ Пропустить",
        "contact_phone": "📞 Телефон",
        "contact_viber": "💜 Viber",
        "contact_whatsapp": "💚 WhatsApp",
        "contact_telegram": "✈️ Telegram",
    },
    "CZ": {
        "lang_prompt": "Vítejte! 👋\nVyberte jazyk:",
        "gdpr": (
            "🔒 *Ochrana osobních údajů*\n\n"
            "Shromažďujeme:\n"
            "• Jméno, věk, město\n"
            "• Kontaktní údaje (email, telefonní číslo)\n"
            "• Popis vaší situace — *údaje o duševním zdraví (čl. 9 GDPR)*\n\n"
            "Údaje slouží výhradně k přidělení specialisty a *nejsou sdíleny s třetími stranami*.\n\n"
            "Všechna vaše data můžete kdykoli smazat příkazem /deleteme.\n\n"
            "Udělujete *výslovný souhlas* se zpracováním údajů včetně údajů o duševním zdraví?"
        ),
        "gdpr_decline": "Rozumíme. Kdykoli napište /start 💙",
        "deleteme_confirm": (
            "🗑 Všechna vaše data byla smazána. Děkujeme za důvěru 💙\n"
            "Kdykoli se vraťte — /start"
        ),
        "deleteme_notfound": "Žádná data nenalezena — možná jste se ještě nezaregistrovali.",
        "intake_name": "Jak se jmenujete? (jméno a příjmení)",
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
        "slot_booked": "✅ Termín zarezervován!\n{details}",
        "slot_reminder": "⏰ Připomenutí: vaše sezení <b>za 2 hodiny</b>.\n\n{details}",
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
        "btn_call_operator": "☎️ Zavolat operátorovi",
        "intake_email": "📧 Zadejte svůj email (povinné pole):",
        "intake_email_invalid": "⚠️ Prosím zadejte platnou emailovou adresu.",
        "intake_phone": "📱 Zadejte své telefonní číslo (povinné pole):",
        "intake_phone_invalid": "⚠️ Prosím zadejte telefonní číslo (minimálně 7 číslic).",
        "intake_contact_method": "Jaký způsob kontaktu preferujete?",
        "intake_protection": "Máte status dočasné ochrany v České republice?",
        "intake_prague": "Je vaše adresa registrace v Praze?",
        "not_eligible_protection": (
            "😔 Bohužel, v rámci tohoto projektu pracujeme pouze s uprchlíky, "
            "kteří mají status dočasné ochrany v České republice."
        ),
        "not_eligible_prague": (
            "😔 Bohužel, v rámci tohoto projektu pracujeme pouze s uprchlíky, "
            "kteří mají status dočasné ochrany v ČR a žijí v Praze."
        ),
        "btn_yes": "✅ Ano",
        "btn_no": "❌ Ne",
        "btn_skip": "⏭ Přeskočit",
        "contact_phone": "📞 Telefon",
        "contact_viber": "💜 Viber",
        "contact_whatsapp": "💚 WhatsApp",
        "contact_telegram": "✈️ Telegram",
    },
    "EN": {
        "lang_prompt": "Welcome! 👋\nSelect your language:",
        "gdpr": (
            "🔒 *Privacy & Data Protection*\n\n"
            "We collect:\n"
            "• Name, age, city\n"
            "• Contact details (email, phone number)\n"
            "• Description of your situation — *mental health data (Art. 9 GDPR)*\n\n"
            "Data is used solely to match you with a specialist and *never shared with third parties*.\n\n"
            "You can delete all your data at any time with /deleteme.\n\n"
            "Do you give *explicit consent* to process your data, including mental health information?"
        ),
        "gdpr_decline": "We understand. Send /start whenever you're ready 💙",
        "deleteme_confirm": (
            "🗑 All your data has been deleted. Thank you for trusting us 💙\n"
            "You can always return — /start"
        ),
        "deleteme_notfound": "No data found — you may not have registered yet.",
        "intake_name": "What is your name? (first and last name)",
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
        "slot_booked": "✅ Session booked!\n{details}",
        "slot_reminder": "⏰ Reminder: your session is <b>in 2 hours</b>.\n\n{details}",
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
        "btn_call_operator": "☎️ Call operator",
        "intake_email": "📧 Enter your email (required):",
        "intake_email_invalid": "⚠️ Please enter a valid email address.",
        "intake_phone": "📱 Enter your phone number (required):",
        "intake_phone_invalid": "⚠️ Please enter a phone number (at least 7 digits).",
        "intake_contact_method": "Which contact method do you prefer?",
        "intake_protection": "Do you have temporary protection status in the Czech Republic?",
        "intake_prague": "Is your registered address in Prague?",
        "not_eligible_protection": (
            "😔 Unfortunately, this project works only with refugees "
            "who have temporary protection status in the Czech Republic."
        ),
        "not_eligible_prague": (
            "😔 Unfortunately, this project works only with refugees "
            "who have temporary protection status in the Czech Republic and live in Prague."
        ),
        "btn_yes": "✅ Yes",
        "btn_no": "❌ No",
        "btn_skip": "⏭ Skip",
        "contact_phone": "📞 Phone",
        "contact_viber": "💜 Viber",
        "contact_whatsapp": "💚 WhatsApp",
        "contact_telegram": "✈️ Telegram",
    },
}


def t(lang: str, key: str) -> str:
    return TEXTS.get(lang, TEXTS["EN"]).get(key, TEXTS["EN"].get(key, key))
