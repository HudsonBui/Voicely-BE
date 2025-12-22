# Luồng hoạt động Chatbot Completion API

## Tổng quan
Endpoint: `POST /chatbot-ai/completion`

Đây là endpoint chính để xử lý các yêu cầu chat từ người dùng. Hệ thống sẽ đi qua nhiều giai đoạn xử lý để trả về câu trả lời phù hợp nhất.

---

## Input Request
```json
{
  "code": "chatbot_code",           // Mã chatbot (bắt buộc)
  "customer_code": "customer_code", // Mã khách hàng (tùy chọn, mặc định: 'anonymous')
  "platform_type": "web/mobile",    // Loại nền tảng (tùy chọn)
  "messages": [                      // Danh sách tin nhắn (bắt buộc)
    {
      "role": "user",
      "content": "Câu hỏi của người dùng"
    }
  ]
}
```

---

## Luồng xử lý chi tiết

### **GIAI ĐOẠN 1: VALIDATE INPUT & SECURITY**
📍 **File**: `chatbot_controller.py` → `chat_gpt_service_.py::main_chatbot()`

1. **Kiểm tra xác thực** (`@require_secret_key_system`)
   - Xác thực secret key
   - Lấy company_id từ request

2. **Validate dữ liệu đầu vào**
   - Kiểm tra JSON hợp lệ
   - Validate `code` (chatbot_code)
   - Validate `messages` không rỗng
   - Kiểm tra `content` trong message cuối cùng

---

### **GIAI ĐOẠN 2: SETUP & INITIALIZATION**
📍 **File**: `chat_gpt_service_.py::main_flow_processing()`

1. **Xác minh chatbot** (`chatbot_verification`)
   - Kiểm tra chatbot tồn tại và đang hoạt động
   - Tạo `chatbot_key = {schema_name}_{chatbot_code}`

2. **Setup cấu hình** (`setup_chatbot_and_customer_code`)
   - Lấy thông tin chatbot từ database:
     - `script_id`: ID kịch bản
     - `answer_default`: Câu trả lời mặc định
     - `enable_auto_reply`: Bật/tắt tự động trả lời
     - `enable_multilingual`: Bật/tắt đa ngôn ngữ
     - `chatbot_id`: ID của chatbot
   - Xử lý customer_code (mặc định: 'anonymous')

3. **Khởi tạo History Record**
   - Tạo `history_id` mới (UUID)
   - Chuẩn bị object `history`:
     ```python
     {
       'id': new_history_id,
       'customer_code': customer_code,
       'platform_type': platform_type,
       'chatbot_code': chatbot_code,
       'company_id': company_id,
       'message_receive': prompt,
       'message_response': "",
       'normalized_message_receive': None,
       'flow_response': "",
       'language': None,
       'detail_id': None
     }
     ```

4. **Xử lý ngôn ngữ** (`multilingual_processing`)
   - Phát hiện ngôn ngữ của tin nhắn
   - Cập nhật `language` vào history

---

### **GIAI ĐOẠN 3: KIỂM TRA GIỚI HẠN TOKEN**

1. **Kiểm tra token limit cấp Company**
   - Query tổng token đã sử dụng của toàn công ty
   - So sánh với `company.token_limit`
   - Nếu vượt → Trả về lỗi 429 (TOKEN_LIMIT_EXCEEDED)

2. **Kiểm tra token limit cấp Chatbot**
   - Query tổng token đã sử dụng của chatbot
   - So sánh với `chatbot_ai.token_limit`
   - Nếu vượt → Trả về lỗi 429 (TOKEN_LIMIT_EXCEEDED)

---

### **GIAI ĐOẠN 4: XỬ LÝ PIPELINE (5 STAGES)**

#### **Stage 1: Kiểm tra số điện thoại** 🔢
📍 **Function**: `_process_phone_number()`

