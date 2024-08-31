import csv
import sqlite3
from datetime import datetime, date

def adapt_date(val):
    return val.isoformat()

def convert_date(val):
    return date.fromisoformat(val.decode())

# 日付型のアダプターとコンバーターを登録
sqlite3.register_adapter(date, adapt_date)
sqlite3.register_converter("date", convert_date)

def import_shifts_from_csv(csv_file):
    conn = sqlite3.connect('shiftlist.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cursor = conn.cursor()

    # テーブルを削除（既存のテーブルがある場合）
    cursor.execute("DROP TABLE IF EXISTS shifts")

    # 新しいテーブルを作成
    cursor.execute("""
    CREATE TABLE shifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        name TEXT NOT NULL,
        skills TEXT,
        desired_date DATE,
        clock_in TEXT,
        clock_out TEXT
    )
    """)

    with open(csv_file, 'r', encoding='utf-8') as file:
        csv_reader = csv.reader(file)
        headers = next(csv_reader)
        date_columns = headers[3:]  # 日付列は4列目から

        for row in csv_reader:
            employee_id = int(row[0])
            name = row[1]
            skills = row[2]

            # 各日付についてシフトを処理
            for i, shift in enumerate(row[3:], start=3):
                if shift and shift.lower() != '休み':
                    # 日付形式を %Y/%m/%d に変更
                    date = datetime.strptime(headers[i], '%Y/%m/%d').date()
                    if '-' in shift:
                        clock_in, clock_out = shift.split('-')
                    else:
                        clock_in = shift
                        clock_out = None

                    cursor.execute("""
                    INSERT INTO shifts (employee_id, name, skills, desired_date, clock_in, clock_out)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (employee_id, name, skills, date, clock_in, clock_out))

    conn.commit()
    conn.close()

# CSVファイルからデータを読み込んで挿入
csv_file = 'shift.csv'
import_shifts_from_csv(csv_file)