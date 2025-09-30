import jwt
import datetime
from django.conf import settings


def create_jwt_token (user):
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "user_id" : user.id,
        "roles" : [ role.name for role in user.roles.all()],
        "user_name" : user.name,
        "type": "access",
        "exp" : now + settings.ACCESS_TOKEN_LIFETIME,
        "iat" : now
    }
    token = jwt.encode(payload,settings.SECRET_KEY_JWT,algorithm="HS256") # Tra ve dang string
    return token
    
    
def decode_jwt (token : str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY_JWT, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    