- Kiểm tra xem tin nhắn có chứa số điện thoại hợp lệ không
- Nếu có → Validate và lưu thông tin
- Ghi nhận token sử dụng
- **Nếu match → Dừng pipeline, trả về kết quả**

---

#### **Stage 2: Kiểm tra từ đặc biệt** ⭐
📍 **Function**: `specialWordsCase()`

- Kiểm tra tin nhắn có chứa từ đặc biệt (special words) không
- Ví dụ: "ok", "chốt", "tks", "cảm ơn"...
- **Nếu match → Dừng pipeline, trả về câu trả lời tương ứng**

---

#### **Stage 3: Lấy lịch sử hội thoại & Normalize câu hỏi** 💬
📍 **Function**: `_get_conversation_history()` + `_process_question()`

1. **Lấy lịch sử hội thoại**
   - Query N tin nhắn gần nhất của customer (theo `NUMBER_MESSAGES`)
   - Format thành messages với role:
     ```python
     [
       {"role": "user", "content": "..."},
       {"role": "assistant", "content": "..."},
       ...
       {"role": "user", "content": "câu hỏi hiện tại"}
     ]
     ```

2. **Normalize câu hỏi** (sử dụng GPT)
   - Gọi API GPT với `chat_gpt_handle_question()`
   - Chuẩn hóa câu hỏi dựa trên:
     - Ngữ cảnh hội thoại
     - Strongfield (lĩnh vực mạnh của chatbot)
   - Lưu kết quả vào `history['normalized_message_receive']`
   - Ghi nhận token sử dụng

---

#### **Stage 4A: Rule-based Processing (nếu bật)** 📋
📍 **Function**: `_process_rule_based()` → `ruleBasedProcessing()`

**Điều kiện**: `keyword_dict[chatbot_key]['rule_based_toggle'] == True`

- Tìm kiếm câu trả lời dựa trên quy tắc cứng
- So khớp normalized question với dữ liệu trong database
- **Nếu tìm thấy → Dừng pipeline, trả về câu trả lời**
- Ghi nhận token sử dụng

---

#### **Stage 4B: Database/Third-party Processing (nếu không dùng rule-based)** 🗄️
📍 **Function**: `_process_db_based()` → `DatabaseBasedProcessing()` hoặc `ThirdPartyDatabaseBasedProcessing()`

**Điều kiện**: `rule_based_toggle == False`

1. **Nếu có third-party integration**:
   - Gọi third-party database (external API)
   - Xử lý với provider đã cấu hình

2. **Nếu không có third-party**:
   - Tìm kiếm trong database nội bộ
   - Sử dụng GPT để tạo câu trả lời từ dữ liệu tìm được

- **Nếu tìm thấy câu trả lời hợp lệ → Dừng pipeline**
- Ghi nhận token sử dụng

---

#### **Stage 5: RAG Processing (Retrieval-Augmented Generation)** 🔍
📍 **Function**: `_process_rag()` → `RAGBasedProcessing()`

**Điều kiện**: `keyword_dict[chatbot_key]['rag_toggle'] == True`

1. **Text RAG**:
   - Tìm kiếm các chunks (đoạn văn bản) liên quan từ tài liệu đã upload
   - Sử dụng embedding similarity để tìm chunks phù hợp nhất
   - Compact conversation history (nén lịch sử để tiết kiệm token)
   - Gọi GPT với context chunks + câu hỏi + lịch sử hội thoại
   - **Nếu tìm thấy câu trả lời → Dừng pipeline**

2. **Image RAG** (hiện đang comment):
   - Tìm kiếm hình ảnh liên quan
   - Xử lý và trả về kết quả kèm hình ảnh

- Ghi nhận token sử dụng (có thể dùng custom_model_id)

---

#### **Stage 6: AI Generation (Fallback)** 🤖
📍 **Function**: `_process_ai_generation()` → `gen_answer()`

**Điều kiện**: Khi không có stage nào ở trên trả về kết quả

