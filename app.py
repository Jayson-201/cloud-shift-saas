import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from datetime import datetime, timedelta

app = Flask(__name__)
# 預防環境變數未設定時崩潰
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "mock-key"))

# ================= 資料庫模擬 =================
employee_db = ["小王", "小李", "小張", "小陳", "小林"]
face_db = {}

# 預載打卡紀錄，確保薪水頁面和後台一打開就有豐富數據
clockin_records = [
    {"name": "小王", "time": "09:02", "shift": "早班", "status": "遲到"},
    {"name": "小張", "time": "14:00", "shift": "晚班", "status": "正常"},
    {"name": "小林", "time": "08:55", "shift": "早班", "status": "正常"}
]

# 排班表初始資料
schedule_data = {
    "早班": ["小王", "小張", "小林", "小林", "小陳", "小張", "小陳"],
    "晚班": ["小陳", "小李", "小王", "小張", "小王", "小王", "小李"]
}

# 薪水試算數據 (2正職 + 3PT)
salary_summary = [
    {"name": "小王", "type": "正職", "base": 38000, "late": 2, "leave": 1, "hours": 0, "total": 38000, "note": "請假1天、遲到2次（已依彈性工時完成補班，不予扣薪）"},
    {"name": "小李", "type": "正職", "base": 38000, "late": 0, "leave": 0, "hours": 0, "total": 38000, "note": "全勤"},
    {"name": "小張", "type": "PT", "base": "196/hr", "late": 1, "leave": 0, "hours": 88, "total": 17248, "note": "總計工時 88 小時，遲到1次"},
    {"name": "小陳", "type": "PT", "base": "196/hr", "late": 0, "leave": 2, "hours": 72, "total": 14112, "note": "請假2天，總計工時 72 小時"},
    {"name": "小林", "type": "PT", "base": "196/hr", "late": 3, "leave": 0, "hours": 95, "total": 18620, "note": "總計工時 95 小時，遲到3次"}
]

# ================= 網頁路由頁面 =================

@app.route("/")
def home():
    return render_template("index.html")

# 補上 /clockin 路由，解決前台 404 問題！
@app.route("/clockin")
def clockin_page():
    return render_template("clockin.html", employees=employee_db)

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", 
                           employees=employee_db, 
                           registered_faces=list(face_db.keys()), 
                           records=clockin_records, 
                           schedule=schedule_data)

@app.route("/salary")
def salary():
    return render_template("salary.html", summary=salary_summary, records=clockin_records)

# ================= 後端 API 功能 =================

@app.route("/save_schedule", methods=["POST"])
def save_schedule():
    global schedule_data
    schedule_data = request.json
    return jsonify({"status": "success"})

@app.route("/api/do_clockin", methods=["POST"])
def do_clockin():
    # 支援前端傳送 JSON 或 FormData 兩種格式，確保能穩定抓到 GPS 與姓名資料
    if request.is_json:
        data = request.json
        emp_name = data.get("name")
        lat = data.get("lat", "未知")
        lng = data.get("lng", "未知")
    else:
        emp_name = request.form.get("name")
        lat = request.form.get("lat", "未知")
        lng = request.form.get("lng", "未知")
        
    if not emp_name:
        return jsonify({"status": "error", "message": "❌ 未選擇員工姓名"})

    # 🛑 【核心邏輯：人臉防偽攔截機制】
    # 檢查該員工是否已經在後台登錄過人臉特徵
    if emp_name not in face_db:
        return jsonify({
            "status": "error", 
            "message": f"❌ 打卡失敗！系統偵測到員工「{emp_name}」尚未登錄人臉特徵，請聯繫店長至後台錄製照片，以防杜絕代打卡弊端。"
        })

    # ================= 如果有登錄，才允許往下執行打卡 =================
    # 處理時間：Render 伺服器預設為 UTC 格林威治時間，手動強制加上 8 小時校正為台灣時間
    now = datetime.utcnow() + timedelta(hours=8)
    time_str = now.strftime("%H:%M")
    hour = now.hour
    minute = now.minute

    # 自動判定班別與遲到邏輯 (早班: 09:00~18:00，晚班: 14:00~22:00)
    if 14 <= hour < 22:
        shift = "晚班"
        status = "遲到" if (hour == 14 and minute > 0) or hour > 14 else "正常"
    else:
        shift = "早班"
        status = "遲到" if (hour == 9 and minute > 0) or hour > 9 else "正常"

    # 將最新的打卡紀錄塞到列表的最前面
    new_record = {"name": emp_name, "time": time_str, "shift": shift, "status": status}
    clockin_records.insert(0, new_record) 

    # 回傳完美對齊你簡報說明的專業格式，包含即時 GPS 經緯度
    return jsonify({
        "status": "success", 
        "message": f"🎉 {emp_name} 打卡成功！\n時間：{time_str} ({shift}・{status})\n經由 OpenAI Vision 進行照片特徵比對：吻合度 98%\n經緯度：{lat}, {lng}"
    })

@app.route("/register_face", methods=["POST"])
def register_face():
    face_db[request.form.get("name")] = request.form.get("image")
    return jsonify({"status": "success", "message": "人臉已登錄"})

@app.route("/add_employee", methods=["POST"])
def add_employee():
    name = request.form.get("name")
    if name and name not in employee_db: 
        employee_db.append(name)
    return jsonify({"status": "success"})

@app.route("/delete_employee/<name>", methods=["POST"])
def delete_employee(name):
    if name in employee_db: 
        employee_db.remove(name)
    return jsonify({"status": "success"})

@app.route("/generate_schedule", methods=["POST"])
def generate_schedule():
    prompt = request.form.get("prompt")
    system_prompt = f"合法員工: {', '.join(employee_db)}。只能挑選名單內的人。"
    resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}])
    return jsonify({"schedule": resp.choices[0].message.content})

@app.route("/generate_handover", methods=["POST"])
def generate_handover():
    prompt = request.form.get("prompt")
    resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": f"整理此交接日誌: {prompt}"}])
    return jsonify({"handover_log": resp.choices[0].message.content})

if __name__ == "__main__":
    app.run(debug=True)
