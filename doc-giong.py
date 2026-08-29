# -*- coding: utf-8 -*-
"""Đọc sẵn toàn bộ câu trả lời trong index.html ra file MP3 bằng giọng Vbee.

Chạy:  python3 doc-giong.py            → đọc lại những câu chưa có file
       python3 doc-giong.py --tat-ca   → đọc lại hết, ghi đè

File ra: audio/phanhoa/<id>.mp3 và audio/trang/<id>.mp3
Sửa nội dung trong index.html xong thì chạy lại lệnh này là giọng cập nhật theo.
"""
import json, os, re, sys, time, urllib.request, urllib.error

GOC = os.path.dirname(os.path.abspath(__file__))
CAU_HINH_VBEE = "/Users/macbook/Documents/TOOL VIDEO - CLAUDE/MASTER EDIT Claude/app/config.json"

GIONG = {
    "phanhoa": "n_hanoi_male_phanhoa_news_vc",        # Phan Hoa (nam, đọc tin)
    "trang":   "n_hanoi_female_trangcunday_news_vc",  # Trang (nữ, đọc tin)
}
BITRATE = 64          # đủ trong cho giọng nói, file nhẹ để web tải nhanh trên 4G
TOC_DO = 1.0


def lay_cau_tra_loi():
    """Rút (id, lời đọc) từ index.html."""
    html = open(os.path.join(GOC, "index.html"), encoding="utf-8").read()
    ds = []
    # tách theo từng mục rồi lấy lời đọc đầu tiên của mục đó — không phụ thuộc thứ tự các trường
    for khoi in re.finditer(r'id:"([a-z0-9-]+)"(.*?)(?=\n\s*\{\s*\n?\s*id:"|\n\];)', html, re.S):
        loi = re.search(r'noi:"(.*?)",?\s*\n', khoi.group(2), re.S)
        if loi:
            ds.append((khoi.group(1), loi.group(1)))
    kh = re.search(r'KHONG_HIEU = \{\s*\n\s*noi:"(.*?)",', html, re.S)
    if kh:
        ds.append(("khong-hieu", kh.group(1)))
    # các câu máy tự nói để báo cho khách, thay cho chữ trên màn hình
    ds.append(("chao-giong", "Dạ em nghe đây ạ."))
    ds.append(("mo-trinh-duyet", "Dạ anh chị đang mở bằng ứng dụng Zalo nên micro không dùng được. "
                                 "Anh chị bấm dấu ba chấm ở góc trên bên phải, rồi chọn mở bằng trình duyệt, "
                                 "là nói chuyện với em được ngay ạ."))
    ds.append(("khong-nghe-duoc", "Dạ để nói chuyện bằng giọng nói với em, anh chị mở trang này bằng Chrome hoặc Safari giúp em ạ. "
                                  "Hoặc anh chị bấm nút nhắn Zalo, nút gọi ở phía dưới màn hình, nhân viên bên em phản hồi ngay."))
    ds.append(("nghi-tay", "Dạ khi nào cần hỏi tiếp, anh chị bấm nút giữa màn hình là em nghe ngay ạ."))
    ds.append(("cho-mot-chut", "Dạ anh chị chờ em một chút ạ."))
    return ds


def _headers(app_id, token):
    return {"Authorization": "Bearer " + token, "App-Id": app_id,
            "Content-Type": "application/json"}


def _goi(url, method, headers, payload=None, timeout=60):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8")
        return json.loads(raw) if raw.strip() else {}


def _dig(d, *keys):
    stack = [d]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for k in keys:
                if k in cur and cur[k] not in (None, ""):
                    return cur[k]
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return None


def doc(text, voice_code, out_path, app_id, token, endpoint):
    h = _headers(app_id, token)
    payload = {"text": text, "mode": "async", "voiceCode": voice_code,
               "webhookUrl": "https://lagia.local/vbee-callback",
               "outputFormat": "mp3", "bitrate": BITRATE, "speed": TOC_DO,
               "clientPause": {"sentenceBreak": 0.5, "paragraphBreak": 0.8}}
    res = _goi(endpoint, "POST", h, payload)
    link = _dig(res, "audioLink", "audio_link", "audio_url", "link")
    rid = _dig(res, "requestId", "request_id", "id")
    if not link and rid:
        han = time.time() + 180
        while time.time() < han:
            time.sleep(2)
            try:
                st = _goi(endpoint + "/requests/" + str(rid), "GET", h)
            except urllib.error.HTTPError as e:
                if e.code in (404, 425):
                    continue
                raise
            link = _dig(st, "audioLink", "audio_link", "audio_url", "link")
            if link:
                break
            if str(_dig(st, "status") or "").upper() in ("FAILED", "ERROR"):
                raise RuntimeError("Vbee báo lỗi: " + json.dumps(st, ensure_ascii=False)[:300])
    if not link:
        raise RuntimeError("Không lấy được file giọng: " + json.dumps(res, ensure_ascii=False)[:300])
    with urllib.request.urlopen(urllib.request.Request(link), timeout=120) as r, open(out_path, "wb") as f:
        f.write(r.read())
    return out_path


def main():
    lam_lai = "--tat-ca" in sys.argv
    cfg = json.load(open(CAU_HINH_VBEE, encoding="utf-8"))["vbee"]
    app_id, token = cfg["app_id"].strip(), cfg["token"].strip()
    endpoint = (cfg.get("endpoint") or "https://api.vbee.vn/v1/tts").rstrip("/")

    ds = lay_cau_tra_loi()
    print("Có %d câu trả lời, đọc bằng %d giọng." % (len(ds), len(GIONG)))
    loi = []
    for ten, ma in GIONG.items():
        thu_muc = os.path.join(GOC, "audio", ten)
        os.makedirs(thu_muc, exist_ok=True)
        for i, (cid, text) in enumerate(ds, 1):
            dich = os.path.join(thu_muc, cid + ".mp3")
            if os.path.exists(dich) and os.path.getsize(dich) > 2000 and not lam_lai:
                print("  [%s %2d/%d] %-14s bỏ qua (đã có)" % (ten, i, len(ds), cid))
                continue
            try:
                doc(text, ma, dich, app_id, token, endpoint)
                print("  [%s %2d/%d] %-14s xong %6.0f KB" % (ten, i, len(ds), cid, os.path.getsize(dich) / 1024))
            except Exception as e:
                loi.append((ten, cid, str(e)[:160]))
                print("  [%s %2d/%d] %-14s LỖI: %s" % (ten, i, len(ds), cid, str(e)[:160]))
    if loi:
        print("\n%d câu bị lỗi, chạy lại lệnh này để đọc tiếp:" % len(loi))
        for g, c, e in loi:
            print("  -", g, c, "|", e)
    else:
        print("\nĐọc xong hết.")


if __name__ == "__main__":
    main()