- Đây là bước cuối cùng - fallback khi không tìm thấy câu trả lời cụ thể
- Compact conversation history
- Query company name từ database
- Gọi GPT để tạo câu trả lời tự do dựa trên:
  - Script/kịch bản chatbot
  - Normalized question
  - Company name
  - Chatbot name
  - Custom model (nếu có)
  - Strongfield
  - Conversation history

- Nếu `enable_auto_reply == False` và không có script phù hợp:
  - Trả về `answer_default`

- Ghi nhận token sử dụng

---

### **GIAI ĐOẠN 5: TRANSLATION & FINALIZATION**

1. **Dịch câu trả lời** (nếu cần)
   - Nếu `enable_multilingual == True`
   - Dịch từ ngôn ngữ chuẩn (thường là tiếng Anh) về ngôn ngữ của người dùng

2. **Cập nhật History**
   - Cập nhật `message_response` trong history
   - Cập nhật `flow_response` (stage nào đã trả lời)
   - Cập nhật `detail_id` (nếu có)

---

### **GIAI ĐOẠN 6: LƯU LỊCH SỬ VÀO DATABASE**
📍 **Function**: `create_chatbot_history()`

- Lưu thông tin hội thoại vào bảng `chatbot_history`:
  - Message receive/response
  - Normalized message
  - Language
  - Platform type
  - Customer code
  - Flow response
  - Detail ID

- Lưu thông tin token sử dụng vào bảng `message_used_token`:
  - Input tokens
  - Output tokens
  - Training tokens
  - Model name
  - Is finetuned

---

## Response Format

### Success Response (200)
```json
{
  "status": 200,
  "success": true,
  "message": "Success",
  "data": "Câu trả lời từ chatbot"
}
```

### Error Responses

**Token Limit Exceeded (429)**
```json
{
  "status": 429,
  "success": false,
  "message": "Token limit exceeded",
  "data": {
    "company_id": "xxx",
    "company_token_limit": 10000,
    "company_total_used_tokens": 10500
  }
}
```

**Invalid Input (400)**
```json
{
  "status": 400,
  "success": false,
  "message": "Invalid JSON data",
  "data": null
}
```

**System Error (500)**
```json
{
  "status": 500,
  "success": false,
  "message": "System error",
  "data": "Error details"
}
```

---

## Sơ đồ luồng (Text Format)

```
┌─────────────────────────────────────────────────────────────┐
│                    REQUEST RECEIVED                          │
│                 POST /chatbot-ai/completion                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              1. VALIDATE & SECURITY CHECK                    │
│  • Xác thực secret key                                       │
│  • Validate JSON, messages, content                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              2. SETUP & INITIALIZATION                       │
│  • Verify chatbot exists & active                            │
│  • Load chatbot configuration                                │
│  • Create history record                                     │
│  • Detect language                                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              3. CHECK TOKEN LIMITS                           │
│  • Company-level limit                                       │
│  • Chatbot-level limit                                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            4. PROCESSING PIPELINE (Waterfall)                │
└─────────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│Stage 1:     │  │Stage 2:     │  │Stage 3:     │
│Phone Number │─▶│Special Words│─▶│Normalize    │
│Validation   │  │Check        │  │Question     │
└─────────────┘  └─────────────┘  └──────┬──────┘
      │                │                  │
      │ Match?         │ Match?           ▼
      ▼                ▼           ┌─────────────┐
    RETURN           RETURN        │Stage 4A/4B: │
                                   │Rule/DB-based│
                                   │Processing   │
                                   └──────┬──────┘
                                          │
                                          │ Match?
                                          ▼
                                   ┌─────────────┐
                                   │Stage 5:     │
                                   │RAG          │
                                   │Processing   │
                                   └──────┬──────┘
                                          │
                                          │ Match?
                                          ▼
                                   ┌─────────────┐
                                   │Stage 6:     │
                                   │AI Generation│
                                   │(Fallback)   │
                                   └──────┬──────┘
                                          │
                         ┌────────────────┼────────────────┐
                         │                                 │
                         ▼                                 ▼
         ┌─────────────────────────────┐   ┌─────────────────────────┐
         │  5. TRANSLATE (if needed)   │   │  6. SAVE HISTORY & TOKEN│
         │  • Multilingual support     │   │  • chatbot_history      │
         └─────────────────────────────┘   │  • message_used_token   │
                         │                 └─────────────────────────┘
                         │                                 │
                         └────────────────┬────────────────┘
                                          │
                                          ▼
                         ┌────────────────────────────────┐
                         │      RETURN RESPONSE           │
                         │  {status, success, message,    │
                         │   data: "Answer"}              │
                         └────────────────────────────────┘
```

