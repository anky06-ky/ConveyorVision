# Contributing to ConveyorVision

Cảm ơn bạn quan tâm đóng góp cho ConveyorVision! Tài liệu này hướng dẫn cách đóng góp code, báo cáo lỗi, và cải thiện project.

## 📋 Mục lục

- [Code of Conduct](#code-of-conduct)
- [Báo cáo lỗi](#báo-cáo-lỗi)
- [Đóng góp code](#đóng-góp-code)
- [Môi trường phát triển](#môi-trường-phát-triển)
- [Chuẩn code](#chuẩn-code)
- [Testing](#testing)

## Code of Conduct

Project này tuân thủ [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/0/code_of-conduct/). Bằng cách tham gia, bạn dự kiến sẽ giữ mã này.

## Báo cáo lỗi

Nếu phát hiện lỗi, hãy tạo issue mới với các thông tin sau:

1. **Tiêu đề rõ ràng**: Mô tả ngắn gọn vấn đề
2. **Môi trường**: OS, Python version, package versions
3. **Bước tái hiện**: Liệt kê chi tiết các bước
4. **Kết quả mong đợi**: Điều gì sẽ xảy ra nếu không có lỗi
5. **Kết quả thực tế**: Điều gì đã xảy ra
6. **Screenshots/Logs**: Nếu có thể

## Đóng góp code

### Quy trình Pull Request

1. **Fork repository** và clone về local
2. **Tạo branch mới** từ `develop`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Viết code** và đảm bảo có test
4. **Chạy tests**: `pytest tests/ -v`
5. **Commit** với message rõ ràng:
   ```bash
   git commit -m "feat: thêm tính năng X"
   git commit -m "fix: sửa lỗi Y"
   ```
6. **Push** lên fork của bạn:
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Tạo Pull Request** tới branch `develop`

### Loại commit

- `feat`: Tính năng mới
- `fix`: Sửa lỗi
- `docs`: Cập nhật documentation
- `style`: Định dạng code (không ảnh hưởng logic)
- `refactor`: Tái cấu trúc code
- `test`: Thêm/sửa tests
- `chore`: Tasks bảo trì

## Môi trường phát triển

### Cài đặt

```bash
# Clone repository
git clone https://github.com/anky06-ky/ConveyorVision.git
cd ConveyorVision

# Tạo virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Cài đặt dependencies
pip install -r requirements.txt

# Cài đặt dev dependencies
pip install -e ".[dev]"
```

### Cấu hình Environment Variables

1. Copy `.env.example` thành `.env`:
   ```bash
   cp .env.example .env
   ```

2. Cập nhật các biến cần thiết trong `.env`

## Chuẩn code

### Python Style Guide

- Tuân thủ [PEP 8](https://peps.python.org/pep-0008/)
- Sử dụng **type hints** cho function signatures
- Viết **docstrings** cho tất cả public functions/classes
- Line length tối đa: **100 ký tự**

### Formatting

Sử dụng **Black** để format code:

```bash
black src/ tests/
```

### Linting

Chạy **Flake8** để kiểm tra:

```bash
flake8 src/ tests/ --max-line-length=100
```

### Type Checking

Sử dụng **MyPy**:

```bash
mypy src/conveyorvision --ignore-missing-imports
```

## Testing

### Chạy tests

```bash
# Chạy tất cả tests
pytest tests/ -v

# Chạy với coverage
pytest tests/ -v --cov=conveyorvision --cov-report=html

# Chạy test cụ thể
pytest tests/test_pipeline.py -v -k test_data_yaml
```

### Viết tests

- Đặt test files trong thư mục `tests/`
- Đặt tên file: `test_*.py`
- Đặt tên function: `test_*`
- Sử dụng pytest fixtures khi cần
- Mỗi test nên độc lập, không phụ thuộc vào test khác

### Cấu trúc test

```python
def test_feature_name():
    """Mô tả ngắn gọn điều được test."""
    # Arrange: Chuẩn bị dữ liệu
    data = {"key": "value"}
    
    # Act: Thực hiện hành động
    result = function_under_test(data)
    
    # Assert: Kiểm tra kết quả
    assert result == expected_value
```

## Cảm ơn

Mọi đóng góp đều được đánh giá cao! Nếu có câu hỏi, hãy tạo issue hoặc liên hệ qua email.

---

Made with ❤️ by ConveyorVision Team
