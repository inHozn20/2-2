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
    
    # 내 정보 최신화
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
        
        # 구매 시 is_used 기본값은 False
        supabase.table('purchases').insert({
            'student_id': user_id, 
            'product_id': product_id,
            'is_used': False
        }).execute()
        
        flash(f"🎉 {product['title']} 구매가 완료되었습니다!")

    return redirect(url_for('shop'))

# 4. 공부시간 랭킹 페이지
@app.route('/ranking')
def ranking():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    rankings_res = supabase.table('users').select('student_id, name, total_study_minutes, points').eq('is_admin', False).order('total_study_minutes', desc=True).execute()
    rankings = rankings_res.data if rankings_res.data else []
    
    return render_template('index.html', page='ranking', rankings=rankings)

# 5. 관리자 페이지
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user' not in session or not session['user'].get('is_admin'):
        flash("관리자 권한이 필요합니다.")
        return redirect(url_for('shop'))

    students = supabase.table('users').select('*').eq('is_admin', False).order('student_id').execute().data
    products = supabase.table('products').select('*').order('id').execute().data
    
    # 구매 내역 (is_used 컬럼 포함 조회)
    purchases_res = supabase.table('purchases').select('id, created_at, is_used, users(name, student_id), products(title, price)').order('created_at', desc=True).execute()
    purchases = purchases_res.data if purchases_res.data else []

    return render_template('index.html', page='admin', students=students, products=products, purchases=purchases)

# 5-1. 쿠폰 사용/사용전 상태 토글
@app.route('/admin/toggle_used/<int:purchase_id>', methods=['POST'])
def toggle_used(purchase_id):
    if 'user' not in session or not session['user'].get('is_admin'):
        return redirect(url_for('shop'))
        
    # 현재 구매 상태 조회
    purchase = supabase.table('purchases').select('is_used').eq('id', purchase_id).execute().data[0]
    current_status = purchase.get('is_used', False)
    
    # 상태 반전 (True <-> False)
    supabase.table('purchases').update({'is_used': not current_status}).eq('id', purchase_id).execute()
    
    flash("쿠폰 사용 상태가 변경되었습니다.")
    return redirect(url_for('admin'))

# 5-2. 상품 추가
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

# 5-3. 상품 삭제
@app.route('/admin/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'user' not in session or not session['user'].get('is_admin'):
        return redirect(url_for('shop'))
        
    supabase.table('products').delete().eq('id', product_id).execute()
    flash("상품이 삭제되었습니다.")
    return redirect(url_for('admin'))

# 5-4. 공부시간 기반 포인트 추가
@app.route('/admin/add_points', methods=['POST'])
def add_points():
    if 'user' not in session or not session['user'].get('is_admin'):
        return redirect(url_for('shop'))
    
    student_id = request.form.get('student_id')
    hours = int(request.form.get('study_hours', 0))
    minutes = int(request.form.get('study_minutes', 0))
    
    total_new_minutes = (hours * 60) + minutes
    
    if total_new_minutes <= 0:
        flash("공부 시간을 입력해 주세요.")
        return redirect(url_for('admin'))

    added_points = (total_new_minutes // 10) * 2
    
    student = supabase.table('users').select('*').eq('student_id', student_id).execute().data[0]
    
    new_points = student['points'] + added_points
    accumulated_study = student.get('total_study_minutes', 0) + total_new_minutes
    
    supabase.table('users').update({
        'points': new_points,
        'total_study_minutes': accumulated_study
    }).eq('student_id', student_id).execute()
    
    time_str = f"{hours}시간 {minutes}분" if hours > 0 else f"{minutes}분"
    flash(f"👏 {student['name']} 학생에게 {added_points}P 지급 완료! (공부시간: {time_str})")
    return redirect(url_for('admin'))