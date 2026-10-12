'use client';

import { useMemo, useState } from 'react';
import { FileArchive, FileImage, FileText, Link2, Plus, Sparkles, Trash2 } from 'lucide-react';
import { createJob } from '@/lib/api';
import { JobView } from '@/components/JobView';

type Output = 'pdf' | 'images' | 'both';

export default function Home() {
  const [urls, setUrls] = useState(['']);
  const [bulk, setBulk] = useState('');
  const [output, setOutput] = useState<Output>('pdf');
  const [width, setWidth] = useState(1600);
  const [keepImages, setKeepImages] = useState(true);
  const [jobId, setJobId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const validUrls = useMemo(() => urls.map(x => x.trim()).filter(Boolean), [urls]);

  function addBulk() {
    const parsed = bulk.split(/\r?\n/).map(x => x.trim()).filter(Boolean);
    if (!parsed.length) return;
    setUrls(parsed);
    setBulk('');
  }

  async function submit() {
    setError('');
    if (!validUrls.length) return setError('أضف رابطًا واحدًا على الأقل.');
    setLoading(true);
    try {
      const res = await createJob({ urls: validUrls, output, image_width: width, keep_images: keepImages });
      setJobId(res.job_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'تعذر بدء المهمة');
    } finally {
      setLoading(false);
    }
  }

  if (jobId) return <JobView jobId={jobId} onNew={() => setJobId(null)} />;

  return (
    <main className="shell">
      <header className="hero">
        <div className="brand"><span className="brandMark"><Sparkles size={20}/></span> DriveExtract</div>
        <div className="eyebrow">Google Drive Viewer Extractor</div>
        <h1>حوّل روابط العارض إلى <span>PDF وصور</span> باحتراف.</h1>
        <p>ألصق رابطًا واحدًا أو عدة روابط، اختر المخرجات، واترك الباقي على النظام.</p>
      </header>

      <section className="panel">
        <div className="stepTitle"><span>1</span><div><b>أضف الروابط</b><small>لا حاجة لرفع أي ملف</small></div></div>

        <div className="urlList">
          {urls.map((url, i) => (
            <div className="urlRow" key={i}>
              <Link2 size={19}/>
              <input value={url} onChange={e => setUrls(v => v.map((x, n) => n === i ? e.target.value : x))} placeholder="https://drive.google.com/..." />
              {urls.length > 1 && <button className="iconBtn" onClick={() => setUrls(v => v.filter((_, n) => n !== i))}><Trash2 size={18}/></button>}
            </div>
          ))}
          <button className="ghostBtn" onClick={() => setUrls(v => [...v, ''])}><Plus size={18}/> إضافة رابط</button>
        </div>

        <details className="bulkBox">
          <summary>لصق عدة روابط دفعة واحدة</summary>
          <textarea value={bulk} onChange={e => setBulk(e.target.value)} placeholder={'رابط 1\nرابط 2\nرابط 3'} />
          <button className="miniBtn" onClick={addBulk}>إضافة الروابط</button>
        </details>

        <div className="divider" />
        <div className="stepTitle"><span>2</span><div><b>اختر المخرجات</b><small>لكل رابط نتيجة مستقلة</small></div></div>

        <div className="outputGrid">
          <button className={`choice ${output === 'pdf' ? 'active' : ''}`} onClick={() => setOutput('pdf')}>
            <FileText/><b>PDF واحد</b><small>كل الصفحات في ملف واحد</small>
          </button>
          <button className={`choice ${output === 'images' ? 'active' : ''}`} onClick={() => setOutput('images')}>
            <FileImage/><b>صور PNG</b><small>كل صفحة كصورة مستقلة</small>
          </button>
          <button className={`choice ${output === 'both' ? 'active' : ''}`} onClick={() => setOutput('both')}>
            <FileArchive/><b>الاثنان</b><small>PDF + صور مضغوطة</small>
          </button>
        </div>

        <details className="advanced">
          <summary>إعدادات متقدمة</summary>
          <div className="settingsGrid">
            <label>جودة الصور<select value={width} onChange={e => setWidth(Number(e.target.value))}><option value={1200}>1200px</option><option value={1600}>1600px — موصى به</option><option value={2000}>2000px</option><option value={2400}>2400px</option></select></label>
            <label className="toggleLabel">الاحتفاظ بالصور<input type="checkbox" checked={keepImages} onChange={e => setKeepImages(e.target.checked)} /></label>
          </div>
        </details>

        {error && <div className="errorBox">{error}</div>}
        <button className="primaryBtn" disabled={loading || !validUrls.length} onClick={submit}>{loading ? 'جارٍ بدء المهمة...' : `بدء المعالجة — ${validUrls.length || 0} رابط`}</button>
      </section>
    </main>
  );
}
