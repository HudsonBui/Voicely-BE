
class AIPrompts:
    """AI-related prompts for various operations."""
    
    SUMMARY_SYSTEM_PROMPT = """Bạn là Trợ lý Tóm tắt Chuyên nghiệp. Nhiệm vụ của bạn là tạo bản tóm tắt dưới dạng JSON (Quill Delta format) để hiển thị trực tiếp trên trình soạn thảo Rich Text.

    ## NGUYÊN TẮC CỐT LÕI

    1. **Hiểu sâu nội dung**: Xác định mục đích chính, thông điệp và cấu trúc lập luận.
    2. **Lọc thông tin**: Phân biệt ý chính/phụ. Chỉ giữ số liệu thiết yếu. Loại bỏ tin lặp.
    3. **Viết súc tích**: Mỗi câu phải mang thông tin giá trị.
    4. **Giữ khách quan**: Trung lập, không thêm ý kiến cá nhân.
    5. **Đảm bảo chính xác**: Không xuyên tạc hoặc thêm thông tin ngoài văn bản gốc.
    6. **Tạo tính mạch lạc**: Sắp xếp logic, dễ hiểu.

    ## QUY TRÌNH

    A. Đọc khảo sát & Nắm ý.
    B. Đánh dấu ý chính & Lọc bỏ chi tiết thừa.
    C. Sắp xếp & Gom nhóm ý.
    D. Viết nháp theo định dạng JSON Delta.
    E. Kiểm tra lại tính hợp lệ của JSON và nội dung.

    ## ĐỊNH DẠNG ĐẦU RA: JSON (QUILL DELTA)

    Bạn **BẮT BUỘC** phải trả về một mảng JSON (JSON Array) hợp lệ, tuân thủ cấu trúc Delta của Quill. Không bao bọc bởi markdown block (```json). Chỉ trả về raw string.

    **Cấu trúc một Operation:**
    `{ "insert": "Nội dung văn bản\\n", "attributes": { "key": value } }`

    **Quy tắc Attributes (Định dạng):**
    - **Tiêu đề lớn (Section):** `{"header": 2}` (Tương đương h2)
    - **Tiêu đề nhỏ:** `{"header": 3}` (Tương đương h3)
    - **In đậm (Ý quan trọng):** `{"bold": true}`
    - **In nghiêng (Thuật ngữ):** `{"italic": true}`
    - **Danh sách (Bullet points):** Áp dụng `{"list": "bullet"}` cho ký tự xuống dòng `\\n` ngay sau nội dung.
    - **Trích dẫn:** Áp dụng `{"blockquote": true}` cho ký tự xuống dòng `\\n`.

    **Lưu ý quan trọng về cú pháp JSON Delta:**
    1. Mỗi đoạn văn hoặc tiêu đề phải kết thúc bằng `\\n`.
    2. Thuộc tính Block (header, list, blockquote) phải được gắn vào ký tự `\\n` (một object riêng chứa `insert: "\\n"`).
    3. Thuộc tính Inline (bold, italic) gắn trực tiếp vào text.

    **Ví dụ mẫu cấu trúc mong muốn:**
    [
    {"insert": "Tiêu đề Tóm tắt\\n", "attributes": {"header": 2}},
    {"insert": "Đây là câu giới thiệu tổng quan.\\n"},
    {"insert": "Luận điểm chính 1"},
    {"insert": "\\n", "attributes": {"list": "bullet"}},
    {"insert": "Luận điểm chính 2"},
    {"insert": "\\n", "attributes": {"list": "bullet"}}
    ]

    ## RÀNG BUỘC TUYỆT ĐỐI

    ✗ KHÔNG trả về định dạng Markdown (**, ##) hay HTML (<b>, <p>).
    ✗ KHÔNG giải thích, chỉ trả về JSON thuần.
    ✗ Đảm bảo JSON valid tuyệt đối (escape kỹ các ký tự đặc biệt như ngoặc kép).
    ✗ Văn bản trong `insert` phải là tiếng Việt (trừ thuật ngữ chuyên ngành).
    """

    SUMMARY_USER_PROMPT = """Tóm tắt văn bản sau thành cấu trúc JSON (Quill Delta) theo hướng dẫn trong System Prompt.

    ## CẤU HÌNH MONG MUỐN

    **Độc giả mục tiêu**: [mặc định: đại chúng có hiểu biết cơ bản]
    **Phong cách trình bày**: [paragraph (đoạn văn) / bullet (gạch đầu dòng)]
    **Độ dài mục tiêu**: [~50{{%}} bản gốc]
    **Ngôn ngữ**: [vi / en / ...]
    **Số ý chính tối đa**: [mặc định: 5] _(chỉ áp dụng nếu chọn bullet)_
    **Giữ số liệu cụ thể**: [có / không - mặc định: có]
    **Thêm từ khóa**: [có / không - mặc định: không] _(Nếu có, tạo section riêng ở cuối)_
    **Thêm trích dẫn nổi bật**: [có / không - mặc định: không] _(Nếu có, dùng attribute blockquote)_

    ---

    ## VĂN BẢN GỐC

    {content}

    ---

    ## YÊU CẦU ĐẦU RA (NGHIÊM NGẶT)

    1. Trả về **duy nhất** một JSON Array hợp lệ (bắt đầu bằng `[` và kết thúc bằng `]`).
    2. **KHÔNG** sử dụng Markdown code block (như ```json ... ```). Chỉ trả về Raw String.
    3. **KHÔNG** thêm bất kỳ lời dẫn hay giải thích nào bên ngoài mảng JSON.
    4. Đảm bảo mọi chuỗi ký tự trong JSON được escape đúng quy chuẩn (đặc biệt là dấu ngoặc kép `"` và ký tự xuống dòng `\\n`).
"""


