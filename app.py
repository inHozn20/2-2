import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-key")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 1. 로그인
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name')
        student_id = request.form.get('student_id')
        
        res = supabase.table('users').select('*').eq('name', name).eq('student_id', student_id).execute()
        if res.data:
            user = res.data[0]
            session['user'] = user
            return redirect(url_for('shop'))
        else:
            flash("이름 또는 학번(비밀번호)이 올바르지 않습니다.")
            
    return render_template('index.html', page='login')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# 2. 상점 메인 페이지
@app.route('/')
@app.route('/shop')
def shop():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_res = supabase.table('users').select('*').eq('student_id', session['user']['student_id']).execute()
    if user_res.data:
        session['user'] = user_res.data[0]

    products = supabase.table('products').select('*').order('id').execute().data
    return render_template('index.html', page='shop', products=products)

# 3. 상품 구매
@app.route('/buy/<int:product_id>', methods=['POST'])
def buy(product_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user']['student_id']
    user = supabase.table('users').select('*').eq('student_id', user_id).execute().data[0]
    product = supabase.table('products').select('*').eq('id', product_id).execute().data[0]

    if product['stock'] <= 0:
        flash("재고가 부족합니다.")
    elif user['points'] < product['price']:
        flash("포인트가 부족합니다.")
    else:
        new_points = user['points'] - product['price']
        new_stock = product['stock'] - 1
        
        supabase.table('users').update({'points': new_points}).eq('student_id', user_id).execute()
        supabase.table('products').update({'stock': new_stock}).eq('id', product_id).execute()
        supabase.table('purchases').insert({'student_id': user_id, 'product_id': product_id}).execute()
        flash(f"{product['title']} 구매가 완료되었습니다!")

    return redirect(url_for('shop'))

# 4. 관리자 페이지 (포인트, 상품, 구매 내역 관리)
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user' not in session or not session['user'].get('is_admin'):
        flash("관리자 권한이 필요합니다.")
        return redirect(url_for('shop'))

    students = supabase.table('users').select('*').eq('is_admin', False).order('student_id').execute().data
    products = supabase.table('products').select('*').order('id').execute().data
    
    # 학생들의 쿠폰 구매 내역 조회 (유저 및 상품 정보 포함)
    purchases_res = supabase.table('purchases').select('id, created_at, users(name, student_id), products(title, price)').order('created_at', desc=True).execute()
    purchases = purchases_res.data if purchases_res.data else []

    return render_template('index.html', page='admin', students=students, products=products, purchases=purchases)

# 4-1. 상품 추가
@app.route('/admin/add_product', methods=['POST'])
def add_product():
    if 'user' not in session or not session['user'].get('is_admin'):
        return redirect(url_for('shop'))
    
    title = request.form.get('title')
    price = int(request.form.get('price', 0))
    stock = int(request.form.get('stock', 0))
    
    supabase.table('products').insert({'title': title, 'price': price, 'stock': stock}).execute()
    flash("상품이 추가되었습니다.")
    return redirect(url_for('admin'))

# 4-2. 상품 삭제
@app.route('/admin/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'user' not in session or not session['user'].get('is_admin'):
        return redirect(url_for('shop'))
        
    supabase.table('products').delete().eq('id', product_id).execute()
    flash("상품이 삭제되었습니다.")
    return redirect(url_for('admin'))

# 4-3. 공부시간 기반 포인트 지급
@app.route('/admin/add_points', methods=['POST'])
def add_points():
    if 'user' not in session or not session['user'].get('is_admin'):
        return redirect(url_for('shop'))
    
    student_id = request.form.get('student_id')
    study_minutes = int(request.form.get('study_minutes', 0))
    
    added_points = (study_minutes // 10) * 2
    
    student = supabase.table('users').select('*').eq('student_id', student_id).execute().data[0]
    new_points = student['points'] + added_points
    
    supabase.table('users').update({'points': new_points}).eq('student_id', student_id).execute()
    flash(f"{student['name']} 학생에게 {added_points}p가 지급되었습니다. (공부시간: {study_minutes}분)")
    return redirect(url_for('admin'))

# 5. 펜 필기 화이트보드 낙서장
@app.route('/doodle', methods=['GET', 'POST'])
def doodle():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        image_data = request.form.get('image_data')
        if image_data:
            supabase.table('board').insert({
                'author_name': session['user']['name'],
                'image_data': image_data
            }).execute()
            flash("화이트보드 그림이 공유되었습니다!")
            return redirect(url_for('doodle'))

    posts = supabase.table('board').select('*').order('created_at', desc=True).execute().data
    return render_template('index.html', page='doodle', posts=posts)