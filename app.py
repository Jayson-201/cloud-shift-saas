import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# 初始化 OpenAI (記得在 Render 後台設定環境變數)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 模擬目前的員工資料庫 (用於 Demo 5人限制)
employee_db = ["小王", "小李", "小張", "小陳", "小林"]

# --- 記得把原本的 employee_db 改成這樣，方便處理刪除 ---
employee_db = ["小王", "小李", "小張", "小陳", "小林"]

# [新增] 刪除員工路由
@app.route("/delete_employee/<name>", methods=["POST"])
def delete_employee(name):
    if name in employee_db:
        employee_db.remove(name)
        return jsonify({"status": "success", "message": f"已刪除員工：{name}"})
    return jsonify({"status": "error", "message": "找不到該員工"})

# [新增] 員工手機打卡前台路由
@app.route("/clockin")
def clockin_page():
    # 這個頁面是給員工用手機看的
    return render_template("clockin.html", employees=employee_db)

# [新增] 接收打卡資料路由
@app.route("/api/do_clockin", methods=["POST"])
def do_clockin():
    emp_name = request.form.get("name")
    lat = request.form.get("lat")
    lng = request.form.get("lng")
    # 這裡可以把打卡時間跟座標存進資料庫，目前先回傳成功
    return jsonify({"status": "success", "message": f"{emp_name} 打卡成功！\n座標: {lat}, {lng}"})

@app.route("/", methods=["GET", "POST"])
def home():
    # 這是你個人化後的 website_main，作為 Landing Page
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    # SaaS 系統後台
    return render_template("dashboard.html", employees=employee_db)

@app.route("/add_employee", methods=["POST"])
def add_employee():
    # 【期末 Demo 亮點】展示 Freemium 商業模式的限制與升級提示
    if len(employee_db) >= 5:
        return jsonify({
            "status": "upgrade_needed",
            "message": "您目前使用的是免費版（限5人），升級標準版即可解鎖無上限排班與一鍵算薪功能！"
        })
    else:
        new_name = request.form.get("name")
        employee_db.append(new_name)
        return jsonify({"status": "success", "message": "新增成功"})

@app.route("/generate_schedule", methods=["POST"])
def generate_schedule():
    # 【Lab 作業整合】OpenAI 應用一：AI 智慧排班建議
    prompt = request.form.get("prompt")
    system_prompt = "你是一個排班小幫手。請根據使用者的需求，生出一份簡單的本週排班表。"
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    return jsonify({"schedule": response.choices[0].message.content})

# 注意：OpenAI 應用二 (圖片生成) 可另外寫一個 route 呼叫 client.images.generate 用於產生店鋪 LOGO

if __name__ == "__main__":
    app.run(debug=True)
