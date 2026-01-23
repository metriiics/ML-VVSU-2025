from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
import uvicorn
from datetime import datetime
import re
import json

from pipeline import preprocessor

# Модели Pydantic для валидации
class VacancyRequest(BaseModel):
    """Модель запроса вакансии - включает все поля из ноутбука"""
    name: str = Field(..., min_length=1, max_length=500, description="Название вакансии")
    description: str = Field(..., min_length=10, description="Описание вакансии")
    
    # Зарплата
    salary_start: Optional[float] = Field(None, ge=0, description="Минимальная зарплата")
    salary_to: Optional[float] = Field(None, ge=0, description="Максимальная зарплата")
    currency: Optional[str] = Field("RUR", max_length=10, description="Валюта зарплаты")
    salary_mode: Optional[str] = Field("За месяц", max_length=50, description="Период оплаты")
    
    # Опыт и занятость
    experience: Optional[str] = Field("Нет опыта", max_length=100, description="Требуемый опыт")
    employment: Optional[str] = Field("Полная занятость", max_length=100, description="Тип занятости")
    
    # График работы
    schedule: Optional[str] = Field('["5/2"]', description="График работы (JSON string)")
    working_hours: Optional[str] = Field('["8 часов"]', description="Рабочее время (JSON string)")
    work_format: Optional[str] = Field('["На месте работодателя"]', description="Формат работы (JSON string)")
    
    # Профессиональные роли
    professional_roles: Optional[str] = Field('[]', description="Профессиональные роли (JSON string)")
    
    # Тип вакансии
    type: Optional[str] = Field("Открытая", max_length=50, description="Тип вакансии")
    
    # Статус работодателя
    employer_trusted: Optional[int] = Field(0, ge=0, le=1, description="Проверенный работодатель")
    premium_status: Optional[int] = Field(0, ge=0, le=1, description="Премиум статус")
    
    # Ключевые навыки
    key_skills: Optional[str] = Field('[]', description="Ключевые навыки (JSON string)")
    
    # Дата публикации (может быть как published_at, так как отдельные поля)
    published_at: Optional[str] = Field(None, description="Дата публикации в формате ISO")
    day: Optional[int] = Field(None, ge=1, le=31, description="День публикации")
    month: Optional[int] = Field(None, ge=1, le=12, description="Месяц публикации")
    year: Optional[int] = Field(None, ge=2000, le=2100, description="Год публикации")
    
    # Опциональные поля из ноутбука
    id: Optional[str] = Field(None, description="ID вакансии")
    url: Optional[str] = Field(None, description="URL вакансии")
    employer_name: Optional[str] = Field(None, description="Название работодателя")
    city_vacancies: Optional[str] = Field(None, description="Город/число вакансий")
    
    @validator('schedule', 'working_hours', 'work_format', 'professional_roles', 'key_skills')
    def validate_json_string(cls, v):
        """Валидация JSON строк"""
        if v is None:
            return '[]'
        try:
            # Проверяем, что это валидный JSON
            json.loads(v)
            return v
        except json.JSONDecodeError:
            # Если не JSON, оборачиваем в JSON
            return json.dumps([v]) if v else '[]'
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Python разработчик",
                "description": "Разработка backend на Django и FastAPI. Оптимизация SQL запросов.",
                "salary_start": 150000.0,
                "salary_to": 250000.0,
                "currency": "RUR",
                "salary_mode": "За месяц",
                "experience": "От 1 года до 3 лет",
                "employment": "Полная занятость",
                "schedule": '["5/2"]',
                "working_hours": '["8 часов"]',
                "work_format": '["Гибрид"]',
                "professional_roles": '["Разработчик"]',
                "type": "Открытая",
                "employer_trusted": 1,
                "premium_status": 0,
                "key_skills": '["Python", "Django", "FastAPI", "PostgreSQL"]',
                "day": 15,
                "month": 1,
                "year": 2024
            }
        }

class ClusterResponse(BaseModel):
    """Модель ответа предсказания кластера"""
    success: bool
    cluster: Optional[int] = None
    confidence: Optional[float] = None
    error: Optional[str] = None
    processing_time_ms: Optional[float] = None
    features_count: Optional[int] = None
    message: Optional[str] = None

class HealthResponse(BaseModel):
    """Модель ответа проверки здоровья"""
    status: str
    models_loaded: bool
    timestamp: datetime
    api_version: str = "1.0.0"
    feature_info: Optional[Dict[str, Any]] = None

class FeaturesResponse(BaseModel):
    """Модель ответа с информацией о признаках"""
    success: bool
    features_count: Optional[int] = None
    feature_names: Optional[List[str]] = None
    features_shape: Optional[List[int]] = None
    error: Optional[str] = None

# Создание FastAPI приложения
app = FastAPI(
    title="Vacancies Clustering API",
    description="API для предсказания кластеров вакансий с использованием KNN модели. Точное воспроизведение pipeline из ноутбука.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация при запуске
@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске сервера"""
    try:
        preprocessor.initialize()
        print("✅ Preprocessor initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize preprocessor: {e}")
        print("⚠️  API будет работать в ограниченном режиме")

@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "message": "Vacancies Clustering API",
        "version": "1.0.0",
        "description": "API для предсказания кластера вакансии с использованием KNN модели",
        "models_loaded": preprocessor.initialized,
        "endpoints": {
            "health": "/health",
            "predict": "/predict",
            "features": "/features",
            "debug": "/debug",
            "docs": "/docs"
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Проверка состояния API"""
    feature_info = None
    if preprocessor.initialized and hasattr(preprocessor, 'feature_info'):
        feature_info = preprocessor.feature_info
    
    return HealthResponse(
        status="healthy" if preprocessor.initialized else "degraded",
        models_loaded=preprocessor.initialized,
        timestamp=datetime.now(),
        feature_info=feature_info
    )

@app.post("/predict", response_model=ClusterResponse)
async def predict_cluster(vacancy: VacancyRequest):
    """
    Предсказание кластера вакансии
    
    Принимает данные вакансии, выполняет полный pipeline предобработки
    как в ноутбуке и возвращает предсказанный кластер
    """
    import time
    
    start_time = time.time()
    
    try:
        if not preprocessor.initialized:
            raise HTTPException(
                status_code=503, 
                detail="Models not loaded. Please check /health endpoint."
            )
        
        # Преобразуем в словарь
        vacancy_dict = vacancy.dict(exclude_none=True)
        
        # Выполняем предсказание кластера
        result = preprocessor.predict_cluster(vacancy_dict)
        
        processing_time = (time.time() - start_time) * 1000
        
        if result["success"]:
            return ClusterResponse(
                success=True,
                cluster=result["cluster"],
                confidence=result["confidence"],
                processing_time_ms=round(processing_time, 2),
                features_count=result.get("features_count", 0),
                message="Prediction successful"
            )
        else:
            return ClusterResponse(
                success=False,
                error=result.get("error", "Unknown error"),
                processing_time_ms=round(processing_time, 2),
                message="Prediction failed"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        return ClusterResponse(
            success=False,
            error=str(e),
            processing_time_ms=round(processing_time, 2),
            message="Internal server error"
        )

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )