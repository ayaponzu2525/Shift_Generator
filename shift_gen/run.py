from shift_generator import ShiftGenerator

import datetime

# ShiftGeneratorのインスタンスを作成
shift_generator = ShiftGenerator('shift_id.csv', 'shift_kibou.csv')

# シフトを生成する期間を設定
start_date = datetime.date(2024, 7, 1)  # 2024年7月1日から
end_date = datetime.date(2024, 7, 1)   # 2024年7月1日まで

# シフトを生成
generated_shifts, shortages = shift_generator.generate_shifts(start_date, end_date)

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