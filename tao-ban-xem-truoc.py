# -*- coding: utf-8 -*-
"""Gộp index.html + toàn bộ file MP3 thành MỘT file HTML duy nhất.

Dùng khi cần gửi bản xem thử cho ai đó mà không kèm được thư mục audio
(ví dụ đăng lên Artifact của Claude). Bản deploy thật lên Netlify thì
dùng thẳng index.html + thư mục audio/, nhẹ hơn nhiều.

Chạy:  python3 tao-ban-xem-truoc.py
Ra:    ban-xem-truoc.html
"""
import base64, json, os, re

GOC = os.path.dirname(os.path.abspath(__file__))


def main():
    html = open(os.path.join(GOC, "index.html"), encoding="utf-8").read()

    kho = {}
    tong = 0
    for giong in sorted(os.listdir(os.path.join(GOC, "audio"))):
        thu_muc = os.path.join(GOC, "audio", giong)
        if not os.path.isdir(thu_muc):
            continue
        for ten in sorted(os.listdir(thu_muc)):
            if not ten.endswith(".mp3"):
                continue
            raw = open(os.path.join(thu_muc, ten), "rb").read()
            tong += len(raw)
            kho["audio/%s/%s" % (giong, ten)] = "data:audio/mpeg;base64," + base64.b64encode(raw).decode()

    print("Nhúng %d file giọng, %.1f MB gốc → khoảng %.1f MB sau khi mã hoá."
          % (len(kho), tong / 1048576, tong * 1.34 / 1048576))

    # nhúng bảng tra + đổi hàm lấy đường dẫn sang lấy từ bảng
    bang = "const KHO_TIENG = " + json.dumps(kho, ensure_ascii=False) + ";\n"
    html = html.replace(
        'function duongDanMp3(id){ return "audio/" + giongChon + "/" + id + ".mp3"; }',
        bang + 'function duongDanMp3(id){ return KHO_TIENG["audio/" + giongChon + "/" + id + ".mp3"] || ""; }',
        1)

    # bản một file: bỏ khung <!doctype>/<head>/<body> cho hợp định dạng Artifact
    html = html[html.index("<title>"):]
    html = html.replace("\n</head>\n<body>\n", "\n").replace("\n</body>\n</html>\n", "\n")

    ra = os.path.join(GOC, "ban-xem-truoc.html")
    open(ra, "w", encoding="utf-8").write(html)
    print("Xong:", ra, "%.1f MB" % (os.path.getsize(ra) / 1048576))


if __name__ == "__main__":
    main()
