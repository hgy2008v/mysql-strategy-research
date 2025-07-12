from sqlalchemy import create_engine
import config

def get_engine():
    """获取SQLAlchemy数据库引擎"""
    url = f"mysql+pymysql://{config.MYSQL_USER}:{config.MYSQL_PASSWORD}@{config.MYSQL_HOST}:{config.MYSQL_PORT}/{config.MYSQL_DB}?charset=utf8mb4"
    return create_engine(url) 