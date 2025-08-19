from django.db import models

class LogEntry(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Ngày / Phiên test")
    user_question = models.TextField(verbose_name="Câu hỏi của người dùng")
    rag_answer = models.TextField(verbose_name="Câu trả lời RAG")
    accuracy = models.CharField(max_length=20, verbose_name="Accuracy (đúng/sai hoặc % điểm)")
    latency = models.FloatField(verbose_name="Latency (s)")
    user_satisfaction = models.IntegerField(verbose_name="User Satisfaction (1–5)")

    def __str__(self):
        return f"{self.timestamp} - {self.user_question[:30]}"

