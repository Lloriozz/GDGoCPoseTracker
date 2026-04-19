# Codex Wiki Ingest Workflow

Quy trình này dùng cho fitness LLM wiki trong backend.
Mục tiêu là: bạn chỉ cần thả source thô vào `knowledge/raw/`, sau đó dùng Codex để tự đọc, phân loại, tổ chức và liên kết kiến thức trong `knowledge/wiki/`.

## 1. Chuẩn bị source

Đặt file vào:

- [knowledge/raw]

Bạn có thể thả vào đây:

- PDF
- markdown
- text notes
- transcript
- bài báo web đã convert sang markdown

### Gợi ý đặt tên file

Ưu tiên tên ngắn, rõ nghĩa, dễ đọc:

- `vietnamese-budget-meals.md`
- `intermittent-fasting-basics.pdf`
- `protein-for-vegetarians.md`
- `knee-friendly-training-guide.pdf`

Tránh tên kiểu:

- `document(7).pdf`
- `new file final final.pdf`

## 2. Mở Codex ở đúng folder

Mở Codex tại:

- [backend]

Lý do:

- Codex sẽ đọc [AGENTS.md]
- Codex sẽ dùng rule trong [CODEX_WIKI.md]

## 3. Prompt ingest chuẩn

### Ingest tất cả source mới trong inbox

```text
Ingest all new sources under knowledge/raw and update the wiki.
Follow knowledge/schema/CODEX_WIKI.md exactly.
Do not modify anything under knowledge/raw.
Classify each source into the appropriate knowledge areas yourself.
Update knowledge/wiki/index.md and append a concise entry to knowledge/logs/ingest-log.md.
```

### Ingest một file cụ thể

```text
Ingest knowledge/raw/your-file-name.pdf and update the wiki.
Follow knowledge/schema/CODEX_WIKI.md exactly.
Do not modify anything under knowledge/raw.
Classify the source into the appropriate wiki sections and update links, index, and ingest log.
```

### Ingest một batch nhỏ rồi tóm tắt thay đổi

```text
Ingest all new sources under knowledge/raw and update the wiki.
Follow knowledge/schema/CODEX_WIKI.md exactly.
Do not modify anything under knowledge/raw.
Classify each source into the right wiki sections, create or update pages, update knowledge/wiki/index.md, and append to knowledge/logs/ingest-log.md.
At the end, summarize:
1. which raw sources were ingested
2. which wiki pages were created
3. which wiki pages were updated
4. any contradictions or weak claims you found
```

## 4. Codex nên làm gì sau prompt ingest

Khi chạy đúng workflow, Codex nên:

1. đọc source trong `knowledge/raw/`
2. tự phân loại source theo topic
3. tạo page mới hoặc cập nhật page cũ trong `knowledge/wiki/`
4. thêm wiki links `[[...]]`
5. cập nhật [knowledge/wiki/index.md]
6. thêm log vào [knowledge/logs/ingest-log.md]
7. giữ nguyên hoàn toàn `knowledge/raw/`

## 5. Sau khi ingest, kiểm tra ở đâu

Mở và kiểm tra:

- [knowledge/wiki/index.md]
- [knowledge/logs/ingest-log.md]
- [knowledge/wiki]
Bạn nên xem:
- page nào mới được tạo
- page nào được cập nhật
- liên kết giữa các page có hợp lý không
- có claim nào bị đánh dấu mâu thuẫn hay cần verification không

## 6. Prompt lint chuẩn

Sau khi ingest vài source, chạy lint:

```text
Lint the wiki under knowledge/wiki.
Follow knowledge/schema/CODEX_WIKI.md exactly.
Check for contradictions, orphan pages, weak linking, overlapping concepts, outdated claims, and weak citations.
Append the report to knowledge/logs/lint-report.md.
Then summarize the highest-priority fixes.
```

## 7. Prompt hỏi đáp dựa trên wiki

Khi bạn muốn Codex trả lời từ wiki thay vì raw source:

```text
Answer this question using the wiki first, not the raw sources unless needed:
[your question here]

Start from knowledge/wiki/index.md, then read the most relevant pages.
If the wiki is missing important knowledge, say so clearly and suggest what should be ingested next.
```

## 8. Prompt để buộc Codex fold câu trả lời ngược vào wiki

Nếu một câu trả lời có giá trị dài hạn, dùng prompt này:

```text
Answer the question using the wiki.
If the answer adds lasting value to the knowledge base, update the relevant wiki pages and append a note to knowledge/logs/ingest-log.md describing what was added.
Do not modify anything under knowledge/raw.
```

## 9. Quy trình thực tế nên dùng

### Vòng làm việc nhẹ

1. thêm 1-3 source mới vào `knowledge/raw/`
2. chạy prompt ingest
3. mở wiki xem các page mới
4. chạy prompt lint
5. sửa source hoặc thêm source mới nếu cần

## 10. Không nên làm

- nhét hàng chục file rất khác nhau trong một lượt đầu tiên
- ingest quá nhiều source khi taxonomy còn chưa ổn
- coi raw source như nơi để Codex chỉnh sửa
- dùng wiki để thay tool tính số

## 11. Checklist nhanh trước mỗi lượt ingest

- file đã nằm trong `knowledge/raw/` chưa
- tên file đã dễ hiểu chưa
- source có đúng scope fitness/nutrition không
- batch có quá nhiều không

