import csv

fieldnames = ["time"]

with open("btc_price_record.csv", "w", newline='', encoding="utf-8") as price_file, \
         open("btc_pred30_record.csv", "w", newline='', encoding="utf-8") as pred30_file, \
         open("btc_pred60_record.csv", "w", newline='', encoding="utf-8") as pred60_file:
        
        price_writer = csv.DictWriter(price_file, fieldnames=fieldnames)
        price_writer.writeheader()
        pred30_writer = csv.DictWriter(pred30_file, fieldnames=fieldnames)
        pred30_writer.writeheader()
        pred60_writer = csv.DictWriter(pred60_file, fieldnames=fieldnames)
        pred60_writer.writeheader()