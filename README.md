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

## Testlar

```bash
pip install -r requirements-dev.txt
python -m pytest
```
