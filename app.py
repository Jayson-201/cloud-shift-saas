import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from datetime import datetime

app = Flask(__name__)
# 預防沒有設定環境變數時報錯，加上預備金鑰或空字串
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "mock-key"))

# 1. 基礎資料庫
employee_db = ["小王", "小李", "小張", "小陳", "小林"]
face_db = {}

# 2. 打卡紀錄儲存（昨晚沒串成功的核心）
clockin_records = [
    {"name": "小王", "time": "09:02", "shift": "早班", "status": "遲到"},
    {"name": "小張", "time": "14:00", "shift": "晚班", "status": "正常"},
    {"name": "小林", "time": "08:55", "shift": "早班", "status": "正常"}
]

# 3. 排班表持久化資料
schedule_data = {
    "早班": ["小王", "小張", "小林", "小林", "小陳", "小張", "小陳"],
    "晚班": ["小陳", "小李", "小王", "小張", "小王", "小王", "小李"]
}

# 4. 薪水試算頁面所需的「本月出勤統計數據」（2位正職、3位PT）
salary_summary = [
    {"name": "小王", "type": "正職", "base": 38000, "late": 2, "leave": 1, "hours": 0, "total": 38000, "note": "請假1天、遲到2次（正職不扣薪）"},
    {"name": "小李", "type": "正職", "base": 38000, "late": 0, "leave": 0, "hours": 0, "total": 38000, "note": "全勤"},
    {"name": "小張", "type": "PT", "base": "196/hr", "late": 1, "leave": 0, "hours": 88, "total": 17248, "note": "總計工時 88 小時，遲到1次"},
    {"name": "小陳", "type": "PT", "base": "196/hr", "late": 0, "leave": 2, "hours": 72, "total": 14112, "note": "請假2天，總計工時 72 小時"},
    {"name": "小林", "type": "PT", "base": "196/hr", "late": 3, "leave": 0, "hours": 95, "total": 18620, "note": "總計工時 95 小時，遲到3次"}
]

@app.route("/")
def home():
    return render_template("index.html")

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

@app.route("/save_schedule", methods=["POST"])
def save_schedule():
    global schedule_data
    schedule_data = request.json
    return jsonify({"status": "success"})

# 核心修正：唯一保留的打卡 API，自動抓取當前時間判定早晚班與遲到
@app.route("/api/do_clockin", methods=["POST"])
def do_clockin():
    # 支援前端傳送 JSON 或 FormData 兩種格式，提高容錯率
    if request.is_json:
        data = request.json
        emp_name = data.get("name")
    else:
        emp_name = request.form.get("name")
        
    if not emp_name:
        return jsonify({"status": "error", "message": "未選擇員工姓名"})

    now = datetime.now()
    time_str = now.strftime("%H:%M")
    hour = now.hour
    minute = now.minute

    # 自動時間與班別判定邏輯
    # 早班: 09:00~18:00，晚班: 14:00~22:00
    if 14 <= hour < 22:
        shift = "晚班"
        status = "遲到" if (hour == 14 and minute > 0) or hour > 14 else "正常"
    else:
        shift = "早班"
        status = "遲到" if (hour == 9 and minute > 0) or hour > 9 else "正常"

    new_record = {"name": emp_name, "time": time_str, "shift": shift, "status": status}
    clockin_records.insert(0, new_record) # 讓最新的打卡紀錄排在最上面

    return jsonify({
        "status": "success", 
        "message": f"🎉 {emp_name} 打卡成功！\n時間：{time_str} ({shift}・{status})"
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
