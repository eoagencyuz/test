"""Bot xabarlari. Barcha raqam va ismlar faqat format namunasi."""
from config import STUDENT_SITE_NAME, STUDENT_SITE_URL

WELCOME = (
    "Assalomu alaykum! 👋\n\n"
    "Qarshi Xalqaro Universiteti talabalari uchun HEMIS ma’lumotlarini aniqlash xizmatiga xush kelibsiz.\n\n"
    "Davom etish uchun ro‘yxatdan o‘ting.\n\n"
    "Ma’lumotlaringizni ketma-ket kiritishingiz kerak bo‘ladi."
)

ASK_NAME = (
    "1️⃣ Ism va familiyangizni to‘liq kiriting.\n\n"
    "Faqat LOTIN alifbosidan foydalaning.\n\n"
    "Masalan:\n"
    "ALIYEV VALI\n\n"
    "Ism va familiya to‘liq yozilishi shart."
)
INVALID_NAME = (
    "❌ Ism va familiya noto‘g‘ri formatda.\n\n"
    "Iltimos, ism va familiyangizni to‘liq LOTIN alifbosida kiriting.\n\n"
    "Masalan:\n"
    "ALIYEV VALI\n\n"
    "Kamida familiya va ism yozilishi kerak."
)

ASK_PHONE = (
    "2️⃣ Telefon raqamingizni yuboring.\n\n"
    "📱 Eng qulay usul — «Telefon raqamni yuborish» tugmasini bosing.\n\n"
    "Yoki telefon raqamingizni qo‘lda kiriting.\n\n"
    "Ruxsat etilgan formatlar:\n\n"
    "XXXXXXXXX\n"
    "yoki\n"
    "998XXXXXXXXX\n\n"
    "Masalan, tasodifiy namuna:\n"
    "901234567\n"
    "998901234567\n\n"
    "⚠️ Namuna raqamlar faqat formatni ko‘rsatish uchun berilgan."
)
INVALID_PHONE = (
    "❌ Telefon raqami noto‘g‘ri formatda.\n\n"
    "Telefon raqamingizni quyidagi formatlardan birida kiriting:\n\n"
    "XXXXXXXXX\n\n"
    "yoki\n\n"
    "998XXXXXXXXX\n\n"
    "Yoki «📱 Telefon raqamni yuborish» tugmasidan foydalaning."
)
FOREIGN_CONTACT = (
    "❌ Iltimos, faqat o‘zingizning telefon raqamingizni "
    "«📱 Telefon raqamni yuborish» tugmasi orqali yuboring."
)
UNSUPPORTED_CONTACT = (
    "❌ Faqat O‘zbekiston (998) telefon raqamlari qabul qilinadi.\n\n"
    "Telefon raqamingizni XXXXXXXXX yoki 998XXXXXXXXX formatida qo‘lda kiriting."
)

ASK_PASSPORT = (
    "3️⃣ Pasport seriya va raqamingizni kiriting.\n\n"
    "Format:\n\n"
    "AA1234567\n\n"
    "Ya’ni:\n"
    "• 2 ta katta LOTIN harfi\n"
    "• 7 ta raqam\n\n"
    "⚠️ Misol faqat formatni tushuntirish uchun."
)
INVALID_PASSPORT = (
    "❌ Pasport seriya va raqami noto‘g‘ri formatda.\n\n"
    "To‘g‘ri format:\n\n"
    "XX1234567\n\n"
    "Ya’ni:\n"
    "2 ta katta lotin harfi + 7 ta raqam.\n\n"
    "Iltimos, qaytadan kiriting."
)

TEXT_REQUIRED = "❌ Iltimos, ushbu bosqich uchun kerakli ma’lumotni matn ko‘rinishida yuboring."
REGISTRATION_IN_PROGRESS = "ℹ️ Ro‘yxatdan o‘tish jarayoni davom etmoqda. Joriy bosqichni yakunlang."
CANCELLED = "❌ Ro‘yxatdan o‘tish bekor qilindi. Kiritilgan ma’lumotlar o‘chirildi."
SEARCHING = "🔎 Ma’lumotlaringiz tekshirilmoqda..."
STILL_SEARCHING = "⏳ Ma’lumotlaringiz tekshirilmoqda, iltimos kuting."
CHOOSE_BUTTON = "ℹ️ Iltimos, quyidagi tugmalardan birini tanlang."
STALE_BUTTON = "Bu tugma eskirgan. Iltimos, /start buyrug‘ini yuboring."
SERVICE_UNAVAILABLE = (
    "⚠️ Hozircha ma’lumotlarni tekshirib bo‘lmadi. "
    "Birozdan so‘ng «✅ Tasdiqlash» tugmasini qayta bosing."
)

NOT_FOUND = (
    "❌ Siz kiritgan ma’lumotlar bo‘yicha talaba topilmadi.\n\n"
    "Iltimos, quyidagilarni tekshiring:\n\n"
    "• Ism va familiya\n"
    "• Telefon raqami\n"
    "• Pasport seriya va raqami\n\n"
    "Agar barcha ma’lumotlar to‘g‘ri bo‘lsa, universitet mas’ul xodimiga murojaat qiling."
)


def confirm_data(full_name: str, phone: str, passport: str) -> str:
    return (
        "🔎 Kiritilgan ma’lumotlaringiz:\n\n"
        f"👤 F.I.Sh.: {full_name}\n\n"
        f"📱 Telefon: {phone}\n\n"
        f"🪪 Pasport: {passport}\n\n"
        "Ma’lumotlaringizni tasdiqlaysizmi?"
    )


def result_message(full_name: str, hemis_id: str, passport: str, direction: str) -> str:
    return (
        f"🎓 Hurmatli {full_name}!\n\n"
        "Sizning Qarshi xalqaro universiteti HEMIS Student axborot tizimidagi talaba ID raqamingiz aniqlandi.\n\n"
        f"🪪 TALABA ID: {hemis_id}\n"
        f"🔑 Boshlang‘ich parol: {passport}\n"
        f"🌐 Sayt: {STUDENT_SITE_URL}\n"
        f"👤 F.I.Sh.: {full_name}\n"
        f"📚 Yo‘nalish: {direction or '—'}\n\n"
        "📌 Tizimga kirish tartibi:\n\n"
        "* Login: Sizga berilgan talaba ID raqami.\n"
        "* Parol: Pasportingizning seriya va raqami.\n\n"
        "⚠️ Muhim: Tizimga birinchi marta kirganingizdan so‘ng xavfsizlik maqsadida "
        "parolingizni albatta almashtiring.\n\n"
        "Hurmat bilan,\n"
        "Qarshi xalqaro universiteti ma’muriyati."
    )


def already_registered(hemis_id: str) -> str:
    return (
        "ℹ️ Siz avval ro‘yxatdan o‘tgansiz.\n\n"
        f"🆔 HEMIS ID: {hemis_id}\n\n"
        "Student tizimiga kirish:\n"
        f"{STUDENT_SITE_NAME}"
    )
