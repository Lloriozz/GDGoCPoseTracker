# Report: Model Training, Optimization & Experiments — GDGoC Pose Tracker

## 1. Tổng quan hệ thống

Pipeline thu thập và phân loại pose được xây dựng hoàn toàn dựa trên **MediaPipe Pose** để trích xuất tọa độ khung xương, sau đó huấn luyện classifier riêng biệt cho từng bài tập. Mỗi frame video được trích xuất các landmark quan trọng dưới dạng vector đặc trưng `(x, y, z, visibility)` cho mỗi khớp, sau đó chuẩn hóa qua **StandardScaler** trước khi đưa vào model.

**Hai hướng tiếp cận** được thử nghiệm song song cho mọi bài tập:
- **Scikit-learn classifiers**: LR, SVC, KNN, DTC, RF, SGDC, NB (và Ridge cho Lunge)
- **Keras/TensorFlow Deep Learning**: MLP với 3, 5, 7 lớp; có/không có Dropout — hyperparameter tuned bằng **Keras Tuner (Hyperband)**

**Phương pháp phát hiện lỗi đơn giản** (không cần ML): dùng công thức tính góc `arctan2` và khoảng cách Euclidean giữa các khớp để ngưỡng hóa trực tiếp.

---

## 2. Bicep Curl

### Dữ liệu

| Tập | Số mẫu | Nhãn |
|-----|--------|------|
| Train | 15,372 | C: 8,238 / L: 7,134 |
| Test | 604 | C: 339 / L: 265 |

- **9 landmarks**: Nose, L/R Shoulder, L/R Elbow, L/R Wrist, L/R Hip → **36 features**
- Nhãn `C` = correct posture, `L` = lean too far back
- 2 lỗi còn lại (loose upper arm, weak peak contraction) phát hiện bằng **angle threshold** (>40° và >60°)

### Kết quả thử nghiệm (test set)

| Rank | Model | Accuracy | F1 |
|------|-------|----------|----|
| 🥇 | KNN | 97.19% | 0.9712 |
| 🥈 | Deep 7-layers | 96.69% | 0.9661 |
| 🥉 | Deep 5-layers | 95.53% | 0.9540 |
| 4 | SVC | 93.21% | 0.9314 |
| 5 | RF | 93.38% | 0.9313 |

Deep Learning (3–7 layers) tuy đạt `val_accuracy` ~99.8% trên train set, nhưng **generalization kém hơn KNN** trên test set (F1 0.966 vs 0.971). KNN được chọn làm model triển khai.

**Cấu trúc các DL models** (best HP từ Hyperband):

| Model | Kiến trúc | Learning rate |
|-------|-----------|---------------|
| `3_layers` | 36→448(tanh)→2 | 0.001 |
| `5_layers` | 36→160→352→64→2(relu) | 0.001 |
| `7_layers_with_dropout` | 36→320→Dropout(0.3)→96→Dropout(0.3)→448→2(relu) | 0.001 |
| `7_layers` | 36→192→320→448→224→448→2(tanh) | 0.0001 |

---

## 3. Squat

### Dữ liệu

| Tập | Số mẫu | Nhãn |
|-----|--------|------|
| Train | 4,160 | down: 2,127 / up: 2,033 |
| Test | 853 | down: 430 / up: 423 |

- **9 landmarks**: Nose, L/R Shoulder, L/R Hip, L/R Knee, L/R Ankle → **36 features**
- Nhiệm vụ: **stage detection** (up/down) — tiền đề cho đếm rep và phát hiện lỗi
- Lỗi feet placement và knee placement phát hiện bằng **ratio distance** (không dùng ML)

### Kết quả (test set)

| Rank | Model | Accuracy | F1 |
|------|-------|----------|----|
| 🥇 | LR | 99.41% | 0.9941 |
| 🥈 | SGDC | 99.30% | 0.9930 |
| 🥉 | KNN | 98.48% | 0.9848 |
| 4 | SVC | 97.66% | 0.9765 |
| ❌ | DTC / NB / RF | ~50% | 0.338 |

DTC, NB, RF **hoàn toàn thất bại** trên test set (dự đoán toàn bộ một lớp), cho thấy chúng overfit train set. **LR** được chọn, và ROC analysis xác định ngưỡng tối ưu ở `threshold ≈ 0.542`.

---

## 4. Plank

### Dữ liệu

| Tập | Số mẫu | Nhãn |
|-----|--------|------|
| Train | 28,520 (+Kaggle) | C: 9,904 / L: 9,546 / H: 9,070 |
| Test | 710 | H: 241 / L: 235 / C: 234 |

- **17 landmarks** (toàn bộ thân từ mũi đến ngón chân) → **68 features**
- 3 nhãn: `C` = correct, `H` = high lower back, `L` = low lower back
- Dữ liệu train bổ sung từ **Kaggle dataset** (`kaggle.csv`)

### Kết quả (test set)

| Rank | Model | Accuracy | F1 (trung bình) |
|------|-------|----------|----------------|
| 🥇 | LR | 99.58% | 0.9958 |
| 🥈 | Deep 7-layers + Dropout | 99.44% | 0.9944 |
| 🥉 | SVC | 98.73% | 0.9874 |
| 4 | SGDC | 98.17% | 0.9817 |
| 5 | KNN | 94.93% | 0.9493 |

