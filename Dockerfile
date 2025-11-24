# Asosiy Python versiyasini tanlash
FROM python:3.9-slim

# Ish katalogini o'rnatish
WORKDIR /app

# Talablarni nusxalash va o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bot kodini nusxalash
COPY main.py .

# Botni ishga tushirish buyrug'i
# "main.py" faylidagi "start_bot" funksiyasiga mos bo'lishi kerak
CMD ["python", "main.py"]