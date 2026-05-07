document.getElementById("orderForm").addEventListener("submit", async function(e) {
    e.preventDefault();

    const description = document.getElementById("description").value;
    const errorEl = document.getElementById("error");

    errorEl.textContent = "";

    const response = await fetch("/create-order", {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: "description=" + encodeURIComponent(description)
    });

    if (response.redirected) {
        window.location.href = response.url;
        return;
    }

    const data = await response.json();

    if (data.error) {
        errorEl.textContent = data.error;
    }
});

const translations = {
    uz: {
        "back": "Orqaga",
        "brand": "TynDyx Cargo",
        "order_details": "Buyurtma ma'lumotlari",
        "feedback_title": "Haydovchi uchun fikr",
        "write_feedback": "Fikringizni yozing...",
        "send": "Yuborish",
        "dashboard": "Dashboard",
        "logout": "Chiqish",
        "login_title": "Kirish",
        "register_title": "Ro'yxatdan o'tish",
        "full_name": "To'liq ism",
        "password": "Parol",
        "role": "Rolni tanlang",
        "my_orders": "Mening buyurtmalarim",
        "active": "Aktiv",
        "inactive": "Aktiv emas"
    },
    en: {
        "back": "Back",
        "brand": "TynDyx Cargo",
        "order_details": "Order Details",
        "feedback_title": "Driver Feedback",
        "write_feedback": "Write your feedback...",
        "send": "Send",
        "dashboard": "Dashboard",
        "logout": "Logout",
        "login_title": "Login",
        "register_title": "Register",
        "full_name": "Full Name",
        "password": "Password",
        "role": "Select Role",
        "my_orders": "My Orders",
        "active": "Active",
        "inactive": "Inactive"
    },
    ru: {
        "back": "Назад",
        "brand": "TynDyx Cargo",
        "order_details": "Информация о заказе",
        "feedback_title": "Отзыв о водителе",
        "write_feedback": "Напишите ваш отзыв...",
        "send": "Отправить",
        "dashboard": "Панель",
        "logout": "Выйти",
        "login_title": "Вход",
        "register_title": "Регистрация",
        "full_name": "Полное имя",
        "password": "Пароль",
        "role": "Выберите роль",
        "my_orders": "Мои заказы",
        "active": "Активен",
        "inactive": "Неактивен"
    }
};

function applyLanguage(lang) {
    localStorage.setItem('selectedLang', lang);

    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (translations[lang] && translations[lang][key]) {
            if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                element.placeholder = translations[lang][key];
            } else {
                element.textContent = translations[lang][key];
            }
        }
    });

    const currentLangDisplay = document.getElementById('current-lang');
    if (currentLangDisplay) {
        currentLangDisplay.textContent = lang.toUpperCase();
    }
}

function initTheme() {
    const themeToggle = document.getElementById('theme-toggle');
    const savedTheme = localStorage.getItem('theme') || 'light';

    if (savedTheme === 'dark') {
        document.body.classList.add('dark');
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('dark');
            const isDark = document.body.classList.contains('dark');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const savedLang = localStorage.getItem('selectedLang') || 'uz';
    applyLanguage(savedLang);

    initTheme();

    const langBtn = document.getElementById('lang-toggle');
    const langMenu = document.querySelector('.lang-menu');
    if (langBtn && langMenu) {
        langBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            langMenu.classList.toggle('show');
        });

        document.addEventListener('click', () => langMenu.classList.remove('show'));
    }
});

function changeLang(lang) {
    applyLanguage(lang);
    const langMenu = document.querySelector('.lang-menu');
    if (langMenu) langMenu.classList.remove('show');
}

