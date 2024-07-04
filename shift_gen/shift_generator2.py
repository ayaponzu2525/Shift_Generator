import pandas as pd
import random
from datetime import datetime, time, timedelta
import holidays  # 日本の祝日を扱うライブラリ
from collections import defaultdict

# 従業員を表すクラス
class Employee:
    def __init__(self, name, register_skill, preferences):
        self.name = name  # 従業員の名前
        self.register_skill = register_skill  # レジスキルの有無（True/False）
        self.preferences = preferences  # 希望シフト時間のリスト
        self.shifts = []  # 割り当てられたシフトを格納するリスト
        self.preference_reflection_rate = 0  # 希望シフトの反映率

# シフトスケジューラーを表すクラス
class ShiftScheduler:
    def __init__(self, csv_file, start_date, end_date):
        self.employees, self.preferences = self.load_data(csv_file)
        self.start_date = start_date
        self.end_date = end_date
        self.schedule = {}

        # 日本の祝日リストを生成
        self.jp_holidays = holidays.JP(years=range(start_date.year, end_date.year + 1))

        # 時間帯ごとの必要人数（平日, 土日祝）
        self.required_staff = {
            'morning': (5, 6),
            'afternoon': (5, 7),
            'evening': (3, 4)
        }

        # レジ担当の必要人数（平日, 土日祝）
        self.required_register_staff = {
            'morning': (3, 4),
            'afternoon': (3, 4),
            'evening': (3, 4)
        }
        
        # 最大人数の制約
        self.max_staff = 10
        
    # 休日チェック関数
    def check_if_busy_day(self, date):
        # 土曜日（5）、日曜日（6）、または祝日の場合
        return date.weekday() >= 5 or date in self.jp_holidays
    
        # 祝日リスト生成関数
    def generate_holiday_list(self, start_date, end_date):
        holidays = []
        for day in holidays.between(start_date, end_date):
            holidays.append(day)
        return holidays

    # CSVファイルから従業員データを読み込むメソッド
    def load_data(self, file_path: str):
        # CSVファイルをDataFrameとして読み込む
        df = pd.read_csv(file_path)
        
        # 従業員情報を格納するリスト
        employees = []
        
        # 従業員ごとの希望シフトを格納する辞書
        # 構造: {従業員ID: {日付: [(開始時間, 終了時間), ...], ...}, ...}
        preferences = defaultdict(lambda: defaultdict(list))
        
        # DataFrameの各行を処理
        for _, row in df.iterrows():
            # 従業員情報を辞書として作成
            employee = {
                'id': row['従業員ID'],
                'name': row['name'],
                'skills': row['skills'].split(',') if isinstance(row['skills'], str) else []
            }
            employees.append(employee)
            
            # 希望日を日付オブジェクトに変換
            date = datetime.strptime(row['希望日'], '%Y-%m-%d').date()
            
            # 出勤時間と退勤時間が両方とも有効な場合のみ処理
            if pd.notna(row['出勤時間']) and pd.notna(row['退勤時間']):
                start_time = datetime.strptime(row['出勤時間'], '%H:%M').time()
                end_time = datetime.strptime(row['退勤時間'], '%H:%M').time()
                
                # 従業員IDと日付に対応する希望シフトリストに追加
                preferences[row['従業員ID']][date].append((start_time, end_time))
        
        # 従業員情報と希望シフト情報を返す
        return employees, preferences
    
    def print_imported_data(self):
        print("インポートした従業員データ:")
        for employee in self.employees:
            print(f"ID: {employee['id']}, 名前: {employee['name']}, スキル: {', '.join(employee['skills'])}")
        
        print("\n希望シフトデータ:")
        for employee_id, dates in self.preferences.items():
            print(f"従業員ID: {employee_id}")
            for date, shifts in dates.items():
                print(f"  日付: {date}")
                for start, end in shifts:
                    print(f"    {start.strftime('%H:%M')} - {end.strftime('%H:%M')}")

    # スケジュールを生成するメソッド
    def generate_schedule(self):
        current_date = self.start_date
        while current_date <= self.end_date:
            is_busy = self.check_if_busy_day(current_date)
            self.generate_day_shifts(current_date, is_busy)
            current_date += timedelta(days=1)
            
    def check_shift_coverage(self, date, is_busy):
        warnings = []
        for period in ['morning', 'afternoon', 'evening']:
            staff_count = self.count_staff_in_timerange(date, period)
            required = self.required_staff[period][1 if is_busy else 0]

            if staff_count < required:
                warnings.append(f"{date}: {period}のシフトが足りません。必要: {required}, 現在: {staff_count}")
            elif staff_count > self.max_staff:
                warnings.append(f"{date}: {period}のシフトが多すぎます。最大: {self.max_staff}, 現在: {staff_count}")

        return warnings

    # 1日分のシフトを生成するメソッド
    def generate_day_shifts(self, date, is_busy):
        store_open = datetime.combine(date, time(9, 0))
        store_close = datetime.combine(date, time(20, 0))
        day_shifts = []

        for employee in self.employees:
            employee_preferences = self.preferences[employee['id']][date]
            for start, end in employee_preferences:
                shift_start = max(store_open, datetime.combine(date, start))
                shift_end = min(store_close, datetime.combine(date, end))
                if shift_start < shift_end:
                    day_shifts.append(Shift(shift_start, shift_end, employee))

        self.schedule[date] = day_shifts
        self.check_shift_coverage(date, is_busy)
        
        # 2. その日のシフトを格納するリスト
        day_shifts = []

        # 3. 各従業員の希望シフトを確認
        for employee in self.employees:
            employee_preferences = self.preferences[employee['id']][date]
            
            # 4. 従業員の希望シフトがある場合、シフトを生成
            for start, end in employee_preferences:
                # 営業時間内に調整
                shift_start = max(store_open, datetime.combine(date, start))
                shift_end = min(store_close, datetime.combine(date, end))
                
                # シフトが有効な場合（開始時間が終了時間より前）、シフトを追加
                if shift_start < shift_end:
                    day_shifts.append(Shift(shift_start, shift_end, employee))

        # 5. 生成したシフトをスケジュールに追加
        self.schedule[date] = day_shifts

        # 6. レジスタッフの配置をチェック
        self.check_register_staff(date)

        # 7. 警告の出力（シフトが足りない場合）
    def check_shift_coverage(self, date, is_busy):
        warnings = []
        time_periods = [
            ('morning', time(9, 0), time(14, 0)),
            ('afternoon', time(14, 0), time(17, 0)),
            ('evening', time(17, 0), time(20, 0))
        ]

        for period, start, end in time_periods:
            staff_count = self.count_staff_in_timerange(date, start, end)
            required = self.required_staff[period][1 if is_busy else 0]

            if staff_count < required:
                warnings.append(f"{date}: {period}のシフトが足りません。必要: {required}, 現在: {staff_count}")
            elif staff_count > self.max_staff:
                warnings.append(f"{date}: {period}のシフトが多すぎます。最大: {self.max_staff}, 現在: {staff_count}")

        return warnings

    def count_staff_in_timerange(self, date, start_time, end_time):
        count = 0
        for shift in self.schedule[date]:
            if (shift.start_time.time() < end_time and shift.end_time.time() > start_time):
                count += 1
        return count

class Shift:
    def __init__(self, start_time, end_time, employee):
        self.start_time = start_time
        self.end_time = end_time
        self.employee = employee

    # レジスタッフの配置をチェックするメソッド（未実装）
    def check_register_staff(self):
        # レジスタッフの配置をチェックします
        pass

    # 休憩時間を計算するメソッド（未実装）
    def calculate_breaks(self):
        # 休憩時間を計算します
        pass

    # 希望反映率を計算するメソッド（未実装）
    def calculate_preference_reflection_rates(self):
        # 希望反映率を計算します
        pass

    # 個別の希望反映率を調整するメソッド（未実装）
    def adjust_individual_reflection_rates(self, employee, rate):
        # 個別の希望反映率を調整します
        pass

    # スケジュールを表示するメソッド
    def print_schedule(self):
        for date, shifts in self.schedule.items():
            print(f"Date: {date}")
            for shift in shifts:
                print(f"  {shift.employee.name}: {shift.start_time} - {shift.end_time}")
            print()

print("======================ok=====================")
