from datetime import datetime
current_date = datetime.now()
month_code = current_date.strftime("%b")  # 3-letter month code
day_code = current_date.strftime("%d")

print(month_code.upper(), day_code)