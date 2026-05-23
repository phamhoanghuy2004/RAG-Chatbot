from django.db import models

class LogEntry(models.Model):
    id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Ngày / Phiên test")
    user_question = models.TextField(verbose_name="Câu hỏi của người dùng")
    rag_answer = models.TextField(verbose_name="Câu trả lời RAG")
    accuracy = models.CharField(max_length=20, verbose_name="Accuracy (đúng/sai hoặc % điểm)")
    latency = models.FloatField(verbose_name="Latency (s)")
    user_satisfaction = models.IntegerField(verbose_name="User Satisfaction (1–5)")

    class Meta:
        db_table = 'log_entries'

    def __str__(self):
        return f"{self.timestamp} - {self.user_question[:30]}"
    
    
class Role(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    
    class Meta:
        db_table = 'roles'

    def __str__(self):
        return self.name


class User(models.Model):
    # Đã bỏ hết db_column, cột trong DB giờ sẽ tên y hệt tên biến
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    email = models.CharField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    account = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    roles = models.ManyToManyField(Role, db_table='user_roles') 
    
    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.name    
    

class Prompt(models.Model):
    PROMPT_TYPES = [
        ("summary", "Summary"),
        ("generate", "Generate Response"),
    ]
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=50, choices=PROMPT_TYPES)
    content = models.TextField()
    is_active = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        null=True, blank=True,
        on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'prompts'

    def __str__(self):
        return f"{self.id} ({self.type})"


class Document(models.Model):
    id = models.AutoField(primary_key=True)
    document_name = models.CharField(max_length=255, unique=True, verbose_name="Tên tài liệu")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'documents'

    def __str__(self):
        return self.document_name