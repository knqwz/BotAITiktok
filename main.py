import os
import time
import json
import re
import threading
import requests
from flask import Flask

ung_dung_flask = Flask(__name__)

khoa_api_gemini = os.environ.get("GEMINI_API_KEY", "").strip()
chuoi_cookie_tho_nhan_tu_render = os.environ.get("TIKTOK_COOKIE", "").strip()

def ham_trich_xuat_va_lam_sach_cookie(chuoi_cookie_goc):
    danh_sach_khoa_truy_van = ['sessionid', 'sessionid_ss', 'sid_tt', 'ttwid', 'tt_csrf_token', 'uid_tt', 'odin_tt']
    ket_qua_trich_xuat = []
    for khoa_can_tim in danh_sach_khoa_truy_van:
        tim_kiem = re.search(fr'{khoa_can_tim}=([^;\s\r\n]+)', chuoi_cookie_goc)
        if tim_kiem:
            ket_qua_trich_xuat.append(f"{khoa_can_tim}={tim_kiem.group(1)}")
    chuoi_cookie_hoan_chinh = "; ".join(ket_qua_trich_xuat)
    return chuoi_cookie_hoan_chinh

chuoi_cookie_tiktok_chuan_hoa = ham_trich_xuat_va_lam_sach_cookie(chuoi_cookie_tho_nhan_tu_render)
if not chuoi_cookie_tiktok_chuan_hoa:
    chuoi_cookie_tiktok_chuan_hoa = chuoi_cookie_tho_nhan_tu_render

tieu_de_gui_yeu_cau_tiktok = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Cookie": chuoi_cookie_tiktok_chuan_hoa,
    "Content-Type": "application/json",
    "Referer": "https://www.tiktok.com/messages",
    "Origin": "https://www.tiktok.com"
}

