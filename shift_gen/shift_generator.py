import pandas as pd
import datetime
import holidays
from collections import defaultdict
from typing import List, Dict, Tuple
import random

'''
pip したもの
pandas
datetime
holidays
'''
class ShiftGenerator:
    #最少人数と最大人数
    def __init__(self, data_file: str):
        self.employees, self.preferences = self.load_data(data_file)
        self.shifts = defaultdict(lambda: defaultdict(list))
        self.preference_rates = {emp['id']: 100 for emp in self.employees}  # 初期値は100%
        self.min_shift_duration = 2  # 最小シフト時間（時間単位）

        self.min_employees = {
            '早朝': 0,
            '朝': 5,
            '昼': 5,
            '夜': 5,
            '深夜': 0,
        }
        self.max_employees = {
            '早朝': 0,
            '朝': 7,
            '昼': 8,
            '夜': 6,
            '深夜': 0,
        }
        self.strict_min_employees = {
            '早朝': 0,
            '朝': 3,
            '昼': 3,
            '夜': 3,
            '深夜': 0,
        }
        self.strict_max_employees = {
            '早朝': 0,
            '朝': 10,
            '昼': 12,
            '夜': 10,
            '深夜': 0,
        }
        # 日本の祝日を初期化
        self.jp_holidays = holidays.JP() 
      
      
    def load_data(self, file_path: str):
        df = pd.read_csv(file_path)
        employees = []
        preferences = defaultdict(lambda: defaultdict(list))
        
        for _, row in df.iterrows():
            employee = {
                'id': row['従業員ID'],
                'name': row['name'],
                'skills': row['skills'].split(',') if isinstance(row['skills'], str) else []
            }
            employees.append(employee)
            
            date = datetime.datetime.strptime(row['希望日'], '%Y-%m-%d').date()
            if pd.notna(row['出勤時間']) and pd.notna(row['退勤時間']):
                start_time = datetime.datetime.strptime(row['出勤時間'], '%H:%M').time()
                end_time = datetime.datetime.strptime(row['退勤時間'], '%H:%M').time()
                preferences[row['従業員ID']][date].append((start_time, end_time))
        
        return employees, preferences

    
    def display_preference_rates(self):
        print("\n従業員別シフト希望反映率:")
        for emp in self.employees:
            print(f"{emp['name']}: {self.preference_rates[emp['id']]}%")

    def set_preference_rate(self, employee_id: int, rate: int):
        if 0 <= rate <= 100 and employee_id in self.preference_rates:
            self.preference_rates[employee_id] = rate
            print(f"従業員ID {employee_id} のシフト希望反映率を {rate}% に設定しました。")
        else:
            print("無効な従業員IDまたは反映率です。")
            
    def is_preferred_shift(self, employee, date, start_hour, end_hour):
        if employee['id'] in self.preferences and date in self.preferences[employee['id']]:
            for pref_start, pref_end in self.preferences[employee['id']][date]:
                if (pref_start.hour <= start_hour < pref_end.hour) or \
                    (pref_start.hour < end_hour <= pref_end.hour) or \
                    (start_hour <= pref_start.hour and pref_end.hour <= end_hour):
                    # 希望反映率を考慮
                    return random.randint(1, 100) <= self.preference_rates[employee['id']]
        return False
    # 他のメソッドは前回のコードと同じなので省略
    # 休日チェック関数
    def check_if_holiday(self, date):
        # 土曜日（5）または日曜日（6）の場合
        if date.weekday() >= 5:
            return True

        # 祝日の場合
        if date in self.jp_holidays:
            return True

        return False

    def assign_shift(self, date, shift_name, start_hour, end_hour):
        available_employees = self.get_available_employees(date, start_hour, end_hour)
        assigned_employees = []

        while available_employees and len(assigned_employees) < self.strict_max_employees[shift_name]:
            best_employee = self.select_best_employee(available_employees, date, start_hour, end_hour, len(assigned_employees))
            if best_employee:
                emp_start, emp_end = self.get_employee_preferred_time(best_employee, date, start_hour, end_hour)
                if emp_start is not None and emp_end is not None:
                    if emp_end - emp_start >= self.min_shift_duration:
                        if not any(emp['employee']['id'] == best_employee['id'] for emp in assigned_employees):
                            if random.randint(1, 100) <= self.preference_rates[best_employee['id']]:
                                assigned_employees.append({
                                    'employee': best_employee,
                                    'start': emp_start,
                                    'end': emp_end,
                                    'break': self.calculate_break_after_merge(emp_start, emp_end)
                                })
            available_employees.remove(best_employee)

        self.shifts[date][shift_name] = assigned_employees
        return assigned_employees

    def get_shift_name(self, hour):
          if 5 <= hour < 9:
              return '早朝'
          elif 9 <= hour < 14:
              return '朝'
          elif 14 <= hour < 17:
              return '昼'
          elif 17 <= hour < 20:
              return '夜'
          else:
              return '深夜'

    def get_employee_preferred_time(self, employee, date, start_hour, end_hour):
        if employee['id'] in self.preferences and date in self.preferences[employee['id']]:
            for pref_start, pref_end in self.preferences[employee['id']][date]:
                print(f"Checking preference for {employee['name']} on {date}: {pref_start} - {pref_end}")
                if pref_start.hour <= start_hour and pref_end.hour >= end_hour:
                    return start_hour, end_hour
                elif pref_start.hour <= start_hour < pref_end.hour:
                    return start_hour, min(end_hour, pref_end.hour)
                elif pref_start.hour < end_hour <= pref_end.hour:
                    return max(start_hour, pref_start.hour), end_hour
        return None, None

    def adjust_shift_time(self, employee, date, start_hour, end_hour):
        emp_id = employee['id']
        if emp_id in self.preferences and date in self.preferences[emp_id]:
            for pref_start, pref_end in self.preferences[emp_id][date]:
                if pref_start.hour <= start_hour and pref_end.hour >= end_hour:
                    return start_hour, end_hour
                elif pref_start.hour <= start_hour < pref_end.hour:
                    return start_hour, min(end_hour, pref_end.hour)
                elif pref_start.hour < end_hour <= pref_end.hour:
                    return max(start_hour, pref_start.hour), end_hour
        return start_hour, end_hour

    def get_available_employees(self, date, start_hour, end_hour):
        available_employees = []
        for emp in self.employees:
            if self.is_employee_available(emp, date, start_hour, end_hour):
                available_employees.append(emp)
        return available_employees


    def is_employee_available(self, employee, date, start_hour, end_hour):
        if employee['id'] in self.preferences and date in self.preferences[employee['id']]:
            for pref_start, pref_end in self.preferences[employee['id']][date]:
                if (pref_start.hour <= start_hour < pref_end.hour) or \
                   (pref_start.hour < end_hour <= pref_end.hour) or \
                   (start_hour <= pref_start.hour and pref_end.hour <= end_hour):
                    return True
        return False

    def check_shift_extension(self, employee, date, start_hour, end_hour):
        warnings = []

        # 1. 1日の最大労働時間をチェック（例：10時間）
        daily_hours = self.calculate_daily_hours(employee, date)
        if daily_hours + (end_hour - start_hour) > 10:
            warnings.append("1日の労働時間が10時間を超えます")

        # 2. 週間労働時間をチェック（例：40時間）
        weekly_hours = self.calculate_weekly_hours(employee, date)
        if weekly_hours + (end_hour - start_hour) > 40:
            warnings.append("週間労働時間が40時間を超えます")

        # 3. 連続勤務日数をチェック（例：6日まで）
        consecutive_days = self.count_consecutive_days(employee, date)
        if consecutive_days >= 6:
            warnings.append("連続勤務日数が6日を超えます")

        # 4. シフト間の最小休憩時間をチェック（例：11時間）
        if not self.check_minimum_rest(employee, date, start_hour, end_hour):
            warnings.append("前のシフトとの間隔が11時間未満です")

        # 5. 従業員の希望シフトとの適合性をチェック
        if not self.check_employee_preference(employee, date, start_hour, end_hour):
            warnings.append("従業員の希望シフト外です")

        return warnings



    def check_minimum_rest(self, employee, date, start_hour, end_hour):
        previous_shift_end = self.get_previous_shift_end(employee, date)
        if previous_shift_end is not None:
            rest_hours = start_hour - previous_shift_end
            if rest_hours < 11:  # 最小11時間の休憩
                return False
        return True

    def get_previous_shift_end(self, employee, date):
        previous_date = date - datetime.timedelta(days=1)
        if previous_date in self.shifts:
            for shift in self.shifts[previous_date].values():
                for emp in shift:
                    if emp['employee']['id'] == employee['id']:
                        return emp['end']
        return None

    def check_employee_preference(self, employee, date, start_hour, end_hour):
      if employee['id'] in self.preferences and date in self.preferences[employee['id']]:
          for pref_start, pref_end in self.preferences[employee['id']][date]:
              # 希望シフトと割り当てシフトが重なっているかチェック
              if (pref_start.hour <= start_hour < pref_end.hour) or \
                  (pref_start.hour < end_hour <= pref_end.hour) or \
                  (start_hour <= pref_start.hour and pref_end.hour <= end_hour):
                  return True
      return False


    def select_best_employee(self, available_employees, date, start_hour, end_hour, current_assigned):
        scored_employees = []
        for emp in available_employees:
            score = self.score_employee(emp, date, start_hour, end_hour, current_assigned)
            scored_employees.append((emp, score))

        return max(scored_employees, key=lambda x: x[1])[0] if scored_employees else None

    def is_preferred_shift(self, employee, date, start_hour, end_hour):
        if employee['id'] in self.preferences and date in self.preferences[employee['id']]:
            for pref_start, pref_end in self.preferences[employee['id']][date]:
                if (pref_start.hour <= start_hour < pref_end.hour) or \
                    (pref_start.hour < end_hour <= pref_end.hour) or \
                    (start_hour <= pref_start.hour and pref_end.hour <= end_hour):
                    return True
        return False


    def score_employee(self, employee, date, start_hour, end_hour, current_assigned):
        score = 0

        # シフト希望度のスコア
        if self.is_preferred_shift(employee, date, start_hour, end_hour):
            score += 100

        # スキルマッチ度のスコア
        if '冷蔵' in employee['skills']:
            score += 30  # 冷蔵スキルを持つ従業員を優先
        if 'レジ' in employee['skills']:
            score += 20
        if '品出し' in employee['skills']:
            score += 20

        # 労働時間バランスのスコア
        weekly_hours = self.calculate_weekly_hours(employee, date)
        if weekly_hours + (end_hour - start_hour) <= 40:
            score += 50
        else:
            score -= (weekly_hours + (end_hour - start_hour) - 40) * 10

        # 連続勤務日数のペナルティ
        consecutive_days = self.count_consecutive_days(employee, date)
        if consecutive_days >= 5:
            score -= (consecutive_days - 4) * 20

        # 目安の最小・最大人数を考慮したスコア調整
        shift_name = self.get_shift_name(start_hour)
        if current_assigned < self.min_employees[shift_name]:
            score += 30  # 目安の最小人数を下回っている場合、スコアを上げる
        elif current_assigned >= self.max_employees[shift_name]:
            score -= 30  # 目安の最大人数を超えている場合、スコアを下げる

        return score
    
    def calculate_preference_reflection_rate(self):
        total_shifts = 0
        reflected_shifts = 0
        for date, shifts in self.shifts.items():
            for shift_name, employees in shifts.items():
                for emp in employees:
                    total_shifts += 1
                    if self.is_employee_preferred_shift(emp['employee'], date, emp['start'], emp['end']):
                        reflected_shifts += 1
        
        if total_shifts > 0:
            return (reflected_shifts / total_shifts) * 100
        return 0
    
    def calculate_employee_preference_reflection_rate(self, employee_id, start_date, end_date):
        total_preferred_hours = 0
        reflected_hours = 0
        current_date = start_date
        while current_date <= end_date:
            if employee_id in self.preferences and current_date in self.preferences[employee_id]:
                for pref_start, pref_end in self.preferences[employee_id][current_date]:
                    pref_hours = (pref_end.hour - pref_start.hour)
                    total_preferred_hours += pref_hours
                    
                    if current_date in self.shifts:
                        for shift_name, employees in self.shifts[current_date].items():
                            for emp in employees:
                                if emp['employee']['id'] == employee_id:
                                    overlap_start = max(pref_start.hour, emp['start'])
                                    overlap_end = min(pref_end.hour, emp['end'])
                                    if overlap_end > overlap_start:
                                        reflected_hours += (overlap_end - overlap_start)
            
            current_date += datetime.timedelta(days=1)
        
        if total_preferred_hours > 0:
            return min((reflected_hours / total_preferred_hours) * 100, 100)  # 100%を超えないようにする
        return 0
    
    def calculate_overall_preference_reflection_rate(self, start_date, end_date):
        total_rate = 0
        employee_count = len(self.employees)
        for emp in self.employees:
            total_rate += self.calculate_employee_preference_reflection_rate(emp['id'], start_date, end_date)
        
        if employee_count > 0:
            return total_rate / employee_count
        return 0
    
    def is_employee_preferred_shift(self, employee, date, start_hour, end_hour):
        if employee['id'] in self.preferences and date in self.preferences[employee['id']]:
            for pref_start, pref_end in self.preferences[employee['id']][date]:
                if (pref_start.hour <= start_hour < pref_end.hour) and (pref_start.hour < end_hour <= pref_end.hour):
                    return True
        return False

    def count_consecutive_days(self, employee, date):
        # この関数の実装を追加する必要があります
        return 0  # 仮の実装

    def calculate_weekly_hours(self, employee, date):
        # この関数の実装を追加する必要があります
        return 0  # 仮の実装


    def count_consecutive_days(self, employee, date):
      count = 0
      current_date = date - datetime.timedelta(days=1)
      while current_date in self.shifts and any(emp['employee']['id'] == employee['id'] for shift in self.shifts[current_date].values() for emp in shift):
          count += 1
          current_date -= datetime.timedelta(days=1)
      return count

    def calculate_weekly_hours(self, employee, date):
        hours = 0
        start_of_week = date - datetime.timedelta(days=date.weekday())
        for day in range(7):
            current_date = start_of_week + datetime.timedelta(days=day)
            if current_date in self.shifts:
                for shift in self.shifts[current_date].values():
                    for emp in shift:
                        if emp['employee']['id'] == employee['id']:
                            hours += emp['end'] - emp['start']
        return hours

    MAX_DAILY_HOURS = 8
    MAX_WEEKLY_HOURS = 40
    MAX_CONSECUTIVE_DAYS = 5

    def can_assign_shift(self, employee, date, start_hour, end_hour):
        # 1日の労働時間チェック
        daily_hours = self.calculate_daily_hours(employee, date)
        if daily_hours + (end_hour - start_hour) > self.MAX_DAILY_HOURS:
            return False

        # 週間労働時間チェック
        weekly_hours = self.calculate_weekly_hours(employee, date)
        if weekly_hours + (end_hour - start_hour) > self.MAX_WEEKLY_HOURS:
            return False

        # 連続勤務日数チェック
        consecutive_days = self.count_consecutive_days(employee, date)
        if consecutive_days >= self.MAX_CONSECUTIVE_DAYS:
            return False

        return True

    def calculate_break_after_merge(self, start_hour, end_hour):
        shift_duration = end_hour - start_hour
        if shift_duration > 8:
            return 60
        elif shift_duration > 6:
            return 45
        elif shift_duration > 4:
            return 30
        else:
            return 0

    def calculate_daily_hours(self, employee, date):
        hours = 0
        if date in self.shifts:
            for shift in self.shifts[date].values():
                for emp in shift:
                    if emp['employee']['id'] == employee['id']:
                        hours += emp['end'] - emp['start']
        return hours

    def get_day_preferences(self, date):
        # その日の全ての希望シフトを取得し、重複を除去してソート
        all_preferences = set()
        for employee_id, preferences in self.preferences.items():
            if date in preferences:
                for start, end in preferences[date]:
                    all_preferences.add((start.hour, end.hour))
        return sorted(all_preferences)

    #シフト生成
    def generate_shifts(self, start_date: datetime.date, end_date: datetime.date) -> Dict:
        shortages = defaultdict(lambda: defaultdict(int))
        skill_shortages = defaultdict(lambda: defaultdict(bool))

        for date in (start_date + datetime.timedelta(n) for n in range((end_date - start_date).days + 1)):
            is_holiday = self.check_if_holiday(date)
            day_preferences = self.get_day_preferences(date)

            if not day_preferences:
                day_preferences = [(9, 14), (14, 17), (17, 20)]

            print(f"Date: {date}")
            daily_warnings = defaultdict(set)  # setを使用して重複を排除

            for start_hour, end_hour in day_preferences:
                shift_name = self.get_shift_name(start_hour)
                required_cashiers = self.min_employees[shift_name] + (1 if is_holiday else 0)
                assigned_employees = self.assign_shift(date, shift_name, start_hour, end_hour)

                shortage = max(0, required_cashiers - len(assigned_employees))
                if shortage > 0:
                    shortages[date][shift_name] = shortage
                    daily_warnings[shift_name].add(f"{shortage}人不足")

                has_refrigeration_skill = any('冷蔵' in emp['employee']['skills'] for emp in assigned_employees)
                if not has_refrigeration_skill:
                    skill_shortages[date][shift_name] = True
                    daily_warnings[shift_name].add("冷蔵スキルを持つ従業員が不在")

                print(f"  {shift_name} shift: {len(assigned_employees)} employees assigned")
                for emp in assigned_employees:
                    print(f"    {emp['employee']['name']}: {emp['start']}:00 - {emp['end']}:00 (休憩: {emp['break']}分)")

            # 警告をまとめて表示
            for shift_name, warnings in daily_warnings.items():
                if warnings:
                    print(f"  {shift_name}の警告: {', '.join(warnings)}")
            print()

        return self.shifts, shortages, skill_shortages


    def get_day_of_week(self, date):
        days = ["月", "火", "水", "木", "金", "土", "日"]
        return days[date.weekday()]

    def display_shifts(self, start_date, end_date):
        print("\n生成されたシフト:")
        for date in (start_date + datetime.timedelta(n) for n in range((end_date - start_date).days + 1)):
            if date in self.shifts:
                print(f"\n日付: {date.strftime('%Y-%m-%d')} ({self.get_day_of_week(date)})")

                all_shifts = []
                for shift_name in ['朝', '昼', '夜']:
                    if shift_name in self.shifts[date]:
                        all_shifts.extend(self.shifts[date][shift_name])

                employee_shifts = {}
                for shift in all_shifts:
                    emp_id = shift['employee']['id']
                    if emp_id not in employee_shifts:
                        employee_shifts[emp_id] = []
                    employee_shifts[emp_id].append(shift)

                for emp_id, shifts in employee_shifts.items():
                    emp_name = shifts[0]['employee']['name']
                    print(f"  {emp_name}:")

                    merged_shifts = self.merge_shifts(shifts)
                    for shift in merged_shifts:
                        break_time = self.calculate_break_after_merge(shift['start'], shift['end'])
                        print(f"    {shift['start']:02d}:00 - {shift['end']:02d}:00 (休憩: {break_time}分)")
            else:
                print(f"\n日付: {date.strftime('%Y-%m-%d')} ({self.get_day_of_week(date)}) - シフトなし")           
    
    def merge_shifts(self, shifts):
        if not shifts:
            return []

        merged = []
        shifts.sort(key=lambda x: x['start'])
        current_shift = shifts[0].copy()
        for next_shift in shifts[1:]:
            if next_shift['start'] <= current_shift['end']:
                current_shift['end'] = max(current_shift['end'], next_shift['end'])
            else:
                merged.append(current_shift)
                current_shift = next_shift.copy()
        merged.append(current_shift)

        return merged
    

# クラス定義の最後に以下を追加して、クラスが正しく定義されたことを確認
print("ShiftGenerator class is defined.")
