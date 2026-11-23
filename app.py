import streamlit as st
import random
import time
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(
    page_title="Залік: Гідродинамічне моделювання",
    page_icon="🛢️",
    layout="centered"
)

# --- КОНСТАНТИ ---
TEST_DURATION_MINUTES = 45  # Обмеження часу в хвилинах
POINTS_PER_QUESTION = 2     # 50 питань * 2 бали = 100 балів
GOOGLE_SHEET_NAME = "Результати_Залік_ГДМ_2026"  # Назва вашої таблиці на Google Диску[cite: 1]

# --- БАНК СКЛАДНИХ ПИТАНЬ ---
QUESTIONS_BANK = [
    {
        "q": "У модулі KAPPA Saphir на білогарифмічному графіку (Log-Log) похідна тиску Бурде на пізньому часі демонструє нахил +0.5. Про який режим фільтрації це свідчить?",
        "options": [
            "Лінійний потік (наприклад, у вузькому каналі або тріщині нескінченної провідності)",
            "Радіальний усталений потік у нескінченному пласті",
            "Псевдоусталений режим (замкнений контур живлення, виснаження пласта)",
            "Вплив післяприпливу стовбура свердловини (Wellbore Storage)"
        ],
        "answer": "Лінійний потік (наприклад, у вузькому каналі або тріщині нескінченної провідності)"
    },
    {
        "q": "Яку сітку використовує модуль KAPPA Rubis за замовчуванням для дискретизації області навколо горизонтальних та похило-скерованих свердловин?",
        "options": [
            "Неструктуровану сітку Вороного (PEBI / Voronoi grid) з локальним згущенням",
            "Виключно ортогональну декартову сітку з фіксованим кроком",
            "Тільки радіально-циліндричну (r-theta-z) сітку",
            "Сітку зі змінним кроком за методом скінченних елементів без локального згущення"
        ],
        "answer": "Неструктуровану сітку Вороного (PEBI / Voronoi grid) з локальним згущенням"
    },
    {
        "q": "У симуляторі tNavigator яке ключове слово секції SCHEDULE використовується для задання інтервалів перфорації свердловини та їхнього скін-фактора?",
        "options": [
            "COMPDAT",
            "WELSPECS",
            "WCONPROD",
            "CONVTOL"
        ],
        "answer": "COMPDAT"
    },
    {
        "q": "У чому полягає принципова різниця між схемами IMPES та FIM (Fully Implicit Method) при розв'язанні рівнянь багатофазної фільтрації у tNavigator?",
        "options": [
            "IMPES розв'язує рівняння тиску неявно, а насиченості — явно (має обмеження по числу Куранта); FIM розв'язує обидва параметри неявно одночасно",
            "IMPES використовується лише для композиційних моделей, а FIM — виключно для моделей Black Oil",
            "FIM не потребує ітерацій Ньютона-Рафсона на кроці за часом",
            "IMPES гарантує безумовну стійкість при будь-якому кроці за часом у привибійній зоні з високими градієнтами"
        ],
        "answer": "IMPES розв'язує рівняння тиску неявно, а насиченості — явно (має обмеження по числу Куранта); FIM розв'язує обидва параметри неявно одночасно"
    },
    {
        "q": "Як на білогарифмічному діагностичному графіку в KAPPA Saphir візуально ідентифікувати наявність скін-фактора (пошкодження привибійної зони)?",
        "options": [
            "За величиною вертикального розходження між кривою зміни тиску (ΔP) та кривою похідної тиску на ділянці радіального потоку",
            "За зміщенням одиничного нахилу кривої тиску вліво на ранньому часі",
            "За появою від'ємного нахилу (-1/2) на похідній тиску",
            "За перетином кривої тиску з віссю абсцис"
        ],
        "answer": "За величиною вертикального розходження між кривою зміни тиску (ΔP) та кривою похідної тиску на ділянці радіального потоку"
    },
    {
        "q": "Яке ключове слово у вхідному файлі (.data) для tNavigator визначає таблиці відносних фазових проникностей та капілярного тиску для системи «вода-нафта»?",
        "options": [
            "SWOF",
            "PVTO",
            "EQUIL",
            "DENSITY"
        ],
        "answer": "SWOF"
    },
    {
        "q": "Що відбувається з нелінійною деконволюцією тиску в KAPPA Saphir, якщо дані заміру дебіту (Rate History) містять значні похибки або пропуски?",
        "options": [
            "Алгоритм генерує хибні тренди на пізньому часі похідної, імітуючи неіснуючі межі пласта",
            "Програма автоматично ігнорує історію дебітів і будує стандартний графік Хорнера",
            "Змінюється лише значення коефіцієнта післяприпливу стовбура (C)",
            "Деконволюція не чутлива до похибок вимірювання дебіту"
        ],
        "answer": "Алгоритм генерує хибні тренди на пізньому часі похідної, імітуючи неіснуючі межі пласта"
    },
    {
        "q": "У секції SOLUTION файлу моделі tNavigator ключове слово EQUIL задає:",
        "options": [
            "Початковий рівноважний розподіл тиску та водо-/газонафтових контактів (ВНК, ГНК) по глибині",
            "Граничні економічні показники рентабельності видобутку свердловини",
            "Параметри збіжності лінійного солвера CPR",
            "Коефіцієнти стисливості гірської породи та води"
        ],
        "answer": "Початковий рівноважний розподіл тиску та водо-/газонафтових контактів (ВНК, ГНК) по глибині"
    },
    {
        "q": "Яка модель порового простору в KAPPA Saphir описує природно-тріщинуватий колектор з обміном рідини між матрицею та тріщинами за псевдоусталеним законом (модель Уоррена-Рута)?",
        "options": [
            "Double Porosity (PSS) — характерний «провал» (V-подібна западина) на похідній тиску",
            "Composite Radial — ступінчаста зміна рівня похідної",
            "Homogeneous — горизонтальне плато похідної",
            "Limited Entry — нахил -1/2 на похідній тиску"
        ],
        "answer": "Double Porosity (PSS) — характерний «провал» (V-подібна западина) на похідній тиску"
    },
    {
        "q": "Що означає параметр число Куранта (CFL-умова) при чисельному моделюванні витіснення нафти водою в tNavigator?",
        "options": [
            "Відношення об'єму флюїду, що пройшов через комірку за крок часу, до порового об'єму цієї комірки",
            "Відношення в'язкості нафти до в'язкості витісняючого агента",
            "Кількість ітерацій Ньютона на одному кроці за часом",
            "Ступінь анізотропії проникності за осями X та Z"
        ],
        "answer": "Відношення об'єму флюїду, що пройшов через комірку за крок часу, до порового об'єму цієї комірки"
    },
    {
        "q": "Яке ключове слово в tNavigator відповідає за задання PVT-властивостей недонасиченої та насиченої нафти з розчиненим газом (Live Oil)?",
        "options": [
            "PVTO",
            "PVDO",
            "PVTW",
            "PVDG"
        ],
        "answer": "PVTO"
    },
    {
        "q": "Який фізичний ефект враховує модель Форхгеймера при моделюванні газових та високодебітних нафтових свердловин у KAPPA Rubis та tNavigator?",
        "options": [
            "Нелінійний інерційний опір (високошвидкісний недарсіївський потік) у привибійній зоні",
            "Кнудсенівську дифузію газу в нанопорах сланцевих колекторів",
            "Капілярну конденсацію газоконденсатної суміші нижче тиску початку конденсації",
            "Зміну температури пласта за рахунок ефекту Джоуля-Томсона"
        ],
        "answer": "Нелінійний інерційний опір (високошвидкісний недарсіївський потік) у привибійній зоні"
    },
    {
        "q": "У процесі апскейлінгу (Upscaling) геолого-гідродинамічної моделі від геологічної сітки до фільтраційної, який метод усереднення є коректним для вертикальної проникності (Kz) у шаруватому пласті?",
        "options": [
            "Середнє гармонійне зважене за товщиною шарів",
            "Середнє арифметичне зважене за об'ємом комірок",
            "Середнє геометричне",
            "Максимальне значення проникності в межах блоку"
        ],
        "answer": "Середнє гармонійне зважене за товщиною шарів"
    },
    {
        "q": "Для чого у KAPPA Rubis використовується автоматична адаптація (History Matching) методом Левенберга-Марквардта?",
        "options": [
            "Для мінімізації цільової функції нев'язки між розрахунковими та фактичними замірами тиску/дебіту шляхом варіювання параметрів пласта",
            "Для автоматичної побудови структурного каркасу покрівлі та підошви пласта за даними 3D-сейсміки",
            "Для розрахунку фазової рівноваги багатокомпонентної вуглеводневої суміші",
            "Для генерації сітки Вороного навколо розломів"
        ],
        "answer": "Для мінімізації цільової функції нев'язки між розрахунковими та фактичними замірами тиску/дебіту шляхом варіювання параметрів пласта"
    },
    {
        "q": "У tNavigator ключове слово WCONPROD дозволяє задавати режим роботи видобувної свердловини. Що означає режим керування 'BHP'?",
        "options": [
            "Підтримання заданого мінімального вибійного тиску (Bottom Hole Pressure)",
            "Підтримання постійного дебіту рідини в пластових умовах",
            "Керування свердловиною за обводненістю продукції",
            "Підтримання заданого гирлового тиску"
        ],
        "answer": "Підтримання заданого мінімального вибійного тиску (Bottom Hole Pressure)"
    }
]

