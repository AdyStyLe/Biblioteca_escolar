import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'sua-chave-secreta-aqui'
    
    # PostgreSQL com Supabase
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:SUA_SENHA@db.rwwwtgeefkqqagqalfzz.supabase.co:5432/postgres'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
