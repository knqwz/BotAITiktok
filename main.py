import os
import time
import json
import threading
import requests
from flask import Flask

ung_dung_flask = Flask(__name__)

KHOA_API_GEMINI = os.environ.get("GEMINI_API_KEY", "")
MA_SESSION_ID = os.environ.get("TIKTOK_SESSION_ID", "")

TIEU_DE_HTTP_TIKTOK = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Cookie": f"sessionid={MA_SESSION_ID}; sessionid_ss={MA_SESSION_ID};",
    "Content-Type": "application/json"
}

LOI_DAN_CHO_AI = """
Bạn là trợ lý AI đại diện cho chủ kênh TikTok. Nhiệm vụ của bạn là tự động phản hồi tin nhắn riêng của người xem.
Hãy tuân thủ các quy tắc sau:
1. Trả lời cực kỳ ngắn gọn, tự nhiên, thân thiện và lịch sự (dưới 15 từ).
2. Đóng vai trực tiếp là chủ kênh, không tự xưng là AI/Robot trừ khi đối phương hỏi thẳng.
3. Nếu người dùng hỏi thông tin không rõ, hãy mời họ theo dõi kênh hoặc để lại bình luận trên video mới nhất.
4. Tuyệt đối không sử dụng ngôn từ thô tục, tranh cãi hay tiết lộ thông tin cá nhân bảo mật.
"""

def tao_cau_tra_loi_tu_gemini(noi_dung_tin_nhan_den):
    duong_dan_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={KHOA_API_GEMINI}"
    cau_truc_du_lieu_gemini = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"{LOI_DAN_CHO_AI}\n\nTin nhắn từ người dùng: '{noi_dung_tin_nhan_den}'"
                    }
                ]
            }
        ]
    }
    tieu_de_gemini = {"Content-Type": "application/json"}
    try:
        phan_hoi_gemini = requests.post(
            duong_dan_gemini,
            headers=tieu_de_gemini,
            data=json.dumps(cau_truc_du_lieu_gemini),
            timeout=10
        )
        if phan_hoi_gemini.status_code == 200:
            du_lieu_json = phan_hoi_gemini.json()
            return du_lieu_json["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        pass
    return "Cảm ơn bạn đã nhắn tin cho mình nhé!"

def lay_danh_sach_cuoc_tro_truyen_tiktok():
    duong_dan_danh_sach = "https://www.tiktok.com/api/im/chat/list/?count=10"
    try:
        phan_hoi = requests.get(duong_dan_danh_sach, headers=TIEU_DE_HTTP_TIKTOK, timeout=10)
        if phan_hoi.status_code == 200:
            return phan_hoi.json()
    except Exception:
        pass
    return None

def gui_tin_nhan_tiktok_web(id_cuoc_tro_truyen, noi_dung_phan_hoi):
    duong_dan_gui_tin = "https://www.tiktok.com/api/im/message/send/"
    du_lieu_gui = {
        "conversation_id": id_cuoc_tro_truyen,
        "type": 1,
        "content": json.dumps({"text": noi_dung_phan_hoi})
    }
    try:
        requests.post(duong_dan_gui_tin, headers=TIEU_DE_HTTP_TIKTOK, data=json.dumps(du_lieu_gui), timeout=10)
    except Exception:
        pass

def vong_lap_xu_ly_tin_nhan_chay_ngam():
    danh_sach_tin_nhan_da_xu_ly = set()
    while True:
        du_lieu_chat = lay_danh_sach_cuoc_tro_truyen_tiktok()
        if du_lieu_chat and "conversations" in du_lieu_chat:
            for cuoc_hien_tai in du_lieu_chat["conversations"]:
                id_cuoc_tro_truyen = cuoc_hien_tai.get("conversation_id")
                tin_nhan_cuoi = cuoc_hien_tai.get("last_message", {})
                id_tin_nhan = tin_nhan_cuoi.get("id")
                noi_dung_tin_nhan = tin_nhan_cuoi.get("content", {}).get("text")
                la_tin_nhan_cua_toi = tin_nhan_cuoi.get("from_user_id") == cuoc_hien_tai.get("user_id")
                
                if id_tin_nhan and id_tin_nhan not in danh_sach_tin_nhan_da_xu_ly:
                    danh_sach_tin_nhan_da_xu_ly.add(id_tin_nhan)
                    if noi_dung_tin_nhan and not la_tin_nhan_cua_toi:
                        cau_tra_loi = tao_cau_tra_loi_tu_gemini(noi_dung_tin_nhan)
                        gui_tin_nhan_tiktok_web(id_cuoc_tro_truyen, cau_tra_loi)
        time.sleep(5)

@ung_dung_flask.route('/')
def kiem_tra_trang_thai_may_chu():
    return "TikTok Gemini Bot Server Online 24/7", 200

luong_chay_ngam = threading.Thread(target=vong_lap_xu_ly_tin_nhan_chay_ngam, daemon=True)
luong_chay_ngam.start()

if __name__ == '__main__':
    cong_may_chu = int(os.environ.get("PORT", 5000))
    ung_dung_flask.run(host='0.0.0.0', port=cong_may_chu)