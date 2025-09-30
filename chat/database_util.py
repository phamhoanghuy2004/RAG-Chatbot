import mysql.connector 
from  mysql.connector import Error
import os
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from .models import User
from .models import Prompt

class MySQLConnector:
    def __init__(self, host, port , user, password, database,  ssl_ca=None):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.ssl_ca = ssl_ca  # Đường dẫn file SSL CA
        self.connection = None
        
    def connect(self):
        try: 
            conn_args = {
                "host" : self.host,
                "port" : self.port,
                "user" : self.user,
                "password" : self.password,
                "database" : self.database
            }
            
            if self.ssl_ca:
                conn_args["ssl_ca"] = self.ssl_ca # bật SSL nếu có file CA
                
            self.connection = mysql.connector.connect(**conn_args)
            
            if self.connection.is_connected():
                print("Kết nối MySQL thành công!")
        except Error as e:
            print(f"Lỗi kết nối MySQL: {e}")
            
    def disconnect (self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("Đã ngắt kết nối MySQL.")
            
def get_db_connection():
    return MySQLConnector(
        host=settings.DATABASES['db_Huy']['HOST'],
        user=settings.DATABASES['db_Huy']['USER'],
        port=settings.DATABASES['db_Huy']['PORT'],
        password=settings.DATABASES['db_Huy']['PASSWORD'],
        database=settings.DATABASES['db_Huy']['NAME'],
        ssl_ca=settings.DATABASES['db_Huy']['OPTIONS']['ssl']['ca']
    )
    
def get_user (query, param):
    db = get_db_connection()
    db.connect()
    
    if not db.connection or not db.connection.is_connected():
        print("Chưa kết nối Mysql")
        return None
    try:
        with db.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, param)
            return cursor.fetchone()        
    except Error as e:
        print(f"Lỗi khi lấy user: {e}")
        return None
    finally:
        db.disconnect()
  
# def get_user_by_id (user_id):
#     query = """select *
#             from `users` u
#             where u.user_id = %s """
#     param = (user_id,)
#     return get_user (query,param)
        
# def get_user_by_account (user_account):
#     query = """select u.user_id, u.user_name, u.user_account, u.user_password, r.role_id, r.role_name
#                 from `users` u
#                 inner join  `user_roles`  ur on u.user_id = ur.user_id 
#                 inner join `roles` r on ur.role_id = r.role_id
#                 where u.user_account = %s """
#     param = (user_account,)
#     return get_user (query,param)        

def get_user_by_id (user_id):
    try:
        return User.objects.get(id=user_id)
    except ObjectDoesNotExist:
        return None

def get_user_by_account(user_account:str):
    try: 
        # lấy user + prefetch luôn roles để tránh query thừa
        user = User.objects.prefetch_related("roles").get(account=user_account)
        return user
    except ObjectDoesNotExist:
        return None
                
def get_generate_prompt ():
    try:
        return Prompt.objects.filter(
            type="generate",
            is_active=True    
        ).first()
    except ObjectDoesNotExist:
        return None
    
def get_summary_prompt ():
    try:
        return Prompt.objects.filter(
            type="summary",
            is_active=True    
        ).first()
    except ObjectDoesNotExist:
        return None