kich_ban_phan_hoi_ai = """
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
                        "text": f"{kich_ban_phan_hoi_ai}\n\nTin nhắn người hâm mộ gửi: '{noi_dung_tin_nhan_den}'"
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
    except Exception as loi_gemini:
        print(f"[NGOẠI LỆ GEMINI API] {loi_gemini}")
    return "Cảm ơn bạn đã nhắn tin cho mình nhé!"

def ham_tim_danh_sach_cuoc_tro_truyen(du_lieu_json):
    if not isinstance(du_lieu_json, dict):
        return []
    if "conversations" in du_lieu_json and isinstance(du_lieu_json["conversations"], list):
        return du_lieu_json["conversations"]
    if "user_conversations" in du_lieu_json and isinstance(du_lieu_json["user_conversations"], list):
        return du_lieu_json["user_conversations"]
    if "data" in du_lieu_json and isinstance(du_lieu_json["data"], dict):
        du_lieu_noi = du_lieu_json["data"]
        for khoa in ["conversations", "user_conversations", "conversation_list", "list"]:
            if khoa in du_lieu_noi and isinstance(du_lieu_noi[khoa], list):
                return du_lieu_noi[khoa]
    for khoa, gia_tri in du_lieu_json.items():
        if isinstance(gia_tri, list) and len(gia_tri) > 0 and isinstance(gia_tri[0], dict):
            if "conversation_id" in gia_tri[0] or "last_message" in gia_tri[0]:
                return gia_tri
    return []

def ham_kiem_tra_phai_nhom_chat(cuoc_tro_truyen):
    loai_cuoc_tro_truyen = cuoc_tro_truyen.get("conversation_type") or cuoc_tro_truyen.get("type")
    la_nhom = cuoc_tro_truyen.get("is_group", False)
    danh_sach_thanh_vien = cuoc_tro_truyen.get("participants") or cuoc_tro_truyen.get("members")
    if loai_cuoc_tro_truyen == 2 or la_nhom is True:
        return True
    if isinstance(danh_sach_thanh_vien, list) and len(danh_sach_thanh_vien) > 2:
        return True
    return False

def ham_giai_ma_noi_dung_tin_nhan(doi_tuong_tin_nhan):
    if not doi_tuong_tin_nhan:
        return ""
    noi_dung_tho = doi_tuong_tin_nhan.get("content")
    if not noi_dung_tho:
        return ""
    if isinstance(noi_dung_tho, dict):
        return noi_dung_tho.get("text", "")
    if isinstance(noi_dung_tho, str):
        try:
            noi_dung_giai_ma = json.loads(noi_dung_tho)
            if isinstance(noi_dung_giai_ma, dict):
                return noi_dung_giai_ma.get("text", "")
        except Exception:
            return noi_dung_tho
    return str(noi_dung_tho)

def ham_lay_thoi_gian_tao_tin_nhan(tin_nhan):
    thoi_gian = tin_nhan.get("create_time") or tin_nhan.get("created_time") or tin_nhan.get("create_time_ms") or 0
    if isinstance(thoi_gian, (int, float)):
        if thoi_gian > 10000000000:
            thoi_gian = thoi_gian / 1000.0
        return float(thoi_gian)
    return 0.0

def ham_lay_danh_sach_tin_nhan_tiktok():
    duong_dan_danh_sach_chat = "https://www.tiktok.com/api/im/chat/list/?count=10"
    try:
        phan_hoi_tiktok = requests.get(duong_dan_danh_sach_chat, headers=tieu_de_gui_yeu_cau_tiktok, timeout=10)
        if phan_hoi_tiktok.status_code == 200:
            du_lieu_json = phan_hoi_tiktok.json()
            if "status_code" in du_lieu_json and du_lieu_json["status_code"] != 0:
                print(f"[CẢNH BÁO COOKIE SAI HOẶC HẾT HẠN] TikTok báo lỗi: {du_lieu_json.get('status_msg')}")
            return du_lieu_json
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
        phan_hoi_gui = requests.post(duong_dan_gui_tin_nhan, headers=tieu_de_gui_yeu_cau_tiktok, data=json.dumps(du_lieu_gui_tin), timeout=10)
        print(f"[GỬI TIN NHẮN TRẢ LỜI] Trạng thái: {phan_hoi_gui.status_code} - Kết quả: {phan_hoi_gui.text[:100]}")
    except Exception as loi_gui_tin:
        print(f"[LỖI GỬI TIN NHẮN] {loi_gui_tin}")

def ham_vong_lap_xu_ly_tin_nhan_chay_ngam():
    danh_sach_id_tin_nhan_da_xu_ly = set()
    moc_thoi_gian_15_phut_truoc = time.time() - (15 * 60)
    print(f"[BOT KHỞI CHẠY BẮT TIN NHẮN TẬP TRUNG] Đang lắng nghe...")
    
    while True:
        try:
            du_lieu_hop_thu = ham_lay_danh_sach_tin_nhan_tiktok()
            if du_lieu_hop_thu:
                danh_sach_cuoc_tro_truyen = ham_tim_danh_sach_cuoc_tro_truyen(du_lieu_hop_thu)
                print(f"[SỐ CUỘC TRÒ TRUYỆN TÌM THẤY]: {len(danh_sach_cuoc_tro_truyen)}")
                
                for cuoc_tro_truyen in danh_sach_cuoc_tro_truyen:
                    if ham_kiem_tra_phai_nhom_chat(cuoc_tro_truyen):
                        continue
                        
                    id_cuoc_tro_truyen = cuoc_tro_truyen.get("conversation_id")
                    tin_nhan_gan_nhat = cuoc_tro_truyen.get("last_message", {})
                    id_tin_nhan = tin_nhan_gan_nhat.get("id") or tin_nhan_gan_nhat.get("server_message_id")
                    
                    thoi_gian_tao_tin = ham_lay_thoi_gian_tao_tin_nhan(tin_nhan_gan_nhat)
                    
                    if thoi_gian_tao_tin > 0 and thoi_gian_tao_tin < moc_thoi_gian_15_phut_truoc:
                        if id_tin_nhan:
                            danh_sach_id_tin_nhan_da_xu_ly.add(id_tin_nhan)
                        continue
                        
                    noi_dung_chuan = ham_giai_ma_noi_dung_tin_nhan(tin_nhan_gan_nhat)
                    la_tin_nhan_do_minh_gui = tin_nhan_gan_nhat.get("from_user_id") == cuoc_tro_truyen.get("user_id")
                    
                    if id_tin_nhan and id_tin_nhan not in danh_sach_id_tin_nhan_da_xu_ly:
                        danh_sach_id_tin_nhan_da_xu_ly.add(id_tin_nhan)
                        if noi_dung_chuan and not la_tin_nhan_do_minh_gui:
                            print(f"[PHÁT HIỆN TIN NHẮN MỚI CÁ NHÂN] ID: {id_tin_nhan} - Nội dung: '{noi_dung_chuan}'")
                            cau_tra_loi_ai = ham_tao_cau_tra_loi_tu_gemini(noi_dung_chuan)
                            print(f"[GEMINI TRẢ LỜI]: '{cau_tra_loi_ai}'")
                            ham_gui_tin_nhan_tiktok(id_cuoc_tro_truyen, cau_tra_loi_ai)
        except Exception as loi_vong_lap:
            print(f"[CẢNH BÁO VÒNG LẶP NGUYÊN NHÂN LỖI]: {loi_vong_lap}")
            
        time.sleep(5)

@ung_dung_flask.route('/')
def ham_kiem_tra_trang_thai_may_chu():
    return "TikTok Gemini Auto Responder Server - Active 24/7", 200

luong_chay_ngam = threading.Thread(target=ham_vong_lap_xu_ly_tin_nhan_chay_ngam, daemon=True)
luong_chay_ngam.start()

if __name__ == '__main__':
    cong_may_chu = int(os.environ.get("PORT", 5000))
    ung_dung_flask.run(host='0.0.0.0', port=cong_may_chu)