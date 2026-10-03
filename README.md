# KIU HEMIS ID bot

Talaba Telegram bot orqali ro'yxatdan o'tadi: F.I.Sh. → telefon → pasport → tasdiqlash.
Bot shu ma'lumotlarni Excel ro'yxat bilan solishtirib, talabaning HEMIS IDsini topadi va
student.kiu.uz tizimiga kirish yo'riqnomasini yuboradi.

## O'rnatish

```bash
pip install -r requirements.txt
cp .env.example .env   # BOT_TOKEN ni yozing
```

Talabalar ro'yxatini `data.xlsx` nomi bilan loyiha papkasiga qo'ying (yoki `.env` da `EXCEL_FILE` ni o'zgartiring).
Faylda **HEMIS ID** ustuni va kamida **Pasport** yoki **Telefon** ustuni bo'lishi kerak; F.I.Sh. ustuni ham tavsiya etiladi.
Ustunlar sarlavha nomi bo'yicha avtomatik aniqlanadi. Fayl almashtirilsa, bot uni qayta ishga tushirmasdan o'qiydi.

`.env`, Excel fayl va `*.db` baza `.gitignore` da: ular GitHub'ga yuklanmaydi.

## Ishga tushirish

```bash
python bot.py
```

`WEBHOOK_HOST` bo'sh bo'lsa polling, to'ldirilgan bo'lsa webhook + veb-sahifa (`/`, `/api/check`, `/health`) rejimida ishlaydi.

## Ro'yxatdan o'tganlarni Google Sheets'ga yozish (ixtiyoriy)

Har bir ro'yxatdan o'tgan talaba avval bot bazasiga, keyin Google Sheets'ga yoziladi
(Telegram ID, username, F.I.Sh., telefon, pasport, HEMIS ID, vaqt). Google vaqtincha ishlamasa,
bot keyinroq qayta yuboradi. Qayta ro'yxatdan o'tgan talabaning qatori yangilanadi.

1. Yangi Google Sheets jadval oching.
2. **Kengaytmalar → Apps Script** ni bosing, ochilgan oynadagi kodni o'chirib,
   `google_apps_script/registrations.gs` faylidagi kodni qo'ying va saqlang.
3. Chap menyuda **⚙️ Project Settings → Script properties → Add script property**:
   nomi `SECRET`, qiymati — uzun tasodifiy maxfiy so'z (masalan, 32+ belgi).
   Skript jadvaldan emas, script.google.com orqali yaratilgan bo'lsa, `SPREADSHEET_ID` xususiyatini ham
   qo'shing (jadval havolasidagi `/d/` va `/edit` orasidagi qism).
   Tekshirish: funksiyalar ro'yxatidan `testYozish` ni tanlab ▶ Run bosing — jadvalda sinov qatori paydo bo'lishi kerak.
4. **Deploy → New deployment → Type: Web app**:
   - *Execute as*: **Me**
   - *Who has access*: **Anyone**
   - **Deploy** ni bosing, Google ruxsat so'rasa — tasdiqlang.
   - Berilgan **Web app URL** ni nusxalang (`https://script.google.com/macros/s/.../exec`).
5. `.env` ga yozing va botni qayta ishga tushiring:
   ```
   SHEETS_WEBHOOK_URL=https://script.google.com/macros/s/.../exec
   SHEETS_SECRET=3-qadamdagi maxfiy so'z
   ```

"Anyone" bo'lsa ham, `SECRET` ni bilmagan odam jadvalga yoza olmaydi va undan hech narsa o'qiy olmaydi.
Jadvalda pasport va telefonlar bo'ladi — uni faqat mas'ul xodimlarga ulashing.
Apps Script kodini o'zgartirsangiz: **Deploy → Manage deployments → ✏️ → Version: New version**.

## Majburiy kanal (ixtiyoriy)

Botdan faqat kanal a'zolari foydalanishi uchun:
1. Botni kanalga **administrator** qilib qo'shing (a'zolikni tekshira olishi uchun; boshqa huquq shart emas).
2. Render → Environment: `REQUIRED_CHANNEL=@kanal_username`
   (yopiq kanal bo'lsa `-100...` ID va `REQUIRED_CHANNEL_URL=https://t.me/+taklif_havolasi`).

A'zo bo'lmagan foydalanuvchiga bot "Kanalga a'zo bo'ling" xabarini va «✅ Tekshirish» tugmasini ko'rsatadi.
Standart kanal `@kiu_uz`; tekshiruvni o'chirish uchun `REQUIRED_CHANNEL=off`.

## Rassilka (adminlar uchun)

1. Botga `/id` yozing — bot Telegram ID raqamingizni aytadi.
2. Render → Environment: `ADMIN_IDS=123456789` (bir nechta admin bo'lsa vergul bilan).
3. Botga `/rassilka` yozing, xabarni yuboring (matn, rasm, video yoki fayl).
   Matnda `{ism}` — talabaning ismi, `{fio}` — to'liq F.I.Sh. bilan almashtiriladi.
4. Namunani ko'rib, kimga yuborishni tanlang: hammaga / HEMIS ID olganlarga / topilmaganlarga.
   Oxirida bot nechtasiga yetib borganini aytadi. Bekor qilish: `/bekor`.

Qabul qiluvchilar bot bazasidan olinadi. Apps Script'da `listRows()` bo'lsa (repodagi
`google_apps_script/registrations.gs`), Google Sheets'dagi ro'yxat ham qo'shiladi — bu Render qayta
ishga tushib bot bazasi tozalanganda ham hammaga yetib borishini ta'minlaydi.

## Testlar

```bash
pip install -r requirements-dev.txt
python -m pytest
```