---

## Các cấu hình quan trọng

| Cấu hình | Ý nghĩa | Ảnh hưởng |
|----------|---------|-----------|
| `rule_based_toggle` | Bật/tắt xử lý rule-based | Quyết định dùng stage 4A hay 4B |
| `rag_toggle` | Bật/tắt RAG | Có chạy stage 5 hay không |
| `enable_auto_reply` | Bật/tắt tự động trả lời | AI generation có tự động tạo câu trả lời không |
| `enable_multilingual` | Bật/tắt đa ngôn ngữ | Có dịch câu trả lời không |
| `custom_model_id` | Model GPT tùy chỉnh | Model nào được dùng cho chatbot này |
| `strongfield` | Lĩnh vực mạnh | Giúp normalize question chính xác hơn |
| `third_party_integration` | Tích hợp bên thứ 3 | Provider nào được dùng (nếu có) |
| `token_limit` (company) | Giới hạn token công ty | Giới hạn tổng token cho toàn công ty |
| `token_limit` (chatbot) | Giới hạn token chatbot | Giới hạn token cho từng chatbot |

---

## Token Tracking

Mỗi stage có thể sử dụng token và được ghi nhận vào `token_stats_list`:

```python
{
  'history_id': uuid,
  'chatbot_id': uuid,
  'model_name': 'gpt-4o-mini',
  'input_token': 150,
  'output_token': 80,
  'training_token': 0,
  'is_finetuned': False
}
```

Tất cả token stats được lưu vào database ở cuối quá trình xử lý.

---

## Tối ưu hóa

1. **Compact Conversation**: Nén lịch sử hội thoại để tiết kiệm token khi gọi GPT
2. **Gộp queries**: Giảm số lần truy vấn database bằng cách gộp nhiều query
3. **Early return**: Dừng pipeline ngay khi tìm thấy câu trả lời hợp lệ
4. **Token limit check**: Kiểm tra giới hạn token trước khi xử lý để tránh lãng phí
5. **Session scope**: Sử dụng database session hiệu quả

---

## Các bảng database liên quan

1. **chatbot_ai**: Thông tin cấu hình chatbot
2. **chatbot_ai_script**: Kịch bản chatbot
3. **chatbot_ai_script_detail**: Chi tiết prompt/câu hỏi-trả lời
4. **chatbot_history**: Lịch sử hội thoại
5. **message_used_token**: Token đã sử dụng
6. **special_words**: Từ đặc biệt
7. **rag_documents**: Tài liệu RAG
8. **rag_chunk_documents**: Chunks từ tài liệu
9. **company**: Thông tin công ty

---

## Lưu ý quan trọng

- Pipeline hoạt động theo kiểu **waterfall**: Stage sau chỉ chạy khi stage trước không trả về kết quả
- **AI Generation (Stage 6)** luôn chạy cuối cùng như fallback
- Token được track ở mỗi stage để theo dõi chi phí
- Hệ thống hỗ trợ **multi-tenancy** qua `schema_name`
- Customer code mặc định là `'anonymous'` nếu không cung cấp
