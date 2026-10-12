'use client';

import { useEffect, useState } from 'react';
import { CheckCircle2, Download, FileArchive, FileImage, FileText, LoaderCircle, RotateCcw, XCircle } from 'lucide-react';
import { fileUrl, getJob, Job } from '@/lib/api';

export function JobView({ jobId, onNew }: { jobId: string; onNew: () => void }) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let stop = false;
    async function tick() {
      try {
        const next = await getJob(jobId);
        if (!stop) setJob(next);
        if (!stop && next.status !== 'done') setTimeout(tick, 1200);
      } catch (e) {
        if (!stop) setError(e instanceof Error ? e.message : 'تعذر قراءة حالة المهمة');
      }
    }
    tick();
    return () => { stop = true; };
  }, [jobId]);

  return (
    <main className="shell resultsShell">
      <header className="hero compact">
        <div className="brand">DriveExtract</div>
        <h1>{job?.status === 'done' ? 'اكتملت المعالجة' : 'نعالج ملفاتك الآن'}</h1>
        <p>{job?.status === 'done' ? 'كل ملف جاهز للتحميل بشكل مستقل.' : 'يمكنك متابعة كل رابط وحالته لحظة بلحظة.'}</p>
      </header>

      <section className="panel">
        <div className="progressHeader"><span>التقدم الكلي</span><b>{job?.progress ?? 0}%</b></div>
        <div className="progress"><i style={{ width: `${job?.progress ?? 0}%` }} /></div>
        {error && <div className="errorBox">{error}</div>}

        <div className="resultList">
          {(job?.items ?? []).map(item => {
            const pct = item.pages_total ? Math.round((item.pages_done / item.pages_total) * 100) : 0;
            return (
              <article className="resultCard" key={item.index}>
                <div className="statusIcon">{item.status === 'done' ? <CheckCircle2/> : item.status === 'failed' ? <XCircle/> : <LoaderCircle className="spin"/>}</div>
                <div className="resultMain">
                  <div className="resultTop"><div><b>{item.name || `الرابط ${item.index}`}</b><small>{item.pages_total ? `${item.pages_done} / ${item.pages_total} صفحة` : item.status}</small></div><span>{item.status === 'done' ? 'جاهز' : item.status === 'failed' ? 'فشل' : `${pct}%`}</span></div>
                  <div className="miniProgress"><i style={{ width: `${item.status === 'done' ? 100 : pct}%` }} /></div>
                  {item.error && <div className="itemError">{item.error}</div>}
                  <div className="actions">
                    {item.pdf_url && <a href={fileUrl(item.pdf_url)}><FileText size={17}/> تنزيل PDF</a>}
                    {item.images_zip_url && <a href={fileUrl(item.images_zip_url)}><FileImage size={17}/> تنزيل الصور</a>}
                  </div>
                </div>
              </article>
            );
          })}
        </div>

        {job?.status === 'done' && (
          <div className="finishActions">
            {job.all_zip_url && <a className="primaryBtn linkBtn" href={fileUrl(job.all_zip_url)}><Download size={19}/> تنزيل كل النتائج ZIP</a>}
            <button className="ghostBtn" onClick={onNew}><RotateCcw size={18}/> مهمة جديدة</button>
          </div>
        )}
      </section>
    </main>
  );
}
