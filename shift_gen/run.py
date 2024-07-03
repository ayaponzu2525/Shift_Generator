from shift_generator import ShiftGenerator
import datetime

# ShiftGeneratorのインスタンスを作成
shift_generator = ShiftGenerator('shift_gen\shift.csv')

# シフト希望反映率を表示
shift_generator.display_preference_rates()

# シフト希望反映率を変更（例）
shift_generator.set_preference_rate(1, 100)  # 従業員ID 1の反映率を100%に設定
shift_generator.set_preference_rate(2, 0)   # 従業員ID 2の反映率を0%に設定
# シフトを生成する期間を設定
start_date = datetime.date(2024, 7, 1)  # 2024年7月1日から
end_date = datetime.date(2024, 7, 1)   # 2024年7月1日まで

# シフトを生成
generated_shifts, shortages, skill_shortages = shift_generator.generate_shifts(start_date, end_date)

# 生成されたシフトを表示
shift_generator.display_shifts(start_date, end_date)

# 不足状況の総括を表示
total_shortages = sum(sum(shifts.values()) for shifts in shortages.values())
if total_shortages > 0:
    print(f"\n全期間で合計{total_shortages}人のシフト不足があります。")
    print("各日の不足状況:")
    for date, shifts in shortages.items():
        for shift_name, shortage in shifts.items():
            print(f"  {date} {shift_name}: {shortage}人不足")
else:
    print("\nすべてのシフトが必要人数を満たしています。")

# 全体のシフト希望反映率を計算して表示
overall_reflection_rate = shift_generator.calculate_overall_preference_reflection_rate(start_date, end_date)
print(f"\n全体のシフト希望反映率: {overall_reflection_rate:.2f}%")

# 各従業員のシフト希望反映率を表示
print("\n各従業員のシフト希望反映率:")
for emp in shift_generator.employees:
    emp_reflection_rate = shift_generator.calculate_employee_preference_reflection_rate(emp['id'], start_date, end_date)
    print(f"{emp['name']}: {emp_reflection_rate:.2f}%")