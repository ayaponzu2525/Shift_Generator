import sqlite3
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
import tensorflow as tf
import numpy as np
import holidays

def read_data_from_sqlite(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM shifts")
    rows = cursor.fetchall()
    
    employees = []
    for row in rows:
        employee_id, name, skills, desired_date, clock_in, clock_out = row
        skills = skills.split(',') if skills else []
        employees.append({
            'id': employee_id,
            'name': name,
            'skills': skills,
            'desired_date': desired_date,
            'clock_in': clock_in,
            'clock_out': clock_out
        })
    
    conn.close()
    return employees

class Employee:
    def __init__(self, id, name, skills, desired_date, clock_in, clock_out):
        self.id = id
        self.name = name
        self.skills = skills
        self.register_skill = 'レジ' in skills
        self.refrigeration_skill = '冷蔵' in skills
        self.stocking_skill = '品出し' in skills
        self.preferences = {}
        if desired_date and clock_in and clock_out:
            self.preferences[datetime.strptime(desired_date, '%Y-%m-%d').date()] = (
                datetime.strptime(clock_in, '%H:%M').time(),
                datetime.strptime(clock_out, '%H:%M').time()
            )

class Shift:
    def __init__(self, employee, start_time, end_time):
        self.employee = employee
        self.start_time = start_time
        self.end_time = end_time

class ShiftAI:
    def __init__(self, employees, shifts, constraints, historical_data):
        self.employees = employees
        self.shifts = shifts
        self.constraints = constraints
        self.historical_data = historical_data
        self.jp_holidays = holidays.JP()
        self.model = self.build_ml_model()
        self.train_model()

    def build_ml_model(self):
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(128, activation='relu', input_shape=(len(self.employees) * 5 + 7,)),
            tf.keras.layers.Dense(256, activation='relu'),
            tf.keras.layers.Dense(len(self.shifts) * len(self.employees), activation='sigmoid')
        ])
        model.compile(optimizer='adam', loss='binary_crossentropy')
        return model

    def train_model(self):
        X, y = self.prepare_training_data()
        self.model.fit(X, y, epochs=100, batch_size=32, validation_split=0.2)

    def prepare_training_data(self):
        X, y = [], []
        for date, shifts in self.historical_data.items():
            X.append(self.prepare_input_data(date))
            y.append(self.encode_shifts(shifts))
        return np.array(X), np.array(y)

    def prepare_input_data(self, date):
        data = []
        for employee in self.employees:
            data.extend([
                int(employee.register_skill),
                int(employee.refrigeration_skill),
                int(employee.stocking_skill),
                1 if date in employee.preferences else 0,
                employee.preferences.get(date, (datetime.min.time(), datetime.min.time()))[0].hour if date in employee.preferences else 0
            ])
        data.extend([date.weekday()] + [int(date in self.jp_holidays)])
        return np.array(data)

    def encode_shifts(self, shifts):
        encoded = np.zeros(len(self.shifts) * len(self.employees))
        for i, employee in enumerate(self.employees):
            for j, shift in enumerate(self.shifts):
                if any(s.employee.id == employee.id and s.start_time == shift[0] for s in shifts):
                    encoded[i * len(self.shifts) + j] = 1
        return encoded

    def generate_shifts(self, date):
        input_data = self.prepare_input_data(date)
        predictions = self.model.predict(input_data.reshape(1, -1))[0]
        initial_shifts = self.decode_predictions(predictions)
        return self.optimize_shifts(date, initial_shifts)

    def decode_predictions(self, predictions):
        shifts = {}
        for i, employee in enumerate(self.employees):
            shifts[employee.id] = {}
            for j, shift in enumerate(self.shifts):
                shifts[employee.id][shift] = predictions[i * len(self.shifts) + j] > 0.5
        return shifts

    def optimize_shifts(self, date, initial_shifts):
        model = cp_model.CpModel()
        
        shifts = {}
        for e in self.employees:
            for s in self.shifts:
                shifts[(e.id, s)] = model.NewBoolVar(f'shift_e{e.id}_s{s[0].strftime("%H%M")}')

        self.add_constraints(model, shifts, date)

        preference_vars = []
        for e in self.employees:
            if date in e.preferences:
                desired_start, desired_end = e.preferences[date]
                for s in self.shifts:
                    if self.shift_overlaps(s, desired_start, desired_end):
                        preference_vars.append(shifts[(e.id, s)])

        model.Maximize(sum(preference_vars))

        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            return self.extract_solution(solver, shifts)
        else:
            return self.heuristic_adjustment(initial_shifts, date)

    def add_constraints(self, model, shifts, date):
        # 各シフトの必要人数を満たす制約
        for s in self.shifts:
            model.Add(sum(shifts[(e.id, s)] for e in self.employees) == self.constraints['required_staff'])

        # 各従業員は最大1シフトまで
        for e in self.employees:
            model.Add(sum(shifts[(e.id, s)] for s in self.shifts) <= 1)

        # スキルに基づく制約（例：各シフトに少なくとも1人のレジ係）
        for s in self.shifts:
            model.Add(sum(shifts[(e.id, s)] for e in self.employees if e.register_skill) >= 1)

    def heuristic_adjustment(self, shifts, date):
        # 簡単なヒューリスティック調整の例
        adjusted_shifts = shifts.copy()
        for e in self.employees:
            if date in e.preferences:
                desired_start, desired_end = e.preferences[date]
                for s in self.shifts:
                    if self.shift_overlaps(s, desired_start, desired_end):
                        adjusted_shifts[e.id][s] = True
                        break
        return adjusted_shifts

    def shift_overlaps(self, shift, start, end):
        return shift[0] <= start < shift[1] or start <= shift[0] < end

    def extract_solution(self, solver, shifts):
        solution = {}
        for e in self.employees:
            solution[e.id] = {}
            for s in self.shifts:
                solution[e.id][s] = solver.Value(shifts[(e.id, s)]) == 1
        return solution

    def get_historical_data(db_file):
        conn = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()
        
        historical_data = {}
        
        cursor.execute("""
        SELECT desired_date, employee_id, name, skills, clock_in, clock_out
        FROM shifts
        WHERE clock_in IS NOT NULL AND clock_out IS NOT NULL
        ORDER BY desired_date
        """)
        
        rows = cursor.fetchall()
        
        for row in rows:
            desired_date, employee_id, name, skills, clock_in, clock_out = row
            
            if desired_date not in historical_data:
                historical_data[desired_date] = []
            
            skills_list = skills.split(',') if skills else []
            
            employee = Employee(id=employee_id, name=name, skills=skills_list, desired_date=None, clock_in=None, clock_out=None)
            
            shift = Shift(
                employee=employee,
                start_time=datetime.strptime(clock_in, '%H:%M').time(),
                end_time=datetime.strptime(clock_out, '%H:%M').time()
            )
            
            historical_data[desired_date].append(shift)
        
        conn.close()
    
        return historical_data

# メイン関数内で以下のように使用
def main():
    db_file = 'shiftlist.db'
    employee_data = read_data_from_sqlite(db_file)
    employees = [Employee(**emp) for emp in employee_data]
    
    shifts = [
        (datetime.strptime("09:00", "%H:%M").time(), datetime.strptime("14:00", "%H:%M").time()),
        (datetime.strptime("14:00", "%H:%M").time(), datetime.strptime("20:00", "%H:%M").time())
    ]
    
    constraints = {
        'required_staff': 2
    }

    historical_data = ShiftAI.get_historical_data(db_file)
    
    # ... 以下は変更なし

    shift_ai = ShiftAI(employees, shifts, constraints, historical_data)
    
    target_date = datetime(2024, 8, 5).date()
    generated_shifts = shift_ai.generate_shifts(target_date)
    
    print(f"Generated shifts for {target_date}:")
    for employee_id, shift_assignment in generated_shifts.items():
        employee = next(e for e in employees if e.id == employee_id)
        for shift, assigned in shift_assignment.items():
            if assigned:
                print(f"{employee.name} assigned to shift {shift[0].strftime('%H:%M')} - {shift[1].strftime('%H:%M')}")

if __name__ == "__main__":
    main()
