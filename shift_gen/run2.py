from shift_generator2 import ShiftGenerator
import datetime

# ShiftGeneratorのインスタンスを作成
shift_generator = ShiftGenerator('shift.csv')

# シフトを生成する期間を設定
start_date = datetime.date(2024, 7, 1)  # 2024年7月1日から
end_date = datetime.date(2024, 7, 1)    # 2024年7月7日まで（1週間分）

# シフトを生成
generated_shifts, shortages, skill_shortages = shift_generator.generate_shifts(start_date, end_date)

# 従業員のスキル情報を表示
shift_generator.display_employee_skills()

# 生成されたシフトを表示
print("生成されたシフト:")
shift_generator.display_shifts(start_date, end_date)

# 人員不足情報を表示
print("\n人員不足情報:")
for date, shifts in shortages.items():
    for shift_name, shortage in shifts.items():
        if shortage > 0:
            print(f"{date} {shift_name}: {shortage}人不足")
        else:
            print("なし")

# スキル不足情報を表示
print("\nスキル不足情報:")
for date, skills in skill_shortages.items():
    for skill_name, shortage in skills.items():
        if shortage > 0:
            print(f"{date} {skill_name}: {shortage}人不足")
        else:
            print("なし")

# 全体のシフト希望反映率を計算して表示
overall_reflection_rate = shift_generator.calculate_overall_preference_reflection_rate(start_date, end_date)
print(f"\n全体のシフト希望反映率: {overall_reflection_rate:.2f}%")

# 各従業員のシフト希望反映率を表示
print("\n各従業員のシフト希望反映率:")
for employee in shift_generator.employees:
    emp_reflection_rate = shift_generator.calculate_employee_preference_reflection_rate(employee.id, start_date, end_date)
    print(f"{employee.name}: {emp_reflection_rate:.2f}%")