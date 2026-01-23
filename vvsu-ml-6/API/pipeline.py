"""
Модуль предобработки данных для вакансий
Точно воспроизводит pipeline из ноутбука
"""

import re
import ast
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Union
import joblib
from gensim.models import Word2Vec
import nltk
from nltk.corpus import stopwords
from pymorphy3 import MorphAnalyzer

class VacancyPreprocessor:
    """Предобработчик вакансий - точная копия из ноутбука"""
    
    def __init__(self, models_dir: str = "models"):
        self.models_dir = models_dir
        self.models = {}
        self.initialized = False
        
        # Инициализация NLP компонентов
        self.morph = None
        self.RUSSIAN_STOPWORDS = None
        self.TOKEN_RE = re.compile(r"[А-Яа-яA-Za-z]+", flags=re.U)
        
        # Храним информацию о признаках
        self.feature_info = {
            'mlb_schedule_classes': None,
            'mlb_working_hours_classes': None,
            'mlb_work_format_classes': None,
            'pca_desc_components': None,
            'pca_name_components': None,
        }
    
    def initialize(self):
        """Инициализация всех моделей"""
        try:
            print("Initializing preprocessor...")
            
            # Загрузка NLTK stopwords
            try:
                nltk.data.find('corpora/stopwords')
            except LookupError:
                nltk.download('stopwords', quiet=True)
            
            # Инициализация NLP компонентов
            self.morph = MorphAnalyzer()
            self.RUSSIAN_STOPWORDS = set(stopwords.words("russian"))
            
            # Загрузка моделей
            self._load_models()
            
            # Собираем информацию о признаках
            self._collect_feature_info()
            
            self.initialized = True
            print("Preprocessor initialized successfully")
            
        except Exception as e:
            print(f"Error initializing preprocessor: {e}")
            raise
    
    def _load_models(self):
        """Загрузка всех сохраненных моделей"""
        try:
            print("Loading Word2Vec models...")
            self.models['w2v_desc'] = Word2Vec.load(f"{self.models_dir}/w2v_desc_model.model")
            self.models['w2v_name'] = Word2Vec.load(f"{self.models_dir}/w2v_name_model.model")
            
            print("Loading PCA models...")
            self.models['pca_desc'] = joblib.load(f"{self.models_dir}/pca_desc.pkl")
            self.models['pca_name'] = joblib.load(f"{self.models_dir}/pca_name.pkl")
            
            print("Loading MLB models...")
            self.models['mlb_schedule'] = joblib.load(f"{self.models_dir}/mlb_schedule.pkl")
            self.models['mlb_working_hours'] = joblib.load(f"{self.models_dir}/mlb_working_hours.pkl")
            self.models['mlb_work_format'] = joblib.load(f"{self.models_dir}/mlb_work_format.pkl")
            
            print("Loading prediction model...")
            self.models['predict_model'] = joblib.load(f"{self.models_dir}/predict_model.joblib")
            
            print("Loading preprocessor...")
            self.models['preprocessor'] = joblib.load(f"{self.models_dir}/preprocessor.pkl")
            
            print(f"Loaded {len(self.models)} models successfully")
            
        except Exception as e:
            print(f"Error loading models: {e}")
            raise
    
    def _collect_feature_info(self):
        """Сбор информации о признаках"""
        try:
            self.feature_info['mlb_schedule_classes'] = len(self.models['mlb_schedule'].classes_)
            self.feature_info['mlb_working_hours_classes'] = len(self.models['mlb_working_hours'].classes_)
            self.feature_info['mlb_work_format_classes'] = len(self.models['mlb_work_format'].classes_)
            self.feature_info['pca_desc_components'] = self.models['pca_desc'].n_components_
            self.feature_info['pca_name_components'] = self.models['pca_name'].n_components_
            
            print("Feature information:")
            print(f"  MLB Schedule classes: {self.feature_info['mlb_schedule_classes']}")
            print(f"  MLB Working Hours classes: {self.feature_info['mlb_working_hours_classes']}")
            print(f"  MLB Work Format classes: {self.feature_info['mlb_work_format_classes']}")
            print(f"  PCA Desc components: {self.feature_info['pca_desc_components']}")
            print(f"  PCA Name components: {self.feature_info['pca_name_components']}")
            
        except Exception as e:
            print(f"Warning: Could not collect feature info: {e}")
    
    def preprocess_text(self, text: str) -> List[str]:
        """Предобработка текста - точная копия из ноутбука"""
        if not isinstance(text, str):
            text = "" if text is None else str(text)

        text = text.lower()
        tokens = self.TOKEN_RE.findall(text)

        lemmas = []
        for token in tokens:
            # Отсекаем короткий мусор
            if len(token) <= 2:
                continue

            # Русские и латинские слова отдельно
            if re.match(r"[а-я]", token):
                # Русское слово: нормальная форма через pymorphy3
                if token in self.RUSSIAN_STOPWORDS:
                    continue
                parsed = self.morph.parse(token)[0]
                lemma = parsed.normal_form
                if lemma in self.RUSSIAN_STOPWORDS:
                    continue
            else:
                # Латинское/английское слово — оставляем как есть
                lemma = token

            lemmas.append(lemma)

        return lemmas
    
    def document_vector(self, tokens: List[str], model_type: str = 'desc') -> np.ndarray:
        """Векторизация документа - точная копия из ноутбука"""
        model = self.models[f'w2v_{model_type}']
        vectors = [model.wv[token] for token in tokens if token in model.wv]

        if not vectors:
            return np.zeros(model.vector_size, dtype="float32")

        return np.mean(vectors, axis=0)
    
    def extract_professional_roles_id(self, roles_str: str) -> int:
        """Извлечение ID профессиональных ролей - точная копия из ноутбука"""
        if not roles_str or roles_str == '[]':
            return 0
        
        try:
            pattern = re.compile(r'\d+')
            rid = pattern.search(roles_str)
            if rid:
                return int(rid.group())
        except:
            pass
        
        return 0
    
    def clean_text_fields(self, text: str, field_type: str = 'skills') -> str:
        """Очистка текстовых полей - точная копия из ноутбука"""
        if not text:
            if field_type == 'skills':
                return "unknown"
            else:
                return ""
        
        # Извлекаем русские слова
        words = re.findall(r'[а-яА-Яё]+', text)
        
        if field_type == 'skills':
            return ','.join(words) if words else "unknown"
        else:
            return ' '.join(words) if words else ""
    
    def safe_parse_list(self, x: str) -> List[str]:
        """Безопасный парсинг строк-списков - точная копия из ноутбука"""
        if pd.isna(x) or x == '[]' or x == '':
            return []
        
        try:
            return ast.literal_eval(x)
        except (ValueError, SyntaxError):
            try:
                clean_str = x.replace("'", '"')
                return json.loads(clean_str)
            except:
                return [str(x)]
    
    def flesch_index_ru(self, text: str) -> int:
        """Индекс удобочитаемости Флеша - точная копия из ноутбука"""
        if pd.isna(text) or str(text).strip() == " ":
            return 0

        text = str(text)

        # количество предложений
        sentences = re.split(r'[.!?]+', str(text).strip())
        sentences = [s for s in sentences if s.strip()]
        count_sent = len(sentences)

        # количество слов
        count_words = len(text.split(" "))

        # кол-во слоги
        syllables = 0
        vowels = 'аеёиоуыэюяАЕЁИОУЫЭЮЯ'
        for word in re.findall(r'\b\w+\b', text):
            syl_count = sum(1 for char in word.lower() if char in vowels)
            syllables += max(1, syl_count)

        if count_sent == 0 or count_words == 0:
            return 0

        avg_sentence_len = count_words / count_sent
        avg_syllables_per_word = syllables / count_words

        flash_score = 206.835 - 1.3 * avg_sentence_len - 60.1 * avg_syllables_per_word
        return np.clip(int(round(flash_score, 0)), 0, 100)
    
    def prepare_features_dataframe(self, vacancy_data: Dict[str, Any]) -> pd.DataFrame:
        """
        Подготовка DataFrame с признаками в точности как в ноутбуке
        
        Возвращает DataFrame с теми же колонками, что и df_before в ноутбуке
        """
        if not self.initialized:
            self.initialize()
        
        # Создаем DataFrame с одной строкой
        df = pd.DataFrame([vacancy_data])
        
        # 1. Обработка даты (если есть published_at)
        if 'published_at' in df.columns:
            df["published_at"] = pd.to_datetime(df["published_at"])
            df["day"] = df["published_at"].dt.day
            df["month"] = df["published_at"].dt.month
            df["year"] = df["published_at"].dt.year
            df = df.drop(["published_at"], axis=1)
        
        # 2. Обработка professional_roles_id
        df['professional_roles_id'] = df['professional_roles'].apply(self.extract_professional_roles_id)
        
        # 3. Очистка текстовых полей
        df['professional_roles'] = df['professional_roles'].apply(
            lambda x: self.clean_text_fields(x, 'roles')
        )
        df['key_skills'] = df['key_skills'].apply(
            lambda x: self.clean_text_fields(x, 'skills')
        )
        df['key_skills'] = df['key_skills'].str.strip()
        df['key_skills'] = df['key_skills'].replace('', "unknown")
        
        # 4. Парсинг списковых полей
        df['schedule_list'] = df['schedule'].apply(self.safe_parse_list)
        df['working_hours_list'] = df['working_hours'].apply(self.safe_parse_list)
        df['work_format_list'] = df['work_format'].apply(self.safe_parse_list)
        
        # 5. Создание новых признаков (как в ноутбуке)
        df["salary_status"] = ~(df["salary_start"].isna() | (df["salary_start"] == 0))
        df["description_length"] = df["description"].apply(len)
        df["employer_popularity"] = 1  # Для одной вакансии всегда 1
        df["is_premium_employer"] = df["premium_status"] & df["employer_trusted"]
        df["index_flash"] = df["description"].apply(self.flesch_index_ru)
        df["key_skills_count"] = df['key_skills'].apply(
            lambda x: len(x.split(",")) if x != "unknown" else 0
        )
        
        # 6. Векторизация текстов
        desc_tokens = self.preprocess_text(df["description"].iloc[0])
        name_tokens = self.preprocess_text(df["name"].iloc[0])
        
        desc_vector = self.document_vector(desc_tokens, 'desc')
        name_vector = self.document_vector(name_tokens, 'name')
        
        # 7. Применение PCA
        desc_pca = self.models['pca_desc'].transform([desc_vector])[0]
        name_pca = self.models['pca_name'].transform([name_vector])[0]
        
        # 8. MultiLabelBinarizer
        schedule_encoded = self.models['mlb_schedule'].transform(df['schedule_list'])[0]
        wh_encoded = self.models['mlb_working_hours'].transform(df['working_hours_list'])[0]
        wf_encoded = self.models['mlb_work_format'].transform(df['work_format_list'])[0]
        
        # 9. Создаем DataFrame с MLB признаками
        schedule_df = pd.DataFrame(
            [schedule_encoded],
            columns=[f'schedule_{i}' for i in range(len(schedule_encoded))],
            index=df.index
        )
        
        wh_df = pd.DataFrame(
            [wh_encoded],
            columns=[f'working_hours_{i}' for i in range(len(wh_encoded))],
            index=df.index
        )
        
        wf_df = pd.DataFrame(
            [wf_encoded],
            columns=[f'work_format_{i}' for i in range(len(wf_encoded))],
            index=df.index
        )
        
        # 10. Создаем DataFrame с PCA признаками
        desc_pca_df = pd.DataFrame(
            [desc_pca],
            columns=[f'desc_pca_{i}' for i in range(len(desc_pca))],
            index=df.index
        )
        
        name_pca_df = pd.DataFrame(
            [name_pca],
            columns=[f'name_pca_{i}' for i in range(len(name_pca))],
            index=df.index
        )
        
        # 11. Создаем DataFrame с оригинальными признаками (как df_orig_edit в ноутбуке)
        orig_columns = [
            'salary_start', 'salary_to', 'currency', 'salary_mode',
            'experience', 'employment', 'professional_roles_id', 'type',
            'employer_trusted', 'premium_status', 'day', 'month', 'year',
            'salary_status', 'description_length', 'employer_popularity',
            'is_premium_employer', 'index_flash', 'key_skills_count'
        ]
        
        # Проверяем, что все колонки есть
        missing_cols = [col for col in orig_columns if col not in df.columns]
        if missing_cols:
            print(f"Warning: Missing columns in input: {missing_cols}")
            # Добавляем недостающие колонки с NaN
            for col in missing_cols:
                df[col] = None
        
        df_orig = df[orig_columns].copy()
        
        # 12. Объединяем все DataFrame (как df_before в ноутбуке)
        df_before = pd.concat([schedule_df, wh_df, wf_df, 
                             desc_pca_df, name_pca_df, df_orig], axis=1)
        
        return df_before
    
    def prepare_features(self, vacancy_data: Dict[str, Any]) -> np.ndarray:
        """
        Подготовка признаков для модели
        
        Возвращает массив признаков, готовый для подачи в модель
        """
        try:
            # 1. Получаем DataFrame с признаками
            df_features = self.prepare_features_dataframe(vacancy_data)
            
            print(f"Features DataFrame shape: {df_features.shape}")
            print(f"Columns count: {len(df_features.columns)}")
            
            # 2. Применяем предобработчик (ColumnTransformer)
            features_transformed = self.models['preprocessor'].transform(df_features)
            
            print(f"Transformed features shape: {features_transformed.shape}")
            
            return features_transformed[0]  # Возвращаем первый (и единственный) вектор
            
        except Exception as e:
            print(f"Error in prepare_features: {e}")
            print(f"DataFrame columns: {list(df_features.columns) if 'df_features' in locals() else 'N/A'}")
            raise
    
    def predict_cluster(self, vacancy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Предсказание кластера вакансии"""
        try:
            # Подготавливаем признаки
            features = self.prepare_features(vacancy_data)
            
            # Проверяем размерность
            if len(features.shape) == 1:
                features = features.reshape(1, -1)
            
            print(f"Features for prediction shape: {features.shape}")
            
            # Предсказание кластера
            prediction = self.models['predict_model'].predict(features)[0]
            
            # Вероятности (если доступно)
            if hasattr(self.models['predict_model'], 'predict_proba'):
                probabilities = self.models['predict_model'].predict_proba(features)[0]
                confidence = float(max(probabilities))
            else:
                confidence = 1.0
            
            return {
                "success": True,
                "cluster": int(prediction),
                "confidence": confidence,
                "features_count": features.shape[1] if len(features.shape) > 1 else len(features)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "cluster": None,
                "confidence": 0.0
            }

# Глобальный экземпляр предобработчика
preprocessor = VacancyPreprocessor()