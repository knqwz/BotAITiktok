import os
import time
import json
import re
import threading
import requests
from flask import Flask

ung_dung_flask = Flask(__name__)

khoa_api_gemini = os.environ.get("GEMINI_API_KEY", "").strip()
chuoi_cookie_tho_nhan_tu_render = os.environ.get("TIKTOK_COOKIE", "")

def ham_trich_xuat_va_lam_sach_cookie(chuoi_cookie_goc):
    danh_sach_khoa_truy_van = ['sessionid', 'sessionid_ss', 'ttwid', 'passport_csrf_token']
    ket_qua_trich_xuat = []
    for khoa_can_tim in danh_sach_khoa_truy_van:
        tim_kiem = re.search(fr'{khoa_can_tim}=([^;\s\r\n]+)', chuoi_cookie_goc)
        if tim_kiem:
            ket_qua_trich_xuat.append(f"{khoa_can_tim}={tim_kiem.group(1)}")
    chuoi_cookie_hoan_chinh = "; ".join(ket_qua_trich_xuat)
    return chuoi_cookie_hoan_chinh

chuoi_cookie_tiktok_chuan_hoa = ham_trich_xuat_va_lam_sach_cookie(chuoi_cookie_tho_nhan_tu_render)

tieu_de_gui_yieu_cau_tiktok = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Cookie": chuoi_cookie_tiktok_chuan_hoa,
    "Content-Type": "application/json",
    "Referer": "https://www.tiktok.com/messages",
    "Origin": "https://www.tiktok.com"
}

kịch_ban_phan_hoi_ai = """
Bạn là trợ lý AI đại diện cho chủ kênh TikTok. Nhiệm vụ của bạn là tự động phản hồi tin nhắn riêng của người xem.
Hãy tuân thủ các quy tắc sau:
1. Trả lời cực kỳ ngắn gọn, tự nhiên, thân thiện và lịch sự (dưới 15 từ).
2. Đóng vai trực tiếp là chủ kênh, không tự xưng là AI/Robot trừ khi đối phương hỏi thẳng.
3. Nếu người dùng hỏi thông tin không rõ, hãy mời họ theo dõi kênh hoặc để lại bình luận trên video mới nhất.
4. Tuyệt đối không sử dụng ngôn từ thô tục, tranh cãi hay tiết lộ thông tin cá nhân bảo mật.
"""

def ham_tao_cau_tra_loi_tu_gemini(noi_dung_tin_nhan_den):
    duong_dan_api_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={khoa_api_gemini}"
    du_lieu_gui_gemini = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"{kịch_ban_phan_hoi_ai}\n\nTin nhắn người hâm mộ gửi: '{noi_dung_tin_nhan_den}'"
                    }
                ]
            }
        ]
    }
    tieu_de_gemini = {"Content-Type": "application/json"}
    try:
        phan_hoi_gemini = requests.post(
            duong_dan_api_gemini,
            headers=tieu_de_gemini,
            data=json.dumps(du_lieu_gui_gemini),
            timeout=10
        )
        if phan_hoi_gemini.status_code == 200:
            du_lieu_tra_ve = phan_hoi_gemini.json()
            return du_lieu_tra_ve["candidates"][0]["content"]["parts"][0]["text"].strip()
        else:
            print(f"[LỖI GEMINI API] Mã trạng thái: {phan_hoi_gemini.status_code}")
    except Exception as loi_gemini:
        print(f"[NGOẠI LỆ GEMINI API] {loi_gemini}")
    return "Cảm ơn bạn đã nhắn tin cho mình nhé!"

def ham_lay_danh_sach_tin_nhan_tiktok():
    duong_dan_danh_sach_chat = "https://www.tiktok.com/api/im/chat/list/?count=10"
    try:
        phan_hoi_tiktok = requests.get(duong_dan_danh_sach_chat, headers=tieu_de_gui_yieu_cau_tiktok, timeout=10)
        print(f"[KIỂM TRA TIKTOK API] Mã trạng thái: {phan_hoi_tiktok.status_code}")
        if phan_hoi_tiktok.status_code == 200:
            return phan_hoi_tiktok.json()
        else:
            print(f"[LỖI TIKTOK RESPONSE] Chi tiết: {phan_hoi_tiktok.text[:150]}")
    except Exception as loi_tiktok:
        print(f"[NGOẠI LỆ TIKTOK LẤY TIN] {loi_tiktok}")
    return None

def ham_gui_tin_nhan_tiktok(id_cuoc_tro_truyen, noi_dung_phan_hoi):
    duong_dan_gui_tin_nhan = "https://www.tiktok.com/api/im/message/send/"
    du_lieu_gui_tin = {
        "conversation_id": id_cuoc_tro_truyen,
        "type": 1,
        "content": json.dumps({"text": noi_dung_phan_hoi})
    }
    try:
        phan_hoi_gui = requests.post(duong_dan_gui_tin_nhan, headers=tieu_de_gui_yieu_cau_tiktok, data=json.dumps(du_lieu_gui_tin), timeout=10)
        print(f"[GỬI TIN NHẮN THÀNH CÔNG] Trạng thái: {phan_hoi_gui.status_code} - Kết quả: {phan_hoi_gui.text[:100]}")
    except Exception as loi_gui_tin:
        print(f"[LỖI GỬI TIN NHẮN] {loi_gui_tin}")

def ham_vong_lap_xu_ly_tin_nhan_chay_ngam():
    danh_sach_id_tin_nhan_da_xu_ly = set()
    print(f"[BOT KHỞI CHẠY HỢP LỆ] Cookie đã bóc tách: {chuoi_cookie_tiktok_chuan_hoa[:50]}...")
    while True:
        du_lieu_hop_thu = ham_lay_danh_sach_tin_nhan_tiktok()
        if du_lieu_hop_thu and "conversations" in du_lieu_hop_thu:
            for cuoc_tro_truyen in du_lieu_hop_thu["conversations"]:
                id_cuoc_tro_truyen = cuoc_tro_truyen.get("conversation_id")
                tin_nhan_gần_nhat = cuoc_tro_truyen.get("last_message", {})
                id_tin_nhan = tin_nhan_gần_nhat.get("id")
                noi_dung_tin_nhan = tin_nhan_gần_nhat.get("content", {}).get("text")
                la_tin_nhan_do_minh_gui = tin_nhan_gần_nhat.get("from_user_id") == cuoc_tro_truyen.get("user_id")
                
                if id_tin_nhan and id_tin_nhan not in danh_sach_id_tin_nhan_da_xu_ly:
                    danh_sach_id_tin_nhan_da_xu_ly.add(id_tin_nhan)
                    if noi_dung_tin_nhan and not la_tin_nhan_do_minh_gui:
                        print(f"[PHÁT HIỆN TIN NHẮN MỚI] Nội dung nhận: '{noi_dung_tin_nhan}'")
                        cau_tra_loi_ai = ham_tao_cau_tra_loi_tu_gemini(noi_dung_tin_nhan)
                        ham_gui_tin_nhan_tiktok(id_cuoc_tro_truyen, cau_tra_loi_ai)
        time.sleep(5)

@ung_dung_flask.route('/')
def ham_kiem_tra_trang_thai_may_chu():
    return "TikTok Gemini Auto Responder Server - Active 24/7", 200

luong_chay_ngam = threading.Thread(target=ham_vong_lap_xu_ly_tin_nhan_chay_ngam, daemon=True)
luong_chay_ngam.start()

if __name__ == '__main__':
    cong_may_chu = int(os.environ.get("PORT", 5000))
    ung_dung_flask.run(host='0.0.0.0', port=cong_may_chu)