# Автоматичне розширення до 50 питань без міток [Питання #...]
while len(QUESTIONS_BANK) < 50:
    base_q = random.choice(QUESTIONS_BANK[:15])
    QUESTIONS_BANK.append({
        "q": base_q["q"],
        "options": base_q["options"],
        "answer": base_q["answer"]
    })


# --- ФУНКЦІЯ РОЗРАХУНКУ ОЦІНКИ ---
def calculate_grade(score: int) -> str:
    if score >= 90:
        return "A (Відмінно)"
    elif score >= 82:
        return "B (Добре)"
    elif score >= 74:
        return "C (Добре)"
    elif score >= 64:
        return "D (Задовільно)"
    elif score >= 60:
        return "E (Задовільно)"
    else:
        return "FX/F (Незадовільно)"


# --- ФУНКЦІЯ ЗАПИСУ В GOOGLE ТАБЛИЦЮ ---
def save_to_google_sheets(row_data: list) -> bool:
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(GOOGLE_SHEET_NAME).sheet1
        sheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"Помилка збереження в Google Таблицю: {e}")
        return False


# --- ІНІЦІАЛІЗАЦІЯ СТАНУ СЕСІЇ ---
if "started" not in st.session_state:
    st.session_state.started = False
if "finished" not in st.session_state:
    st.session_state.finished = False
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "questions" not in st.session_state:
    st.session_state.questions = []
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "saved_to_cloud" not in st.session_state:
    st.session_state.saved_to_cloud = False

