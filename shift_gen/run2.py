from datetime import datetime, time, timedelta
from shift_generator2 import ShiftScheduler

def main():
    start_date = datetime(2024, 7, 1)
    end_date = datetime(2024, 7, 31)
    scheduler = ShiftScheduler('shift_gen/shift.csv', start_date, end_date)  # フォワードスラッシュを使用

    # インポートしたデータの確認
    scheduler.print_imported_data()

    # スケジュール生成
    scheduler.generate_schedule()

if __name__ == "__main__":
    main()