**LR** vượt trội rõ ràng, kể cả so với các mạng Deep Learning. Đây là bài tập duy nhất mà LR lấy vị trí #1 tuyệt đối với accuracy **99.58%** — có thể do phân tách tuyến tính tốt trong không gian 68 features.

---

## 5. Lunge

### Dữ liệu (2 task riêng biệt)

**Stage Detection (I/M/D)**:

| Tập | Số mẫu | Nhãn |
|-----|--------|------|
| Train | 24,244 | D: 8,232 / M: 8,148 / I: 7,864 |
| Test | 1,205 | D: 416 / I: 402 / M: 387 |

**Error Detection — Knee Over Toe (C/L)**:

| Tập | Số mẫu | Nhãn |
|-----|--------|------|
| Train | ~24,000 | C / L (balanced) |
| Test | 1,107 | C: 576 / L: 531 |

- **13 landmarks** (thêm L/R Heel, L/R Foot Index) → **52 features**
- Lỗi góc knee (knee angle 60°–135°) phát hiện bằng **angle threshold** với phân tích đồ thị trực quan
- Lỗi **knee over toe** phức tạp hơn → dùng ML

### Stage Detection (test set)

| Rank | Model | Accuracy |
|------|-------|----------|
| 🥇 | Ridge | 95.10% |
| 🥈 | SVC | 95.19% |
| 🥉 | LR | 94.85% |

> Lưu ý: trên **train set**, KNN đạt 99.5% nhưng tụt xuống 91.5% trên test set — overfit rõ ràng. Ridge/SVC/LR generalize tốt hơn nhiều.

### Error Detection (test set)

| Rank | Model | Accuracy | F1 |
|------|-------|----------|----|
| 🥇 | LR | 97.20% | 0.9720 |
| 🥈 | SGDC | 95.75% | 0.9575 |
| 🥉 | DNN 3-layers | 92.77% | 0.9274 |
| 4 | DTC | 91.69% | 0.9167 |

Deep Learning (7 layers + dropout) chỉ đạt **86.4%** — thấp hơn cả DTC. **LR** một lần nữa giành top.

---

## 6. Tổng hợp: Model được chọn để triển khai

| Bài tập | Task | Model được chọn | Accuracy (test) | Ghi chú |
|---------|------|----------------|----------------|---------|
| Bicep Curl | Posture (lean-back) | **KNN** | 97.19% | sklearn → CoreML Pipeline |
| Squat | Stage (up/down) | **LR** | 99.41% | sklearn → CoreML Pipeline |
| Lunge | Stage (I/M/D) | **LR (OvR)** | ~95% | Retrain OvR vì coremltools không hỗ trợ multinomial |
| Lunge | Error (knee-over-toe) | **LR (OvR)** | 97.20% | Retrain OvR |
| Plank | Posture (C/L/H) | **LR (OvR)** | 99.58% | Retrain OvR |

---

## 7. Tối ưu hóa & Export CoreML

**Vấn đề phát sinh khi export**: `coremltools` chỉ hỗ trợ `LogisticRegression` với `multi_class='ovr'`, trong khi các model gốc dùng `multi_class='auto'` (multinomial với lbfgs). Giải pháp: **retrain lại với OvR** trực tiếp từ file CSV gốc — độ chính xác tương đương (~99%).

**Pipeline export** (`export_coreml.py`):

1. Tải scaler và model từ `.pkl`
2. Wrap thành `sklearn.Pipeline([("scaler", scaler), ("clf", model)])`
3. Convert qua `ct.converters.sklearn.convert()` với `input_features = Array(n_features)`
4. Scaler được **baked vào CoreML pipeline** → app truyền raw MediaPipe coordinates trực tiếp mà không cần pre-process

**5 `.mlpackage` output**:

| File | Model | Features | Labels |
|------|-------|----------|--------|
| `bicep_posture.mlpackage` | KNN | 36 | C / L |
| `squat_stage.mlpackage` | LR | 36 | down / up |
| `lunge_stage.mlpackage` | LR (OvR) | 52 | I / M / D |
| `lunge_error.mlpackage` | LR (OvR) | 52 | C / L |
| `plank_posture.mlpackage` | LR (OvR) | 68 | C / L / H |

---

## 8. Kết luận & Nhận xét

- **Scikit-learn classifiers** (đặc biệt LR và KNN) **vượt trội** hoặc ngang bằng Deep Learning cho bài toán này, trong khi đơn giản hơn nhiều và nhẹ hơn đáng kể cho on-device inference.
- **Deep Learning** bị overfit rõ ràng ở Bicep và Lunge mặc dù đã dùng Dropout và EarlyStopping; lợi ích chính của Hyperband là tự động tìm số units và learning rate tối ưu.
- **Phương pháp hybrid**: kết hợp rule-based (angle/distance threshold) cho các lỗi đơn giản + ML cho các lỗi phức tạp giúp giảm số lượng model cần huấn luyện và inference overhead.
- **Generalization gap** rõ nhất ở Lunge stage (KNN train 99.5% → test 91.5%) và Bicep DL models (train ~99.8% → test ~96%), nhấn mạnh tầm quan trọng của test set độc lập.