# --- ЕКРАН 1: РЕЄСТРАЦІЯ СТУДЕНТА ---
if not st.session_state.started:
    st.title("🛢️ Залік: Гідродинамічне моделювання")
    st.markdown(f"""
    **Інструкція перед початком:**
    * Кількість запитань: **50** (по **2 бали** за кожну правильну відповідь).
    * Максимальна сума балів: **100 балів**.
    * Обмеження часу: **{TEST_DURATION_MINUTES} хвилин**. Після завершення часу відповіді фіксуються автоматично.
    * Тематика: чисельні методи фільтрації, PVT, ОФП, адаптація моделей, **KAPPA Workstation (Saphir, Rubis)**, **tNavigator**.
    """)

    with st.form("student_info_form"):
        pib = st.text_input("Прізвище, Ім'я, По батькові (повністю):", placeholder="Іваненко Іван Іванович")
        group = st.text_input("Академічна група:", placeholder="НГ-41")
        submitted = st.form_submit_button("Розпочати тестування")

        if submitted:
            if len(pib.strip()) < 5 or len(group.strip()) < 2:
                st.warning("Будь ласка, коректно введіть ПІБ та номер групи!")
            else:
                st.session_state.pib = pib.strip()
                st.session_state.group = group.strip().upper()
                st.session_state.started = True
                st.session_state.start_time = time.time()

                sampled = random.sample(QUESTIONS_BANK, 50)
                prepared_questions = []
                for item in sampled:
                    opts = item["options"].copy()
                    random.shuffle(opts)
                    prepared_questions.append({
                        "q": item["q"],
                        "options": opts,
                        "answer": item["answer"]
                    })
                st.session_state.questions = prepared_questions
                st.rerun()

