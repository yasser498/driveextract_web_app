# DriveExtract

واجهة ويب RTL لتحويل روابط Google Drive Viewer إلى PDF وصور بدون رفع ملفات من الجهاز.

## إصلاح الاتصال بين الواجهة والمحرك

الإصدار الحالي لا يجعل المتصفح يتصل مباشرة بـ `localhost:8000`.
الواجهة ترسل الطلبات إلى Next.js على نفس الدومين عبر:

```text
/api/proxy/...
```

ثم Next.js يتصل داخليًا بخدمة FastAPI عبر المتغير:

```env
API_INTERNAL_BASE=http://api:8000
```

وبذلك لا يحتاج المستخدم إلى الوصول إلى منفذ FastAPI ولا توجد مشكلة CORS بين المتصفح والـAPI.

## التشغيل السريع عبر Docker

```bash
docker compose up --build
```

ثم افتح:

```text
http://localhost:3000
```

يمكن اختبار المحرك من داخل حاوية الواجهة عبر البروكسي:

```text
http://localhost:3000/api/proxy/api/health
```

المفترض أن يعيد:

```json
{"ok":true}
```

## البنية

- `frontend/` — Next.js + React
- `backend/` — FastAPI + BeautifulSoup + Pillow
- `backend/storage/` — الملفات الناتجة مؤقتًا

## نشر الواجهة والـAPI على نفس VPS

الأبسط هو تشغيل `docker compose` ووضع Nginx أو Cloudflare أمام المنفذ 3000 فقط. لا يلزم نشر المنفذ 8000 للعامة.

## إذا كانت الواجهة على Vercel والـAPI على VPS

اضبط متغير البيئة في Vercel:

```env
API_INTERNAL_BASE=https://api.example.com
```

وفي هذه الحالة يجب أن يكون عنوان FastAPI متاحًا من خوادم Vercel عبر HTTPS. المتصفح نفسه سيستمر في استخدام `/api/proxy` على دومين Vercel.

## المخرجات

- PDF واحد لكل رابط
- صور PNG لكل رابط
- PDF + صور ZIP
- رابط واحد أو عدة روابط
- تقدم مستقل لكل رابط
- تنزيل جميع النتائج ZIP
