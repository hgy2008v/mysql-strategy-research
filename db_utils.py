from sqlalchemy import create_engine
import pymysql
import pandas as pd
import config

def get_engine():
    """获取SQLAlchemy数据库引擎"""
    url = f"mysql+pymysql://{config.MYSQL_USER}:{config.MYSQL_PASSWORD}@{config.MYSQL_HOST}:{config.MYSQL_PORT}/{config.MYSQL_DB}?charset=utf8mb4"
    return create_engine(url)

def get_db_connection():
    """获取PyMySQL数据库连接"""
    try:
        connection = pymysql.connect(
            host=config.MYSQL_HOST,
            port=config.MYSQL_PORT,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DB,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None

def execute_query(query, params=None):
    """执行SQL查询并返回结果"""
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            return result
    except Exception as e:
        print(f"查询执行失败: {e}")
        return None
    finally:
        if conn:
            conn.close()

def execute_update(query, params=None):
    """执行SQL更新操作"""
    try:
        conn = get_db_connection()
        if conn is None:
            return False
        
        with conn.cursor() as cursor:
            affected_rows = cursor.execute(query, params or ())
            conn.commit()
            return affected_rows > 0
    except Exception as e:
        print(f"更新执行失败: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_dataframe(query, params=None):
    """执行查询并返回DataFrame"""
    try:
        engine = get_engine()
        df = pd.read_sql(query, engine, params=params)
        return df
    except Exception as e:
        print(f"DataFrame查询失败: {e}")
        return pd.DataFrame()

def test_connection():
    """测试数据库连接"""
    try:
        conn = get_db_connection()
        if conn:
            print("✅ 数据库连接成功！")
            conn.close()
            return True
        else:
            print("❌ 数据库连接失败！")
            return False
    except Exception as e:
        print(f"❌ 数据库连接测试失败: {e}")
        return False 