class TranscriptionConfig:
    """Transcription service configuration constants."""
    
    # File size limits
    MAX_SYNC_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_ASYNC_FILE_SIZE = 1 * 1024 * 1024  # 1MB
    MAX_GCS_FALLBACK_SIZE = 2 * 1024 * 1024  # 2MB
    
    # Duration limits
    MAX_SYNC_DURATION = 60  # 60 seconds
    MAX_ASYNC_DURATION = 300  # 5 minutes
    MAX_GCS_DURATION = 480 * 60  # 480 minutes (8 hours)
    
    # Audio settings
    DEFAULT_SAMPLE_RATE = 16000
    DEFAULT_ENCODING = "LINEAR16"
    
    # Timeout settings
    LONG_RUNNING_TIMEOUT = 7200  # 120 minutes
    GCS_TRANSCRIPTION_TIMEOUT = 7200  # 120 minutes


class AudioConfig:
    """Audio file configuration constants."""
    
    # Supported formats
    SUPPORTED_FORMATS = [
        'wav', 'mp3', 'flac', 'ogg', 'opus', 
        'm4a', 'aac', 'wma', 'webm'
    ]
    
    # Format categories
    LOSSLESS_FORMATS = ['wav', 'flac']
    COMPRESSED_FORMATS = ['mp3', 'aac', 'm4a', 'ogg', 'opus']
    
    # Conversion settings
    CONVERT_FORMATS = ['mp3', 'm4a', 'aac']  # Formats to convert for better recognition
    CONVERTED_SAMPLE_RATE = 16000
    CONVERTED_CHANNELS = 1  # Mono


class FileUploadConfig:
    """File upload configuration constants."""
    
    # Upload limits
    MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_FILE_NAME_LENGTH = 255
    
    # Allowed MIME types
    ALLOWED_AUDIO_MIME_TYPES = [
        'audio/wav',
        'audio/mpeg',
        'audio/mp3',
        'audio/flac',
        'audio/ogg',
        'audio/opus',
        'audio/m4a',
        'audio/aac',
        'audio/x-wav',
        'audio/x-m4a',
    ]
    
    # Upload paths
    UPLOAD_BASE_DIR = "uploads"
    AUDIO_UPLOAD_DIR = "uploads/audio"
    TEMP_UPLOAD_DIR = "uploads/temp"


class LanguageCodes:
    """Supported language codes for transcription."""
    
    SUPPORTED_LANGUAGES = [
        {"code": "en-US", "name": "English (US)"},
        {"code": "en-GB", "name": "English (UK)"},
        {"code": "vi-VN", "name": "Vietnamese"},
        {"code": "es-ES", "name": "Spanish (Spain)"},
        {"code": "es-MX", "name": "Spanish (Mexico)"},
        {"code": "fr-FR", "name": "French"},
        {"code": "de-DE", "name": "German"},
        {"code": "ja-JP", "name": "Japanese"},
        {"code": "ko-KR", "name": "Korean"},
        {"code": "zh-CN", "name": "Chinese (Simplified)"},
        {"code": "zh-TW", "name": "Chinese (Traditional)"},
        {"code": "pt-BR", "name": "Portuguese (Brazil)"},
        {"code": "pt-PT", "name": "Portuguese (Portugal)"},
        {"code": "it-IT", "name": "Italian"},
        {"code": "ru-RU", "name": "Russian"},
        {"code": "ar-SA", "name": "Arabic"},
        {"code": "hi-IN", "name": "Hindi"},
        {"code": "th-TH", "name": "Thai"},
        {"code": "id-ID", "name": "Indonesian"},
    ]
    
    DEFAULT_LANGUAGE = "en-US"


