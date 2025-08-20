import bcrypt

def check_password (plaintext_password, hashed_password):
    return bcrypt.checkpw(plaintext_password, hashed_password)



