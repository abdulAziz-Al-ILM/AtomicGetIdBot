# Asosiy Python versiyasini tanlash
FROM python:3.9-slim

# Ish katalogini o'rnatish
WORKDIR /app

# Talablarni nusxalash va o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bot kodini nusxalash
COPY main.py .

# SQLite ma'lumotlar bazasi uchun /app katalogiga yozish huquqini berish
RUN chmod -R 777 /app

# Botni ishga tushirish buyrug'i
CMD ["python", "main.py"]
