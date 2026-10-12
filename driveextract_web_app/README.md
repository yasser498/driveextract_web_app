# DriveExtract

واجهة ويب RTL لتحويل روابط Google Drive Viewer إلى PDF وصور بدون رفع ملفات من الجهاز.

## التشغيل السريع عبر Docker

```bash
docker compose up --build
```

ثم افتح:

- Frontend: http://localhost:3000
- API: http://localhost:8000/docs

## البنية

- `frontend/` — Next.js 15 + React 19
- `backend/` — FastAPI + BeautifulSoup + Pillow
- `backend/storage/` — الملفات الناتجة مؤقتًا

## ما يدعمه التطبيق

- رابط واحد أو عدة روابط
- PDF واحد لكل رابط
- صور PNG لكل رابط
- PDF + صور
- تقدم حي لكل رابط
- تنزيل كل النتائج ZIP
- استخراج اسم الملف من صفحة العارض قدر الإمكان

## ملاحظة مهمة

المحرك الحالي يعتمد على بنية Google Drive Viewer التي تحتوي عناصر مثل:

```css
li.vyqwGc[data-page-index]
img.TH5Red[data-src]
```

إذا غيّرت Google بنية العارض مستقبلًا، يلزم تحديث selectors في `backend/app/main.py`.

## إعداد الإنتاج

### Frontend
اضبط:

```env
NEXT_PUBLIC_API_BASE=https://api.example.com
```

### Backend
اضبط:

```env
CORS_ORIGINS=https://app.example.com
```

يفضّل تشغيل FastAPI على VPS لأن المعالجة قد تكون طويلة وملفات الصور/PDF قد تكون كبيرة. يمكن نشر Next.js على Vercel أو على نفس الـVPS.