class StatusCodes:
    """Status codes for various operations."""
    
    # Audio processing status
    AUDIO_PENDING = "pending"
    AUDIO_PROCESSING = "processing"
    AUDIO_COMPLETED = "completed"
    AUDIO_FAILED = "failed"
    
    # Transcription status
    TRANSCRIPTION_PENDING = "pending"
    TRANSCRIPTION_IN_PROGRESS = "in_progress"
    TRANSCRIPTION_COMPLETED = "completed"
    TRANSCRIPTION_FAILED = "failed"
    
    # Note status
    NOTE_ACTIVE = "active"
    NOTE_ARCHIVED = "archived"
    NOTE_DELETED = "deleted"


class ErrorMessages:
    """Common error messages."""
    
    # Authentication errors
    INVALID_CREDENTIALS = "Invalid email or password"
    UNAUTHORIZED = "Not authenticated"
    FORBIDDEN = "Permission denied"
    TOKEN_EXPIRED = "Token has expired"
    INVALID_TOKEN = "Invalid token"
    
    # File errors
    FILE_NOT_FOUND = "File not found"
    FILE_TOO_LARGE = "File size exceeds maximum allowed size"
    INVALID_FILE_FORMAT = "Invalid file format"
    UPLOAD_FAILED = "File upload failed"
    
    # Transcription errors
    TRANSCRIPTION_UNAVAILABLE = "Transcription service is not available"
    TRANSCRIPTION_FAILED = "Transcription failed"
    GCS_NOT_CONFIGURED = "Google Cloud Storage not configured"
    GCS_UPLOAD_FAILED = "Failed to upload file to Google Cloud Storage"
    
    # Database errors
    DATABASE_ERROR = "Database operation failed"
    RECORD_NOT_FOUND = "Record not found"
    DUPLICATE_ENTRY = "Record already exists"
    
    # General errors
    INTERNAL_ERROR = "Internal server error"
    VALIDATION_ERROR = "Validation error"
    BAD_REQUEST = "Bad request"


class SuccessMessages:
    """Common success messages."""
    
    # Authentication
    LOGIN_SUCCESS = "Login successful"
    LOGOUT_SUCCESS = "Logout successful"
    SIGNUP_SUCCESS = "Account created successfully"
    
    # File operations
    UPLOAD_SUCCESS = "File uploaded successfully"
    DELETE_SUCCESS = "File deleted successfully"
    
    # Transcription
    TRANSCRIPTION_SUCCESS = "Transcription completed successfully"
    TRANSCRIPTION_STARTED = "Transcription started"
    
    # Note operations
    NOTE_CREATED = "Note created successfully"
    NOTE_UPDATED = "Note updated successfully"
    NOTE_DELETED = "Note deleted successfully"


class RegexPatterns:
    """Common regex patterns for validation."""
    
    EMAIL = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    PASSWORD = r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*#?&]{8,}$'  # Min 8 chars, 1 letter, 1 number
    PHONE = r'^\+?1?\d{9,15}$'
    URL = r'^https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)$'


class CacheKeys:
    """Cache key templates."""
    
    USER_PROFILE = "user:profile:{user_id}"
    AUDIO_FILE = "audio:file:{audio_id}"
    TRANSCRIPTION = "transcription:{audio_id}"
    NOTE = "note:{note_id}"
    USER_NOTES = "user:notes:{user_id}"
    
    # Cache TTL (in seconds)
    DEFAULT_TTL = 3600  # 1 hour
    SHORT_TTL = 300  # 5 minutes
    LONG_TTL = 86400  # 24 hours


class PaginationDefaults:
    """Default pagination settings."""
    
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    MIN_PAGE_SIZE = 1

class Common:
    # Embedding model configuration
    EMBEDDING_MODEL = "text-embedding-005"
    EMBEDDING_DIMENSION = 768  # Default dimension for text-embedding-005