import pandas as pd

# Tạo file Excel mẫu
sample_data = {
    'student_id': ['HE123456', 'HE123457', 'HE123458'],
    'name': ['Nguyễn Văn A', 'Trần Thị B', 'Lê Văn C'],
    'class': ['IT01', 'IT02', 'IT01'],
    'major': ['Công nghệ thông tin', 'Công nghệ thông tin', 'Công nghệ thông tin']
}

df = pd.DataFrame(sample_data)
df.to_excel('students_sample.xlsx', index=False)

print("✅ Đã tạo file mẫu students_sample.xlsx")
print("📋 Cấu trúc file Excel:")
print("- student_id: Mã sinh viên")
print("- name: Tên sinh viên")
print("- class: Lớp")
print("- major: Chuyên ngành")
