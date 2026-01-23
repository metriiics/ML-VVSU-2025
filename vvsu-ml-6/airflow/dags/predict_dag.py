from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

def get_vacancies_from_db():
    """Берет все вакансии из фиксированной БД"""
    import sqlite3
    
    db_path = '/opt/airflow/dags/data/vacancies_fixed.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем все поля которые есть в таблице
        cursor.execute("PRAGMA table_info(vacancies)")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]
        
        cursor.execute("SELECT * FROM vacancies")
        rows = cursor.fetchall()
        
        vacancies = []
        for row in rows:
            vacancy = {}
            for i, col_name in enumerate(column_names):
                vacancy[col_name] = row[i]
            vacancies.append(vacancy)
        
        conn.close()
        
        print(f"✅ Получено {len(vacancies)} вакансий из БД")
        return vacancies
        
    except Exception as e:
        return []

def make_predictions_from_db():
    """Делает предсказания используя ТОЛЬКО данные из БД"""
    import requests
    
    vacancies = get_vacancies_from_db()
    
    if not vacancies:
        return "No vacancies"
    
    results = []

    for idx, vacancy in enumerate(vacancies, 1):
        print(f"\n[{idx}/{len(vacancies)}] 📋 {vacancy.get('name', 'Без названия')}")
        
        required_fields = ['name', 'description']
        missing_fields = [f for f in required_fields if not vacancy.get(f)]
        
        if missing_fields:
            continue
        
        try:
            vacancy_data = {}
            
            vacancy_data['name'] = str(vacancy.get('name'))
            vacancy_data['description'] = str(vacancy.get('description'))
            
            if vacancy.get('salary_start') is not None:
                vacancy_data['salary_start'] = float(vacancy.get('salary_start'))
            if vacancy.get('salary_to') is not None:
                vacancy_data['salary_to'] = float(vacancy.get('salary_to'))
            if vacancy.get('currency'):
                vacancy_data['currency'] = str(vacancy.get('currency'))
            if vacancy.get('salary_mode'):
                vacancy_data['salary_mode'] = str(vacancy.get('salary_mode'))
            if vacancy.get('experience'):
                vacancy_data['experience'] = str(vacancy.get('experience'))
            if vacancy.get('employment'):
                vacancy_data['employment'] = str(vacancy.get('employment'))
            if vacancy.get('schedule'):
                vacancy_data['schedule'] = str(vacancy.get('schedule'))
            if vacancy.get('working_hours'):
                vacancy_data['working_hours'] = str(vacancy.get('working_hours'))
            if vacancy.get('work_format'):
                vacancy_data['work_format'] = str(vacancy.get('work_format'))
            if vacancy.get('professional_roles'):
                vacancy_data['professional_roles'] = str(vacancy.get('professional_roles'))
            if vacancy.get('type'):
                vacancy_data['type'] = str(vacancy.get('type'))
            if vacancy.get('employer_trusted') is not None:
                vacancy_data['employer_trusted'] = int(vacancy.get('employer_trusted'))
            if vacancy.get('premium_status') is not None:
                vacancy_data['premium_status'] = int(vacancy.get('premium_status'))
            if vacancy.get('key_skills'):
                vacancy_data['key_skills'] = str(vacancy.get('key_skills'))
            
            if vacancy.get('published_at'):
                vacancy_data['published_at'] = str(vacancy.get('published_at'))
            
            response = requests.post(
                "http://localhost:8000/predict",
                json=vacancy_data,
                headers={'Content-Type': 'application/json'},
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):   
                    results.append({
                        'vacancy_id': vacancy.get('id'),
                        'vacancy_name': vacancy.get('name'),
                        'cluster': result.get('cluster'),
                        'confidence': result.get('confidence'),
                        'success': True
                    })
                else:
                    results.append({
                        'vacancy_id': vacancy.get('id'),
                        'vacancy_name': vacancy.get('name'),
                        'success': False,
                        'error': result.get('error')
                    })
            else:
                results.append({
                    'vacancy_id': vacancy.get('id'),
                    'vacancy_name': vacancy.get('name'),
                    'success': False,
                    'error': f"HTTP {response.status_code}"
                })
                
        except requests.exceptions.ConnectionError:
            return "API connection failed"
        except Exception as e:
            results.append({
                'vacancy_id': vacancy.get('id'),
                'vacancy_name': vacancy.get('name'),
                'success': False,
                'error': str(e)
            })
    
    if results:
        successful = sum(1 for r in results if r.get('success'))
        total = len(results)

        
        if successful > 0:
            from collections import Counter
            clusters = Counter([r['cluster'] for r in results if r.get('success')])
            
            print(f"\n📈 Распределение по кластерам:")
            for cluster, count in clusters.most_common():
                percentage = (count / successful) * 100
                bar = '█' * int(percentage / 5)
                print(f"   Кластер {cluster}: {bar} {count} вакансий ({percentage:.1f}%)")
    else:
        print("Нет результатов")

    return f"Обработано: {len(results)}"

with DAG(
    'hh_predict_db',
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=['hh', 'prediction', 'db-only'],
) as dag:
    
    predict_task = PythonOperator(
        task_id='predict_from_db_only',
        python_callable=make_predictions_from_db,
    )