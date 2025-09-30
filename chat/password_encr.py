import bcrypt

def check_password (plaintext_password, hashed_password):
    return bcrypt.checkpw(plaintext_password, hashed_password)

def hash_password(plaintext_password: str) -> str:
    # Mã hóa password: cần encode sang bytes
    hashed = bcrypt.hashpw(plaintext_password.encode("utf-8"), bcrypt.gensalt())
    # Trả về string để lưu DB (decode từ bytes)
    return hashed.decode("utf-8")


# Ví dụ sử dụng
plain = "123456"
hashed_pw = hash_password(plain)
print("Plain:", plain)
print("Hashed:", hashed_pw)

