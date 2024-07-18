import pandas as pd
import datetime
from collections import defaultdict
import holidays

class Employee:
    def __init__(self, id, name, register_skill, preferences):
        self.id = id  # 従業員ID
        self.name = name  # 従業員の名前
        self.register_skill = register_skill  # レジスキルの有無（True/False）
        self.preferences = preferences  # 希望シフト時間のリスト（辞書形式：{日付: [(開始時間, 終了時間), ...]}）
        self.shifts = []  # 割り当てられたシフトを格納するリスト
        self.preference_reflection_rate = None  # 希望シフトの反映率（初期値はNone、シフト生成後に計算）

    def calculate_preference_reflection_rate(self, start_date, end_date):
        """
        指定された期間における希望シフトの反映率を計算する
        
        :param start_date: 計算開始日
        :param end_date: 計算終了日
        :return: 希望シフトの反映率（0-100の範囲）
        """
        total_preferred_hours = 0
        total_assigned_hours = 0
        current_date = start_date
        while current_date <= end_date:
            # その日の希望シフト時間を合計
            preferred_hours = sum((end - start).total_seconds() / 3600 
                                  for start, end in self.preferences.get(current_date, []))
            # その日の割り当てられたシフト時間を合計
            assigned_hours = sum((shift.end_time - shift.start_time).total_seconds() / 3600 
                                 for shift in self.shifts if shift.start_time.date() == current_date)
            total_preferred_hours += preferred_hours
            total_assigned_hours += assigned_hours
            current_date += datetime.timedelta(days=1)
        
        # 希望シフト時間がある場合のみ反映率を計算
        if total_preferred_hours > 0:
            self.preference_reflection_rate = (total_assigned_hours / total_preferred_hours) * 100
        else:
            self.preference_reflection_rate = 0
        
        return self.preference_reflection_rate

class Shift:
    def __init__(self, start_time, end_time, employee):
        self.start_time = start_time  # シフト開始時間
        self.end_time = end_time  # シフト終了時間
        self.employee = employee  # シフトに割り当てられた従業員
        self.break_time = self.calculate_break_time()  # 休憩時間

    def calculate_break_time(self):
        """
        シフトの長さに基づいて休憩時間を計算する
        
        :return: 休憩時間（分）
        """
        shift_duration = (self.end_time - self.start_time).total_seconds() / 3600
        if shift_duration < 5:
            return 0
        elif shift_duration < 6:
            return 15
        elif shift_duration < 8:
            return 30
        else:
            return 45

