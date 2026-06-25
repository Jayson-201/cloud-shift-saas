import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# 初始化 OpenAI (需在 Render 環境變數中設定 OPENAI_API_KEY)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 模擬目前的員工資料庫 (List)
employee_db = ["小王", "小李", "小張", "小陳", "小林"]

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", employees=employee_db)

@app.route("/add_employee", methods=["POST"])
def add_employee():
    if len(employee_db) >= 5:
        return jsonify({
            "status": "upgrade_needed",
            "message": "您目前使用的是體驗版（限5人），升級標準版即可解鎖無上限排班與一鍵算薪功能！"
        })
    else:
        new_name = request.form.get("name")
        if new_name and new_name not in employee_db:
            employee_db.append(new_name)
        return jsonify({"status": "success", "message": "新增成功"})

# [重點功能] 刪除員工路由
@app.route("/delete_employee/<name>", methods=["POST"])
def delete_employee(name):
    if name in employee_db:
        employee_db.remove(name)
        return jsonify({"status": "success", "message": f"已成功將員工「{name}」刪除。"})
    return jsonify({"status": "error", "message": "找不到該員工，可能已被刪除。"})

@app.route("/clockin")
def clockin_page():
    return render_template("clockin.html", employees=employee_db)

@app.route("/api/do_clockin", methods=["POST"])
def do_clockin():
    emp_name = request.form.get("name")
    lat = request.form.get("lat")
    lng = request.form.get("lng")
    return jsonify({"status": "success", "message": f"✅ {emp_name} 打卡成功！\n經緯度: {lat}, {lng}"})

@app.route("/generate_schedule", methods=["POST"])
def generate_schedule():
    prompt = request.form.get("prompt")
    system_prompt = "你是一個排班調度顧問。請根據店長遇到的突發狀況（如請假、缺人），給出具體的調度建議與應對方案。"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
        )
        return jsonify({"schedule": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/generate_handover", methods=["POST"])
def generate_handover():
    prompt = request.form.get("prompt")
    system_prompt = """你是一個專業的店鋪營運助理。請將員工口語化的交接內容，
    整理成專業的交接日誌，並調整事情的先後順序（緊急優先）。
    請務必嚴格使用以下三個標籤進行分類條列：
    「⚠️ 待辦事項」、「🔧 設備報修」、「📝 營運紀錄」。"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
        )
        return jsonify({"handover_log": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
