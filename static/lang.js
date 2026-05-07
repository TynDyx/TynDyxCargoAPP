function changeLang(lang) {
    const langText = {
        'uz': 'UZ',
        'en': 'EN',
        'ru': 'RU'
    };
    
    document.getElementById('current-lang').textContent = langText[lang];
    localStorage.setItem('selectedLang', lang);

    console.log("Til o'zgartirildi:", lang);
}

document.addEventListener('DOMContentLoaded', () => {
    const savedLang = localStorage.getItem('selectedLang');
    if (savedLang) {
        const langText = { 'uz': 'UZ', 'en': 'EN', 'ru': 'RU' };
        document.getElementById('current-lang').textContent = langText[savedLang];
    }
});