class ShiftGenerator:
    def __init__(self, csv_file):
        self.employees = []  # 従業員リスト
        self.preferences = defaultdict(lambda: defaultdict(list))  # 従業員の希望シフト
        self.load_data(csv_file)  # CSVファイルからデータを読み込む
        self.jp_holidays = holidays.JP()  # 日本の祝日カレンダー
        
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
        
        self.max_staff = 10  # 最大スタッフ数
        self.schedule = {}  # 生成されたシフトスケジュール

    def load_data(self, file_path):
        """
        CSVファイルから従業員データを読み込む
        
        :param file_path: CSVファイルのパス
        """
        df = pd.read_csv(file_path)
        
        for _, row in df.iterrows():
            employee = Employee(
                id=row['従業員ID'],
                name=row['name'],
                register_skill='レジ' in row['skills'].split(','),
                preferences={}
            )
            self.employees.append(employee)
            
            date = datetime.datetime.strptime(row['希望日'], '%Y-%m-%d').date()
            
            if pd.notna(row['出勤時間']) and pd.notna(row['退勤時間']):
                start_time = datetime.datetime.strptime(row['出勤時間'], '%H:%M').time()
                end_time = datetime.datetime.strptime(row['退勤時間'], '%H:%M').time()
                
                self.preferences[employee.id][date].append((start_time, end_time))
                employee.preferences[date] = [(start_time, end_time)]
        
    def get_shift_hours(self, shift_name):
        """
        シフト名から開始時間と終了時間を取得する
        
        :param shift_name: シフト名 ('morning', 'afternoon', 'evening')
        :return: (開始時間, 終了時間) のタプル
        """
        if shift_name == 'morning':
            return datetime.time(9, 0), datetime.time(14, 0)
        elif shift_name == 'afternoon':
            return datetime.time(14, 0), datetime.time(17, 0)
        elif shift_name == 'evening':
            return datetime.time(17, 0), datetime.time(20, 0)
        else:
            raise ValueError(f"Invalid shift name: {shift_name}")

    def generate_shifts(self, start_date, end_date):
        """
        指定された期間のシフトを生成する
        
        :param start_date: シフト生成開始日
        :param end_date: シフト生成終了日
        :return: 生成されたシフト、人員不足情報、スキル（レジ）不足情報
        """
        current_date = start_date
        shortages = defaultdict(lambda: defaultdict(int))
        skill_shortages = defaultdict(lambda: defaultdict(int))

        while current_date <= end_date:
            is_busy = self.check_if_busy_day(current_date)
            day_shifts, day_shortages, day_skill_shortages = self.generate_day_shifts(current_date, is_busy)
            self.schedule[current_date] = day_shifts
            shortages[current_date] = day_shortages
            skill_shortages[current_date] = day_skill_shortages
            current_date += datetime.timedelta(days=1)

        # シフト生成後、各従業員の希望シフト反映率を計算
        for employee in self.employees:
            employee.calculate_preference_reflection_rate(start_date, end_date)

        return self.schedule, shortages, skill_shortages

    def check_if_busy_day(self, date):
        """
        指定された日が混雑日（土日祝）かどうかを判定する
        
        :param date: 判定する日付
        :return: 混雑日の場合True、そうでない場合False
        """
        return date.weekday() >= 5 or date in self.jp_holidays

    def generate_day_shifts(self, date, is_busy):
        """
        1日分のシフトを生成する
        
        :param date: シフトを生成する日付
        :param is_busy: 混雑日かどうか
        :return: 生成されたシフト、人員不足情報、スキル（レジ）不足情報
        """
        store_open = datetime.datetime.combine(date, datetime.time(9, 0))
        store_close = datetime.datetime.combine(date, datetime.time(20, 0))
        day_shifts = []
        shortages = defaultdict(int)
        skill_shortages = defaultdict(int)

        for employee in self.employees:
            employee_preferences = self.preferences[employee.id].get(date, [])
            for start, end in employee_preferences:
                shift_start = max(store_open, datetime.datetime.combine(date, start))
                shift_end = min(store_close, datetime.datetime.combine(date, end))
                if shift_start < shift_end:
                    day_shifts.append(Shift(shift_start, shift_end, employee))

        self.check_shift_coverage(date, is_busy, day_shifts, shortages)
        self.check_register_staff(date, is_busy, day_shifts, skill_shortages)

        return day_shifts, shortages, skill_shortages

    def check_shift_coverage(self, date, is_busy, shifts, shortages):
        """
        シフトの人員カバー状況をチェックする
        
        :param date: チェックする日付
        :param is_busy: 混雑日かどうか
        :param shifts: その日のシフトリスト
        :param shortages: 人員不足情報を格納する辞書
        """
        time_periods = [
            ('morning', datetime.time(9, 0), datetime.time(14, 0)),
            ('afternoon', datetime.time(14, 0), datetime.time(17, 0)),
            ('evening', datetime.time(17, 0), datetime.time(20, 0))
        ]

        for period, start, end in time_periods:
            staff_count = self.count_staff_in_timerange(shifts, start, end)
            required = self.required_staff[period][1 if is_busy else 0]

            if staff_count < required:
                shortages[period] = required - staff_count

    def check_register_staff(self, date, is_busy, shifts, skill_shortages):
        """
        レジスタッフの配置状況をチェックする
        
        :param date: チェックする日付
        :param is_busy: 混雑日かどうか
        :param shifts: その日のシフトリスト
        :param skill_shortages: スキル（レジ）不足情報を格納する辞書
        """
        time_periods = [
            ('morning', datetime.time(9, 0), datetime.time(14, 0)),
            ('afternoon', datetime.time(14, 0), datetime.time(17, 0)),
            ('evening', datetime.time(17, 0), datetime.time(20, 0))
        ]

        for period, start, end in time_periods:
            register_staff_count = self.count_register_staff_in_timerange(shifts, start, end)
            required = self.required_register_staff[period][1 if is_busy else 0]

            if register_staff_count < required:
                skill_shortages[period] = required - register_staff_count

    def count_staff_in_timerange(self, shifts, start_time, end_time):
        """
        指定された時間範囲内のスタッフ数をカウントする
        
        :param shifts: シフトのリスト
        :param start_time: 開始時間
        :param end_time: 終了時間
        :return: スタッフ数
        """
        return sum(1 for shift in shifts if shift.start_time.time() < end_time and shift.end_time.time() > start_time)

    def count_register_staff_in_timerange(self, shifts, start_time, end_time):
        """
        指定された時間範囲内のレジスタッフ数をカウントする
        
        :param shifts: シフトのリスト
        :param start_time: 開始時間
        :param end_time: 終了時間
        :return: レジスタッフ数
        """
        return sum(1 for shift in shifts if shift.start_time.time() < end_time and shift.end_time.time() > start_time and shift.employee.register_skill)

    def display_preference_rates(self):
        """
        全従業員のシフト希望反映率を表示する
        """
        print("シフト希望反映率:")
        for employee in self.employees:
            print(f"{employee.name}: {employee.preference_reflection_rate:.2f}%")

    def set_preference_rate(self, employee_id, rate):
        """
        指定された従業員のシフト希望反映率を設定する
        
        :param employee_id: 従業員ID
        :param rate: 設定する反映率
        """
        for employee in self.employees:
            if employee.id == employee_id:
                employee.preference_reflection_rate = rate
                break

    def display_shifts(self, start_date, end_date):
        """
        指定された期間のシフトを表示する
        
        :param start_date: 表示開始日
        :param end_date: 表示終了日
        """
        current_date = start_date
        while current_date <= end_date:
            print(f"\n日付: {current_date}")
            if current_date in self.schedule:
                for shift in self.schedule[current_date]:
                    print(f"  {shift.employee.name}: {shift.start_time.time()} - {shift.end_time.time()} (休憩: {shift.break_time}分)")
            else:
                print("  シフトなし")
            current_date += datetime.timedelta(days=1)

    def calculate_overall_preference_reflection_rate(self, start_date, end_date):
        """
        指定された期間の全体的なシフト希望反映率を計算する
        
        :param start_date: 計算開始日
        :param end_date: 計算終了日
        :return: 全体的なシフト希望反映率
        """
        total_preferred_hours = 0
        total_assigned_hours = 0
        current_date = start_date
        while current_date <= end_date:
            for employee in self.employees:
                preferred_hours = sum((end - start).total_seconds() / 3600 
                                      for start, end in employee.preferences.get(current_date, []))
                assigned_hours = sum((shift.end_time - shift.start_time).total_seconds() / 3600 
                                     for shift in self.schedule.get(current_date, []) if shift.employee.id == employee.id)
                total_preferred_hours += preferred_hours
                total_assigned_hours += assigned_hours
            current_date += datetime.timedelta(days=1)
        
        if total_preferred_hours > 0:
            return (total_assigned_hours / total_preferred_hours) * 100
        else:
            return 0

    def calculate_employee_preference_reflection_rate(self, employee_id, start_date, end_date):
        """
        指定された従業員の指定期間におけるシフト希望反映率を計算する
        
        :param employee_id: 従業員ID
        :param start_date: 計算開始日
        :param end_date: 計算終了日
        :return: 従業員のシフト希望反映率
        """
        employee = next((emp for emp in self.employees if emp.id == employee_id), None)
        if not employee:
            return 0

        return employee.calculate_preference_reflection_rate(start_date, end_date)
    
print("======================ok=============================")