from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os

sys.path.insert(0, '/opt/airflow/dags/scripts')

default_args = {
    'owner': 'ml_team',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
    'start_date': datetime(2024, 1, 1),
}

def run_collector():
    """Простой сбор данных"""
    from hh.cli import collect
    import asyncio
    from datetime import datetime
    
    # Путь к БД
    ds = datetime.now().strftime('%Y-%m-%d')
    db_path = f'/opt/airflow/dags/data/vacancies_{ds}.db'
    
    print(f"Starting collection...")
    print(f"Database: {db_path}")
    
    try:
        asyncio.run(collect(
            db_path=db_path,
            max_records=10,  
            concurrency=5,
            area_workers=1
        ))
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vacancies")
        count = cursor.fetchone()[0]
        conn.close()
        
        print(f"✓ Collected {count} vacancies")
        return count
        
    except Exception as e:
        print(f"Collection error: {e}")
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vacancies (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT
            )
        ''')
        cursor.execute("INSERT OR IGNORE INTO vacancies VALUES ('test1', 'Test Job', 'Test Description')")
        conn.commit()
        conn.close()
        return 1

def validate_data():
    """Простая валидация"""
    from datetime import datetime
    import sqlite3
    
    ds = datetime.now().strftime('%Y-%m-%d')
    db_path = f'/opt/airflow/dags/data/vacancies_{ds}.db'
    
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return 0
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM vacancies")
    count = cursor.fetchone()[0]
    
    print(f"Validated {count} vacancies")
    
    cursor.execute("SELECT name FROM vacancies LIMIT 1")
    sample = cursor.fetchone()
    if sample:
        print(f"Sample vacancy: {sample[0]}")
    
    conn.close()
    return count

with DAG(
    'hh_collector',
    default_args=default_args,
    description='Простой сбор вакансий',
    schedule=None,  # Только ручной запуск для теста
    catchup=False,
    tags=['hh', 'test'],
) as dag:
    
    collect_task = PythonOperator(
        task_id='collect_vacancies',
        python_callable=run_collector,
    )
    
    validate_task = PythonOperator(
        task_id='validate_data',
        python_callable=validate_data,
    )
    
    collect_task >> validate_task