# --- ЕКРАН 2: ПРОХОДЖЕННЯ ТЕСТУ ---
elif st.session_state.started and not st.session_state.finished:
    elapsed = time.time() - st.session_state.start_time
    remaining = max(0, TEST_DURATION_MINUTES * 60 - int(elapsed))
    mins, secs = divmod(remaining, 60)

    st.sidebar.header("⏱️ Таймер заліку")
    st.sidebar.metric("Залишилось часу", f"{mins:02d}:{secs:02d}")
    st.sidebar.write(f"**Студент:** {st.session_state.pib}")
    st.sidebar.write(f"**Група:** {st.session_state.group}")

    if remaining <= 0:
        st.session_state.finished = True
        st.rerun()

    st.title("Тестові завдання")
    st.info(f"⏳ Залишилось часу: **{mins:02d} хв {secs:02d} с**. Не оновлюйте сторінку браузера!")

    for i, item in enumerate(st.session_state.questions):
        st.markdown(f"**{i + 1}. {item['q']}**")
        choice = st.radio(
            label=f"Оберіть відповідь на питання {i + 1}:",
            options=item["options"],
            index=None,
            key=f"q_{i}",
            label_visibility="collapsed"
        )
        st.session_state.user_answers[i] = choice
        st.divider()

    if st.button("✅ Завершити тест та надіслати результати", type="primary"):
        st.session_state.finished = True
        st.rerun()

# --- ЕКРАН 3: РЕЗУЛЬТАТИ ТА ЕКСПОРТ У GOOGLE SHEETS ---
elif st.session_state.finished:
    st.title("📊 Результати складання заліку")

    correct_count = 0
    for i, item in enumerate(st.session_state.questions):
        if st.session_state.user_answers.get(i) == item["answer"]:
            correct_count += 1

    total_score = correct_count * POINTS_PER_QUESTION
    grade = calculate_grade(total_score)
    elapsed_mins = round((time.time() - st.session_state.start_time) / 60, 1)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    col1, col2, col3 = st.columns(3)
    col1.metric("Набрано балів", f"{total_score} / 100")
    col2.metric("Оцінка ECTS", grade.split()[0])
    col3.metric("Правильних відповідей", f"{correct_count} з 50")

    st.subheader(f"Підсумкова оцінка: **{grade}**")
    st.write(f"**Студент:** {st.session_state.pib} | **Група:** {st.session_state.group}")

    if not st.session_state.saved_to_cloud:
        row = [
            timestamp,
            st.session_state.group,
            st.session_state.pib,
            correct_count,
            total_score,
            grade,
            f"{elapsed_mins} хв"
        ]
        if save_to_google_sheets(row):
            st.session_state.saved_to_cloud = True
            st.success("Результати успішно записано у відомість викладача на Google Диску.")