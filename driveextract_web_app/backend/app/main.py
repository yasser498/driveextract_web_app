from __future__ import annotations

import io
import os
import re
import shutil
import threading
import uuid
import zipfile
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Literal
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, HttpUrl
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="DriveExtract API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OutputType = Literal["pdf", "images", "both"]

class CreateJobRequest(BaseModel):
    urls: list[HttpUrl] = Field(min_length=1, max_length=50)
    output: OutputType = "pdf"
    image_width: int = Field(default=1600, ge=800, le=3000)
    keep_images: bool = True

@dataclass
class ItemResult:
    index: int
    url: str
    status: str = "queued"
    name: str | None = None
    pages_total: int = 0
    pages_done: int = 0
    pdf_url: str | None = None
    images_zip_url: str | None = None
    error: str | None = None

@dataclass
class JobState:
    id: str
    status: str = "queued"
    progress: int = 0
    output: str = "pdf"
    items: list[ItemResult] = field(default_factory=list)
    all_zip_url: str | None = None

JOBS: dict[str, JobState] = {}
LOCK = threading.Lock()


def safe_name(name: str, fallback: str) -> str:
    name = (name or fallback).strip()
    name = re.sub(r"[\x00-\x1f<>:\"/\\|?*]+", "_", name)
    name = re.sub(r"\s+", " ", name).strip(" ._-")
    return (name or fallback)[:140]


def browser_headers(referer: str | None = None) -> dict[str, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
        "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
    }
    if referer:
        headers["Referer"] = referer
    return headers


