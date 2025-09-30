from django.db import models

class LogEntry(models.Model):
    id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Ngày / Phiên test")
    user_question = models.TextField(verbose_name="Câu hỏi của người dùng")
    rag_answer = models.TextField(verbose_name="Câu trả lời RAG")
    accuracy = models.CharField(max_length=20, verbose_name="Accuracy (đúng/sai hoặc % điểm)")
    latency = models.FloatField(verbose_name="Latency (s)")
    user_satisfaction = models.IntegerField(verbose_name="User Satisfaction (1–5)")

    def __str__(self):
        return f"{self.timestamp} - {self.user_question[:30]}"
    
    
class Role(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name

class User(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    email = models.CharField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True) # mặc định thì null false
    account = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True) #auto_now_add: Tự động set giá trị ngày/giờ khi bản ghi được tạo lần đầu. Không thay đổi sau này
    updated_at = models.DateTimeField(auto_now=True)   #auto_now: Tự động cập nhật TG hiện tại nếu dùng save()
    roles = models.ManyToManyField(Role) # Django sẽ tự tạo bảng trung gian
    
    def __str__(self):
        return self.name    
    
class Prompt (models.Model):
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

    def __str__(self):
        return f"{self.id} ({self.type})"