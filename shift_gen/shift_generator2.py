import pandas as pd
import datetime
from collections import defaultdict
import holidays

class Employee:
    def __init__(self, id, name, register_skill, refrigeration_skill, preferences):
        self.id = id
        self.name = name
        self.register_skill = register_skill
        self.refrigeration_skill = refrigeration_skill
        self.preferences = preferences
        self.shifts = []

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
        elif shift_duration < 7:
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
        
        self.required_refrigeration_staff = {
            'evening': (1, 1)  # 平日, 土日祝
        }

    def load_data(self, file_path):
        """
        CSVファイルから従業員データを読み込む
        
        :param file_path: CSVファイルのパス
        """
        df = pd.read_csv(file_path)
        
        for _, row in df.iterrows():
            skills = row['skills'].split(',')
            employee = Employee(
                id=row['従業員ID'],
                name=row['name'],
                register_skill='レジ' in skills,
                refrigeration_skill='冷蔵' in skills,
                preferences={}
            )
            self.employees.append(employee)
            
            date = datetime.datetime.strptime(row['希望日'], '%Y-%m-%d').date()
            
            if pd.notna(row['出勤時間']) and pd.notna(row['退勤時間']):
                start_time = datetime.datetime.strptime(row['出勤時間'], '%H:%M').time()
                end_time = datetime.datetime.strptime(row['退勤時間'], '%H:%M').time()
                
                self.preferences[employee.id][date].append((start_time, end_time))
                employee.preferences[date] = [(start_time, end_time)]
        

    def generate_shifts(self, start_date, end_date):
        """
        指定された期間のシフトを生成する
        
        :param start_date: シフト生成開始日
        :param end_date: シフト生成終了日
        :return: 生成されたシフト、人員不足情報、スキル（レジ）不足情報
        """
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

        self.check_shift_coverage(is_busy, day_shifts, shortages)
        self.check_register_staff(is_busy, day_shifts, skill_shortages)
        self.check_refrigeration_staff(is_busy, day_shifts, skill_shortages)

        return day_shifts, shortages, skill_shortages

    def check_shift_coverage(self, is_busy, shifts, shortages):
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

    def check_register_staff(self, is_busy, shifts, skill_shortages):
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
                skill_shortages[f'{period}_register'] = required - register_staff_count
    
    def check_refrigeration_staff(self, is_busy, shifts, skill_shortages):
        '''
        冷蔵スキル持つスタッフの配置
        '''
        evening_start = datetime.time(17, 0)
        evening_end = datetime.time(20, 0)
        refrigeration_staff_count = self.count_refrigeration_staff_in_timerange(shifts, evening_start, evening_end)
        required = self.required_refrigeration_staff['evening'][1 if is_busy else 0]

        if refrigeration_staff_count < required:
            skill_shortages['evening_refrigeration'] = required - refrigeration_staff_count
    
    def count_refrigeration_staff_in_timerange(self, shifts, start_time, end_time):
        '''
        冷蔵スキルを持つスタッフが必要数いるかカウント
        '''
        return sum(1 for shift in shifts 
                    if shift.start_time.time() < end_time 
                    and shift.end_time.time() > start_time 
                    and shift.employee.refrigeration_skill)



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
        employee_rates = []
        for employee in self.employees:
            rate = self.calculate_employee_preference_reflection_rate(employee.id, start_date, end_date)
            if rate != 100:  # 希望シフトがある従業員のみ計算に含める
                employee_rates.append(rate)
        
        if employee_rates:
            return sum(employee_rates) / len(employee_rates)
        else:
            return 100  # 全員希望シフトがない場合は100%とする

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

        total_preferred_minutes = 0
        total_assigned_minutes = 0
        current_date = start_date
        while current_date <= end_date:
            preferred_shifts = employee.preferences.get(current_date, [])
            if preferred_shifts:  # 希望シフトがある日のみ計算
                preferred_minutes = sum(self.time_diff_in_minutes(end, start) for start, end in preferred_shifts)
                assigned_shifts = [shift for shift in self.schedule.get(current_date, []) if shift.employee.id == employee_id]
                assigned_minutes = sum(self.time_diff_in_minutes(shift.end_time.time(), shift.start_time.time()) for shift in assigned_shifts)
                total_preferred_minutes += preferred_minutes
                total_assigned_minutes += assigned_minutes
            current_date += datetime.timedelta(days=1)
        
        if total_preferred_minutes > 0:
            return (total_assigned_minutes / total_preferred_minutes) * 100
        else:
            return 100  # 希望シフトがない場合は100%とする

    @staticmethod
    def time_diff_in_minutes(end, start):
        '''
        時間の計算を分単位で行う
        '''
        return ((datetime.datetime.combine(datetime.date.today(), end) - 
                datetime.datetime.combine(datetime.date.today(), start)).total_seconds() / 60)
    
print("======================ok=============================")