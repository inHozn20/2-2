import os
from flask import Flask, render_template, request, redirect
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Supabase 연동 설정
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route("/")
def index():
    # DB에서 방명록 목록 가져오기 (최신순)
    response = supabase.table("guestbook").select("*").order("id", desc=True).execute()
    posts = response.data
    return render_template("index.html", posts=posts)

@app.route("/add", methods=["POST"])
def add():
    name = request.form.get("name")
    message = request.form.get("message")
    
    # DB에 데이터 저장
    supabase.table("guestbook").insert({"name": name, "message": message}).execute()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)