def extract_document_name(html_text: str, fallback: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    candidates: list[str] = []
    for attrs in [
        {"property": "og:title"},
        {"name": "og:title"},
        {"name": "title"},
    ]:
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            candidates.append(tag.get("content").strip())
    if soup.title and soup.title.string:
        candidates.append(soup.title.string.strip())

    for value in candidates:
        value = re.sub(r"\s*[-–—|]\s*Google Drive.*$", "", value, flags=re.I)
        value = re.sub(r"\.pdf$", "", value, flags=re.I)
        if value:
            return safe_name(value, fallback)
    return fallback


def extract_page_records(html_text: str, base_url: str) -> list[dict]:
    soup = BeautifulSoup(html_text, "html.parser")
    records: list[dict] = []

    for li in soup.select("li.vyqwGc[data-page-index]"):
        try:
            page_index = int(li.get("data-page-index"))
        except Exception:
            continue
        img = li.select_one("div.LD67He img.TH5Red") or li.select_one("img.TH5Red")
        if not img:
            continue
        image_url = img.get("data-src") or img.get("src")
        if not image_url or image_url.startswith("data:"):
            continue
        records.append({"index": page_index, "url": urljoin(base_url, image_url)})

    if not records:
        for idx, img in enumerate(soup.select("img.TH5Red")):
            image_url = img.get("data-src") or img.get("src")
            if image_url and not image_url.startswith("data:"):
                records.append({"index": idx, "url": urljoin(base_url, image_url)})

    unique = {r["index"]: r for r in records}
    return [unique[k] for k in sorted(unique)]


def make_high_res(url: str, width: int) -> str:
    if re.search(r"([?&])w=\d+", url):
        return re.sub(r"([?&])w=\d+", lambda m: f"{m.group(1)}w={width}", url)
    if re.search(r"=s\d+(-rw)?(-v\d+)?$", url):
        return re.sub(r"=s\d+", f"=s{width}", url)
    return url


def fetch_viewer(url: str) -> tuple[str, str, requests.cookies.RequestsCookieJar]:
    response = requests.get(url, headers=browser_headers(), timeout=60)
    response.raise_for_status()
    return response.text, response.url, response.cookies


def images_to_pdf(image_files: list[Path], target: Path) -> None:
    opened: list[Image.Image] = []
    for path in sorted(image_files):
        img = Image.open(path).convert("RGB")
        opened.append(img.copy())
        img.close()
    if not opened:
        raise RuntimeError("لا توجد صور لإنشاء PDF")
    opened[0].save(target, "PDF", resolution=150.0, save_all=True, append_images=opened[1:])
    for img in opened:
        img.close()


def zip_folder(folder: Path, target: Path) -> None:
    target_resolved = target.resolve()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(folder.rglob("*")):
            if file.is_file() and file.resolve() != target_resolved:
                zf.write(file, file.relative_to(folder))


def set_job(job_id: str, **kwargs):
    with LOCK:
        job = JOBS[job_id]
        for k, v in kwargs.items():
            setattr(job, k, v)


def process_job(job_id: str, req: CreateJobRequest):
    job_dir = STORAGE_DIR / job_id
    pdf_dir = job_dir / "pdf"
    images_root = job_dir / "images"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    images_root.mkdir(parents=True, exist_ok=True)

    set_job(job_id, status="processing")
    total_items = len(req.urls)

    for item_idx, http_url in enumerate(req.urls):
        url = str(http_url)
        item = JOBS[job_id].items[item_idx]
        item.status = "reading"
        try:
            html, final_url, cookies = fetch_viewer(url)
            fallback = f"drive_file_{item_idx+1:03d}"
            name = extract_document_name(html, fallback)
            item.name = name

            records = extract_page_records(html, final_url)
            if not records:
                raise RuntimeError("لم أجد صور الصفحات داخل عارض Google Drive")

            item.pages_total = len(records)
            item.status = "downloading"
            image_dir = images_root / name
            image_dir.mkdir(parents=True, exist_ok=True)

            session = requests.Session()
            session.headers.update(browser_headers(url))
            for key, value in cookies.items():
                session.cookies.set(key, value)

            image_files: list[Path] = []
            for page_pos, record in enumerate(records, start=1):
                page_no = int(record["index"]) + 1
                image_url = make_high_res(record["url"], req.image_width)
                r = session.get(image_url, timeout=60)
                r.raise_for_status()
                img = Image.open(io.BytesIO(r.content)).convert("RGB")
                target = image_dir / f"page-{page_no:03d}.png"
                img.save(target, "PNG", optimize=True)
                img.close()
                image_files.append(target)
                item.pages_done = page_pos

                completed_before = item_idx / total_items
                within_item = (page_pos / max(len(records), 1)) / total_items
                set_job(job_id, progress=min(95, int((completed_before + within_item) * 100)))

            if req.output in ("pdf", "both"):
                item.status = "building_pdf"
                pdf_path = pdf_dir / f"{name}.pdf"
                duplicate = 2
                while pdf_path.exists():
                    pdf_path = pdf_dir / f"{name}_{duplicate}.pdf"
                    duplicate += 1
                images_to_pdf(image_files, pdf_path)
                item.pdf_url = f"/api/jobs/{job_id}/files/pdf/{pdf_path.name}"

            if req.output in ("images", "both"):
                images_zip = job_dir / f"{name}_images.zip"
                zip_folder(image_dir, images_zip)
                item.images_zip_url = f"/api/jobs/{job_id}/files/root/{images_zip.name}"

            if not req.keep_images and req.output == "pdf":
                shutil.rmtree(image_dir, ignore_errors=True)

            item.status = "done"
        except Exception as exc:
            item.status = "failed"
            item.error = str(exc)

    zip_target = job_dir / "all_results.zip"
    zip_folder(job_dir, zip_target)
    set_job(job_id, status="done", progress=100, all_zip_url=f"/api/jobs/{job_id}/files/root/{zip_target.name}")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/jobs")
def create_job(req: CreateJobRequest):
    job_id = uuid.uuid4().hex[:12]
    items = [ItemResult(index=i + 1, url=str(url)) for i, url in enumerate(req.urls)]
    JOBS[job_id] = JobState(id=job_id, output=req.output, items=items)
    thread = threading.Thread(target=process_job, args=(job_id, req), daemon=True)
    thread.start()
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    data = asdict(job)
    return data


@app.get("/api/jobs/{job_id}/files/{scope}/{filename}")
def download_file(job_id: str, scope: Literal["pdf", "root"], filename: str):
    base = STORAGE_DIR / job_id
    file_path = (base / ("pdf" if scope == "pdf" else "") / filename).resolve()
    if base.resolve() not in file_path.parents:
        raise HTTPException(400, "Invalid path")
    if not file_path.is_file():
        raise HTTPException(404, "File not found")
    return FileResponse(file_path, filename=file_path.name)
